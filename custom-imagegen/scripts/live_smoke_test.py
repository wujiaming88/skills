#!/usr/bin/env python3
"""对已配置的自定义图片接口执行显式付费的真实冒烟测试。"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Sequence
import zlib

CLI = Path(__file__).with_name("image_gen.py")
REQUIRED_ENV = (
    "CUSTOM_IMAGE_API_BASE_URL",
    "CUSTOM_IMAGE_API_KEY",
    "CUSTOM_IMAGE_MODEL",
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class SmokeTestError(RuntimeError):
    """表示真实接口冒烟测试未满足契约。"""


def _require_configuration() -> None:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name, "").strip()]
    if missing:
        raise SmokeTestError(f"Missing configuration: {', '.join(missing)}")


def _parse_fixed_size(size: str) -> tuple[int, int]:
    parts = size.lower().split("x", 1)
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise SmokeTestError("--size must be a fixed WIDTHxHEIGHT value.")
    width, height = int(parts[0]), int(parts[1])
    if width <= 0 or height <= 0:
        raise SmokeTestError("--size dimensions must be greater than zero.")
    return width, height


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def _write_half_mask(path: Path, width: int, height: int) -> None:
    """生成左半透明、右半不透明的 RGBA PNG 蒙版。"""
    transparent = b"\xff\xff\xff\x00" * (width // 2)
    opaque = b"\xff\xff\xff\xff" * (width - width // 2)
    scanlines = b"".join(b"\x00" + transparent + opaque for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    content = PNG_SIGNATURE
    content += _png_chunk(b"IHDR", header)
    content += _png_chunk(b"IDAT", zlib.compress(scanlines))
    content += _png_chunk(b"IEND", b"")
    path.write_bytes(content)


def _run_cli(arguments: Sequence[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise SmokeTestError(detail)


def _assert_png_size(path: Path, expected: tuple[int, int]) -> None:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise SmokeTestError(f"Expected a PNG output: {path}")
    actual = struct.unpack(">II", data[16:24])
    if actual != expected:
        raise SmokeTestError(f"Unexpected output size for {path}: {actual}, expected {expected}")


def _generate_image(output: Path, size: str) -> None:
    _run_cli(
        [
            "generate",
            "--prompt",
            "A red ceramic mug on a plain table",
            "--size",
            size,
            "--quality",
            "low",
            "--no-augment",
            "--out",
            str(output),
        ]
    )


def _edit_images(
    images: Sequence[Path],
    prompt: str,
    output: Path,
    size: str,
    mask: Path | None = None,
) -> None:
    arguments = ["edit"]
    for image in images:
        arguments.extend(["--image", str(image)])
    if mask is not None:
        arguments.extend(["--mask", str(mask)])
    arguments.extend(
        [
            "--prompt",
            prompt,
            "--size",
            size,
            "--quality",
            "low",
            "--no-augment",
            "--out",
            str(output),
        ]
    )
    _run_cli(arguments)


def _run_smoke_test(output_dir: Path, size: str) -> list[Path]:
    dimensions = _parse_fixed_size(size)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = output_dir / "generated.png"
    single_edit = output_dir / "single-edit.png"
    multi_edit = output_dir / "multi-edit.png"
    masked_edit = output_dir / "masked-edit.png"
    mask = output_dir / "mask.png"
    _generate_image(generated, size)
    _assert_png_size(generated, dimensions)
    _edit_images([generated], "Change only the mug color to blue", single_edit, size)
    _assert_png_size(single_edit, dimensions)
    _edit_images(
        [generated, single_edit],
        "Place both mugs side by side",
        multi_edit,
        size,
    )
    _assert_png_size(multi_edit, dimensions)
    _write_half_mask(mask, *dimensions)
    _edit_images(
        [generated],
        "Change only the masked area to green",
        masked_edit,
        size,
        mask,
    )
    _assert_png_size(masked_edit, dimensions)
    return [generated, single_edit, multi_edit, masked_edit, mask]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--confirm-billable", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.confirm_billable:
        print("Error: pass --confirm-billable to allow four live API calls.", file=sys.stderr)
        return 2
    try:
        _require_configuration()
        outputs = _run_smoke_test(Path(args.out_dir), args.size)
    except (OSError, SmokeTestError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("Live smoke test passed:")
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
