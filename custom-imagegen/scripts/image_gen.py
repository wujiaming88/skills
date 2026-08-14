#!/usr/bin/env python3
"""通过自定义 OpenAI 兼容接口生成或编辑图片。"""

from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence
import urllib.error
import urllib.parse
import urllib.request

API_BASE_URL_ENV = "CUSTOM_IMAGE_API_BASE_URL"
API_KEY_ENV = "CUSTOM_IMAGE_API_KEY"
MODEL_ENV = "CUSTOM_IMAGE_MODEL"
DEFAULT_OUTPUT = "output/custom-imagegen/output.png"
DEFAULT_TIMEOUT_SECONDS = 180.0
MAX_BATCH_JOBS = 500
MAX_EDIT_IMAGES = 16
MAX_IMAGE_BYTES = 50 * 1024 * 1024
RESERVED_EXTRA_FIELDS = {"model", "prompt", "n", "image", "mask"}
PROMPT_FIELD_NAMES = (
    "use_case",
    "asset_type",
    "scene",
    "subject",
    "style",
    "composition",
    "lighting",
    "palette",
    "materials",
    "text",
    "constraints",
    "negative",
)
REQUEST_OPTION_NAMES = (
    "size",
    "quality",
    "background",
    "output_format",
    "output_compression",
    "moderation",
    "response_format",
    "user",
)


class CliError(RuntimeError):
    """表示可向用户直接说明的命令行错误。"""


@dataclass(frozen=True)
class GenerationPlan:
    """保存一次生成请求及对应的输出路径。"""

    payload: dict[str, Any]
    outputs: tuple[Path, ...]


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def _read_prompt(prompt: str | None, prompt_file: str | None) -> str:
    if prompt and prompt_file:
        raise CliError("Use --prompt or --prompt-file, not both.")
    if prompt_file:
        path = Path(prompt_file)
        if not path.is_file():
            raise CliError(f"Prompt file not found: {path}")
        value = path.read_text(encoding="utf-8").strip()
    else:
        value = (prompt or "").strip()
    if not value:
        raise CliError("Missing prompt. Use --prompt or --prompt-file.")
    return value


def _normalize_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    for suffix in ("/images/generations", "/images/edits"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CliError(f"{API_BASE_URL_ENV} must be an absolute HTTP(S) URL.")
    if parsed.query or parsed.fragment:
        raise CliError(f"{API_BASE_URL_ENV} must not contain a query or fragment.")
    return value.rstrip("/")


def _load_setting(cli_value: str | None, env_name: str) -> str:
    value = (cli_value or os.getenv(env_name, "")).strip()
    if not value:
        raise CliError(f"Missing configuration: set {env_name}.")
    return value


def _load_api_key(dry_run: bool) -> str:
    value = os.getenv(API_KEY_ENV, "").strip()
    if not value and not dry_run:
        raise CliError(f"Missing configuration: set {API_KEY_ENV}.")
    return value


def _parse_extra_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(f"--extra-json is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CliError("--extra-json must contain a JSON object.")
    conflicts = RESERVED_EXTRA_FIELDS.intersection(value)
    if conflicts:
        names = ", ".join(sorted(conflicts))
        raise CliError(f"--extra-json cannot override reserved fields: {names}")
    return value


def _augment_prompt(prompt: str, fields: Mapping[str, Any], enabled: bool) -> str:
    if not enabled:
        return prompt
    labels = {
        "use_case": "Use case",
        "asset_type": "Asset type",
        "scene": "Scene/backdrop",
        "subject": "Subject",
        "style": "Style/medium",
        "composition": "Composition/framing",
        "lighting": "Lighting/mood",
        "palette": "Color palette",
        "materials": "Materials/textures",
        "text": "Text (verbatim)",
        "constraints": "Constraints",
        "negative": "Avoid",
    }
    lines = [f"Primary request: {prompt}"]
    for name in PROMPT_FIELD_NAMES:
        value = fields.get(name)
        if value is not None and str(value).strip():
            rendered = f'"{value}"' if name == "text" else str(value)
            lines.append(f"{labels[name]}: {rendered}")
    return "\n".join(lines)


def _validate_request_values(count: int, values: Mapping[str, Any]) -> None:
    if count < 1 or count > 10:
        raise CliError("--n must be between 1 and 10.")
    compression = values.get("output_compression")
    if compression is not None and not 0 <= int(compression) <= 100:
        raise CliError("--output-compression must be between 0 and 100.")
    background = values.get("background")
    output_format = values.get("output_format")
    if background == "transparent" and output_format not in {None, "png", "webp"}:
        raise CliError("Transparent background requires png or webp output format.")


def _build_payload(
    model: str,
    prompt: str,
    count: int,
    values: Mapping[str, Any],
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_request_values(count, values)
    payload: dict[str, Any] = {"model": model, "prompt": prompt, "n": count}
    for name in REQUEST_OPTION_NAMES:
        if values.get(name) is not None:
            payload[name] = values[name]
    if values.get("input_fidelity") is not None:
        payload["input_fidelity"] = values["input_fidelity"]
    if extra:
        payload["extra_body"] = dict(extra)
    return payload


def _normalize_extension(output_format: str | None) -> str:
    value = (output_format or "png").lower().lstrip(".")
    if not re.fullmatch(r"[a-z0-9]+", value):
        raise CliError("--output-format must be a simple file format such as png or webp.")
    return "jpg" if value == "jpeg" else value


def _build_output_paths(out: str, count: int, output_format: str | None) -> list[Path]:
    extension = _normalize_extension(output_format)
    path = Path(out)
    if not path.suffix:
        path = path.with_suffix(f".{extension}")
    if count == 1:
        return [path]
    return [
        path.with_name(f"{path.stem}-{index}{path.suffix}")
        for index in range(1, count + 1)
    ]


def _ensure_outputs_available(paths: Sequence[Path], force: bool) -> None:
    normalized = [str(path.absolute()) for path in paths]
    if len(normalized) != len(set(normalized)):
        raise CliError("Multiple jobs resolve to the same output path.")
    if force:
        return
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise CliError(f"Output already exists: {existing[0]} (use --force to overwrite)")


def _redact(text: str, secret: str) -> str:
    return text.replace(secret, "[REDACTED]") if secret else text


def _format_sdk_error(exc: Exception, api_key: str) -> str:
    status_code = getattr(exc, "status_code", None)
    prefix = f"HTTP {status_code}: " if isinstance(status_code, int) else ""
    return _redact(f"{prefix}{exc}", api_key)


def _create_client(base_url: str, api_key: str, timeout: float) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise CliError(
            "The openai package is required for live calls. "
            "Install it in the active environment with `python3 -m pip install openai`."
        ) from exc
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=0,
    )


def _call_generate(client: Any, payload: Mapping[str, Any], api_key: str) -> Any:
    try:
        return client.images.generate(**payload)
    except Exception as exc:
        raise CliError(f"Image generation failed: {_format_sdk_error(exc, api_key)}") from exc


def _call_edit(
    client: Any,
    payload: Mapping[str, Any],
    images: Sequence[Path],
    mask: Path | None,
    api_key: str,
) -> Any:
    try:
        with ExitStack() as stack:
            image_files = [stack.enter_context(path.open("rb")) for path in images]
            request = dict(payload)
            request["image"] = image_files[0] if len(image_files) == 1 else image_files
            if mask is not None:
                request["mask"] = stack.enter_context(mask.open("rb"))
            return client.images.edit(**request)
    except Exception as exc:
        raise CliError(f"Image edit failed: {_format_sdk_error(exc, api_key)}") from exc


def _decode_base64_image(value: str) -> bytes:
    encoded = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    try:
        image = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CliError("Image API returned invalid base64 image data.") from exc
    if not image:
        raise CliError("Image API returned an empty base64 image.")
    return image


def _download_image(url: str, timeout: float) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CliError("Image download URL must be an absolute HTTP(S) URL.")
    request = urllib.request.Request(url, headers={"Accept": "image/*"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            image = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise CliError(f"Image download failed: {exc}") from exc
    if not image:
        raise CliError("Image download returned an empty body.")
    return image


def _extract_images(result: Any, timeout: float) -> list[bytes]:
    data = getattr(result, "data", None)
    if not isinstance(data, list) or not data:
        raise CliError("Image API response does not contain a non-empty data array.")
    images: list[bytes] = []
    for index, item in enumerate(data, start=1):
        image_b64 = getattr(item, "b64_json", None)
        image_url = getattr(item, "url", None)
        if isinstance(image_b64, str):
            images.append(_decode_base64_image(image_b64))
        elif isinstance(image_url, str):
            images.append(_download_image(image_url, timeout))
        else:
            raise CliError(f"Image API data item {index} has neither b64_json nor url.")
    return images


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
        raise CliError(f"Failed to write image {path}: {exc}") from exc


def _save_images(images: Sequence[bytes], outputs: Sequence[Path]) -> None:
    if len(images) != len(outputs):
        raise CliError(
            f"Image API returned {len(images)} image(s), expected {len(outputs)} from n."
        )
    for image, output in zip(images, outputs):
        _write_atomic(output, image)
        print(f"Wrote {output}")


def _prompt_fields(values: Mapping[str, Any]) -> dict[str, Any]:
    return {name: values.get(name) for name in PROMPT_FIELD_NAMES}


def _preview(
    endpoint: str,
    payload: Mapping[str, Any],
    outputs: Sequence[Path],
    inputs: Mapping[str, Any] | None = None,
) -> None:
    visible_payload = {key: value for key, value in payload.items() if key != "extra_body"}
    if payload.get("extra_body"):
        visible_payload["extra"] = payload["extra_body"]
    preview = {"endpoint": endpoint, "outputs": [str(path) for path in outputs]}
    if inputs:
        preview.update(inputs)
    preview.update(visible_payload)
    print(json.dumps(preview, ensure_ascii=False, indent=2, sort_keys=True))


def _validate_edit_inputs(raw_images: Sequence[str], raw_mask: str | None) -> tuple[list[Path], Path | None]:
    if not raw_images:
        raise CliError("At least one --image is required for edit.")
    if len(raw_images) > MAX_EDIT_IMAGES:
        raise CliError(f"Edit accepts at most {MAX_EDIT_IMAGES} input images.")
    images = [_validate_image_file(Path(raw), "Input image") for raw in raw_images]
    mask = _validate_image_file(Path(raw_mask), "Mask") if raw_mask else None
    if mask is not None and mask.suffix.lower() != ".png":
        _warn(f"Mask should normally be a PNG with an alpha channel: {mask}")
    return images, mask


def _validate_image_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise CliError(f"{label} not found: {path}")
    size = path.stat().st_size
    if size > MAX_IMAGE_BYTES:
        raise CliError(f"{label} exceeds 50MB: {path}")
    if size == 0:
        raise CliError(f"{label} is empty: {path}")
    return path


def _run_generate(args: argparse.Namespace) -> None:
    values = vars(args)
    base_url = _normalize_base_url(_load_setting(args.base_url, API_BASE_URL_ENV))
    model = _load_setting(args.model, MODEL_ENV)
    api_key = _load_api_key(args.dry_run)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    prompt = _augment_prompt(prompt, _prompt_fields(values), not args.no_augment)
    payload = _build_payload(model, prompt, args.n, values, _parse_extra_json(args.extra_json))
    outputs = _build_output_paths(args.out, args.n, args.output_format)
    _ensure_outputs_available(outputs, args.force)
    if args.dry_run:
        _preview(f"{base_url}/images/generations", payload, outputs)
        return
    client = _create_client(base_url, api_key, args.timeout)
    result = _call_generate(client, payload, api_key)
    _save_images(_extract_images(result, args.timeout), outputs)


def _run_edit(args: argparse.Namespace) -> None:
    values = vars(args)
    base_url = _normalize_base_url(_load_setting(args.base_url, API_BASE_URL_ENV))
    model = _load_setting(args.model, MODEL_ENV)
    api_key = _load_api_key(args.dry_run)
    images, mask = _validate_edit_inputs(args.image, args.mask)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    prompt = _augment_prompt(prompt, _prompt_fields(values), not args.no_augment)
    payload = _build_payload(model, prompt, args.n, values, _parse_extra_json(args.extra_json))
    outputs = _build_output_paths(args.out, args.n, args.output_format)
    _ensure_outputs_available(outputs, args.force)
    if args.dry_run:
        inputs = {"images": [str(path) for path in images], "mask": str(mask) if mask else None}
        _preview(f"{base_url}/images/edits", payload, outputs, inputs)
        return
    client = _create_client(base_url, api_key, args.timeout)
    result = _call_edit(client, payload, images, mask, api_key)
    _save_images(_extract_images(result, args.timeout), outputs)


def _read_batch_jobs(path: str) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise CliError(f"Batch input not found: {source}")
    jobs: list[dict[str, Any]] = []
    for line_number, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            value = json.loads(line) if line.startswith("{") else line
        except json.JSONDecodeError as exc:
            raise CliError(f"Invalid JSON on line {line_number}: {exc}") from exc
        job = {"prompt": value} if isinstance(value, str) else value
        if not isinstance(job, dict) or not str(job.get("prompt", "")).strip():
            raise CliError(f"Batch line {line_number} must contain a prompt.")
        jobs.append(job)
    if not jobs:
        raise CliError("Batch input contains no jobs.")
    if len(jobs) > MAX_BATCH_JOBS:
        raise CliError(f"Batch contains more than {MAX_BATCH_JOBS} jobs.")
    return jobs


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:50] or "image"


def _merge_values(base: Mapping[str, Any], job: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    names = (*PROMPT_FIELD_NAMES, *REQUEST_OPTION_NAMES, "model", "n")
    for key in names:
        if job.get(key) is not None:
            merged[key] = job[key]
    return merged


def _build_batch_plans(args: argparse.Namespace, model: str) -> list[GenerationPlan]:
    base = vars(args).copy()
    base["model"] = model
    base_extra = _parse_extra_json(args.extra_json)
    plans: list[GenerationPlan] = []
    for index, job in enumerate(_read_batch_jobs(args.input), start=1):
        values = _merge_values(base, job)
        prompt = _augment_prompt(
            str(job["prompt"]).strip(), _prompt_fields(values), not args.no_augment
        )
        job_extra = job.get("extra", {})
        if not isinstance(job_extra, dict):
            raise CliError(f"Batch job {index} extra must be an object.")
        extra = dict(base_extra)
        extra.update(_parse_extra_json(json.dumps(job_extra)))
        count = int(values["n"])
        payload = _build_payload(str(values["model"]), prompt, count, values, extra)
        name = str(job.get("out") or f"{index:03d}-{_slugify(str(job['prompt']))}")
        out = str(Path(args.out_dir) / Path(name).name)
        outputs = tuple(_build_output_paths(out, count, values.get("output_format")))
        plans.append(GenerationPlan(payload=payload, outputs=outputs))
    return plans


def _run_generate_batch(args: argparse.Namespace) -> None:
    base_url = _normalize_base_url(_load_setting(args.base_url, API_BASE_URL_ENV))
    model = _load_setting(args.model, MODEL_ENV)
    api_key = _load_api_key(args.dry_run)
    plans = _build_batch_plans(args, model)
    all_outputs = [path for plan in plans for path in plan.outputs]
    _ensure_outputs_available(all_outputs, args.force)
    if args.dry_run:
        for plan in plans:
            _preview(f"{base_url}/images/generations", plan.payload, plan.outputs)
        return
    client = _create_client(base_url, api_key, args.timeout)
    for plan in plans:
        result = _call_generate(client, plan.payload, api_key)
        _save_images(_extract_images(result, args.timeout), plan.outputs)


def _add_request_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", help=f"Override {API_BASE_URL_ENV}")
    parser.add_argument("--model", help=f"Override {MODEL_ENV}")
    parser.add_argument("--n", type=int, default=1, help="Images per prompt, 1-10")
    parser.add_argument("--size", help="Provider-specific size, for example 1024x1024")
    parser.add_argument("--quality", help="Provider-specific quality")
    parser.add_argument("--background", choices=["transparent", "opaque", "auto"])
    parser.add_argument("--output-format", choices=["png", "jpeg", "webp"])
    parser.add_argument("--output-compression", type=int)
    parser.add_argument("--moderation", choices=["low", "auto"])
    parser.add_argument("--response-format", choices=["url", "b64_json"])
    parser.add_argument("--user")
    parser.add_argument("--extra-json", help="Provider-specific JSON object")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-augment", action="store_true")
    for field in PROMPT_FIELD_NAMES:
        parser.add_argument(f"--{field.replace('_', '-')}", dest=field)


def _add_prompt_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--out", default=DEFAULT_OUTPUT)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate one prompt")
    _add_request_arguments(generate)
    _add_prompt_arguments(generate)
    generate.set_defaults(handler=_run_generate)

    edit = subparsers.add_parser("edit", help="Edit one or more local images")
    _add_request_arguments(edit)
    _add_prompt_arguments(edit)
    edit.add_argument("--image", action="append", required=True)
    edit.add_argument("--mask")
    edit.add_argument("--input-fidelity", choices=["low", "high"])
    edit.set_defaults(handler=_run_edit)

    batch = subparsers.add_parser("generate-batch", help="Generate JSONL jobs sequentially")
    _add_request_arguments(batch)
    batch.add_argument("--input", required=True)
    batch.add_argument("--out-dir", default="output/custom-imagegen")
    batch.set_defaults(handler=_run_generate_batch)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero.")
    try:
        args.handler(args)
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
