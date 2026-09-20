#!/usr/bin/env python3
"""Seedance 2.5 官方异步视频 API CLI；Python 3.10+，无第三方依赖。"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from seedance_payload import (
    FIELDS,
    MODEL,
    RATIOS,
    TASK_TYPES,
    encode_payload,
    http_url,
    media_item,
    preview_payload,
    read_payload,
    require,
    validate_payload,
)

API_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
KEY_ENV = "SEEDANCE_API_KEY"
TERMINAL = {"succeeded", "failed", "cancelled", "expired"}


def redact(text: str) -> str:
    secret = os.environ.get(KEY_ENV, "")
    return text.replace(secret, "[REDACTED]") if secret else text


def emit(value: Any, *, error: bool = False) -> None:
    print(redact(json.dumps(value, ensure_ascii=False, allow_nan=False)),
          file=sys.stderr if error else sys.stdout, flush=True)


class NoRedirect(HTTPRedirectHandler):
    """认证 API 禁止重定向，防止 Bearer 被转发至第三方。"""

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        raise ValueError("API 返回重定向，已阻止；请核对官方端点")


class MediaRedirect(HTTPRedirectHandler):
    """产物下载只允许继续访问 HTTPS，且不携带 API 认证头。"""

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> Request | None:
        http_url(newurl, https_only=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, timeout: float) -> None:
        key = os.environ.get(KEY_ENV, "")
        require(bool(key.strip()), f"未设置环境变量 {KEY_ENV}；请在本地安全配置，不要把密钥发到对话中")
        require(not any(c.isspace() for c in key), f"{KEY_ENV} 含空白字符")
        self.key = key
        self.timeout = timeout
        self.opener = build_opener(NoRedirect())

    def request(self, method: str, suffix: str = "", *, body: dict[str, Any] | None = None,
                query: list[tuple[str, str]] | None = None, timeout: float | None = None) -> dict[str, Any]:
        url = API_URL + suffix + (("?" + urlencode(query)) if query else "")
        request = Request(url, data=encode_payload(body) if body is not None else None,
                          headers={"Authorization": f"Bearer {self.key}",
                                   "Content-Type": "application/json"}, method=method)
        try:
            with self.opener.open(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read(8192).decode("utf-8", errors="replace")
            request_id = exc.headers.get("X-Request-Id", "")
            raise RuntimeError(f"HTTP {exc.code}; request_id={request_id}; {detail}") from exc
        except (URLError, TimeoutError, OSError, HTTPException) as exc:
            note = "；创建结果未知，请查询任务列表核对，勿自动重新提交" if method == "POST" else ""
            raise RuntimeError(f"API 网络错误：{exc}{note}") from exc
        if not raw and method == "DELETE":
            return {}
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise RuntimeError("API 返回非 JSON 响应；请检查任务状态后再决定是否重试") from exc
        require(isinstance(result, dict), "API 响应必须是 JSON 对象")
        if result.get("error") and not result.get("status"):
            raise RuntimeError(f"API 错误：{json.dumps(result['error'], ensure_ascii=False)}")
        return result

    def get(self, task_id: str, *, timeout: float | None = None) -> dict[str, Any]:
        return self.request("GET", task_path(task_id), timeout=timeout)


def task_path(task_id: str) -> str:
    require(bool(task_id.strip()) and not any(c.isspace() for c in task_id), "任务 ID 不能为空或含空白")
    require(task_id not in {".", ".."}, "任务 ID 无效")
    return "/" + quote(task_id, safe="")


def wait_task(client: Client, task_id: str, seconds: float, interval: float) -> dict[str, Any]:
    """本地超时不会取消服务端任务，后续可用同一 ID 继续查询。"""
    deadline = time.monotonic() + seconds
    previous: str | None = None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"等待超时；任务 {task_id} 可能仍在运行，请用 wait/get 继续查询")
        try:
            task = client.get(task_id, timeout=min(client.timeout, remaining))
        except (ValueError, RuntimeError) as exc:
            raise RuntimeError(f"查询任务 {task_id} 失败；可用同一 ID 恢复：{exc}") from exc
        status = task.get("status")
        require(isinstance(status, str) and status in TERMINAL | {"queued", "running"},
                f"任务 {task_id} 返回未知状态：{status}")
        if status != previous:
            emit({"id": task_id, "status": status}, error=True)
            previous = status
        if status in TERMINAL:
            return task
        time.sleep(min(interval, max(0, deadline - time.monotonic())))


def check_output(path: Path, force: bool) -> None:
    require(not path.is_dir(), f"输出路径是目录：{path}")
    require(force or not path.exists(), f"文件已存在：{path}；确认覆盖后使用 --force")
    require(not path.is_symlink(), f"输出路径不能是符号链接：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def staged_file(path: Path, force: bool) -> Iterator[Path]:
    """下载或序列化完整后原子发布，失败时不留下半个产物。"""
    check_output(path, force)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        yield temporary
        if force:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_receipt(path: str | None, task: dict[str, Any], force: bool) -> None:
    if path:
        with staged_file(Path(path).expanduser(), force) as temporary:
            temporary.write_text(redact(json.dumps(task, ensure_ascii=False, indent=2)) + "\n", encoding="utf-8")


def validate_download_format(prefix: bytes, path: Path, image: bool) -> None:
    """按实际签名识别尾帧；线上可能在 .png URL 返回 JPEG。"""
    if not image:
        require(prefix[4:8] == b"ftyp", "产物不是预期的 MP4/MOV；拒绝保存错误页")
        return
    formats = ((b"\x89PNG\r\n\x1a\n", "PNG", {".png"}),
               (b"\xff\xd8\xff", "JPEG", {".jpg", ".jpeg"}))
    for signature, label, suffixes in formats:
        if prefix.startswith(signature):
            require(not path.suffix or path.suffix.lower() in suffixes,
                    f"尾帧实际格式为 {label}，请使用 {'/'.join(sorted(suffixes))} 后缀后重试下载")
            return
    raise ValueError("尾帧不是支持的 PNG/JPEG；拒绝保存错误页")


def download_file(url: str, path: Path, timeout: float, force: bool, *, image: bool = False) -> None:
    http_url(url, https_only=True)
    opener = build_opener(MediaRedirect())
    try:
        with (staged_file(path, force) as temporary,
              opener.open(Request(url), timeout=timeout) as response,
              temporary.open("wb") as output):
            length = response.headers.get("Content-Length")
            prefix = response.read(32)
            validate_download_format(prefix, path, image)
            output.write(prefix)
            size = len(prefix)
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                size += len(chunk)
            require(length is None or size == int(length), "产物下载不完整")
    except (HTTPError, URLError, TimeoutError, HTTPException) as exc:
        raise RuntimeError(f"产物下载失败：{exc}；可按任务 ID 重试下载，无需重新生成") from exc


def download_task(task: dict[str, Any], args: argparse.Namespace) -> dict[str, str]:
    require(task.get("status") == "succeeded", f"任务未成功：{task.get('status')}；{task.get('error')}")
    content = task.get("content")
    require(isinstance(content, dict), "成功响应缺少 content")
    outputs = (("video_url", args.out, False), ("last_frame_url", args.last_frame_out, True))
    # 先核对所有 URL，避免第二个字段缺失时才发现只能交付部分产物。
    for key, path, _ in outputs:
        if path:
            require(isinstance(content.get(key), str), f"响应缺少 {key}；尾帧需创建时启用 return_last_frame")
            http_url(content[key], https_only=True)
    saved: dict[str, str] = {}
    for key, path, is_image in outputs:
        if path:
            target = Path(path).expanduser()
            try:
                download_file(content[key], target, args.http_timeout, args.force, image=is_image)
            except (ValueError, OSError, RuntimeError) as exc:
                raise RuntimeError(f"{exc}；已保存文件：{json.dumps(saved, ensure_ascii=False)}；仅重试缺失产物") from exc
            saved[key] = str(target.resolve())
    return saved


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    convenience = [getattr(args, name) for name in FIELDS - {"model", "content", "tools", "service_tier"}]
    convenience += [args.prompt, args.prompt_file, args.web_search]
    media_flags = ("first_frame", "last_frame", "reference_image", "reference_video", "reference_audio")
    convenience += [getattr(args, name) for name in media_flags]
    if args.request:
        require(not any(value is not None for value in convenience), "--request 不可与生成参数混用；请直接修改 JSON")
        return read_payload(args.request)
    require(not (args.prompt and args.prompt_file), "--prompt 与 --prompt-file 二选一")
    prompt = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else args.prompt
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}] if prompt is not None else []
    for role in media_flags:
        values = getattr(args, role)
        kind = "image" if role.endswith("frame") else role.removeprefix("reference_")
        for source in ([values] if isinstance(values, str) else values or []):
            content.append(media_item(source, kind, role))
    body = {name: getattr(args, name) for name in FIELDS - {"model", "content", "tools", "service_tier"}
            if getattr(args, name) is not None}
    body["content"] = content
    if args.web_search:
        body["tools"] = [{"type": "web_search"}]
    return validate_payload(body)


def list_query(args: argparse.Namespace) -> list[tuple[str, str]]:
    for value in (args.page_num, args.page_size):
        require(1 <= value <= 500, "page_num/page_size 必须在 [1, 500]")
    query = [("page_num", str(args.page_num)), ("page_size", str(args.page_size))]
    for key, value in (("status", args.status), ("model", args.endpoint_id), ("service_tier", args.service_tier)):
        if value is not None:
            query.append((f"filter.{key}", value))
    query.extend(("filter.task_ids", task_id) for task_id in args.task_id or [])
    return query


def preflight_files(args: argparse.Namespace) -> None:
    paths = [getattr(args, key, None) for key in ("out", "last_frame_out", "receipt")]
    resolved = [Path(path).expanduser().resolve() for path in paths if path]
    require(len(set(resolved)) == len(resolved), "视频、尾帧和回执必须使用不同路径")
    for path in paths:
        if path:
            check_output(Path(path).expanduser(), args.force)


def create_task(args: argparse.Namespace) -> dict[str, Any]:
    body = build_payload(args)
    if args.dry_run:
        return {"method": "POST", "url": API_URL, "body": preview_payload(body)}
    if args.last_frame_out:
        require(body.get("return_last_frame") is True, "--last-frame-out 需要 return_last_frame=true")
    if args.out:
        require(Path(args.out).suffix.lower() == "." + body.get("output_format", "mp4"), "输出文件扩展名必须与 output_format 一致")
    preflight_files(args)
    client = Client(args.http_timeout)
    created = client.request("POST", body=body)
    task_id = created.get("id")
    require(isinstance(task_id, str) and bool(task_id), "创建响应缺少任务 ID；请先查询列表，勿盲目重提")
    emit({"id": task_id, "status": "submitted"}, error=True)
    save_receipt(args.receipt, created, args.force)
    if not (args.wait or args.out or args.last_frame_out):
        return created
    task = wait_task(client, task_id, args.wait_timeout, args.poll_interval)
    save_receipt(args.receipt, task, True)
    if task.get("status") == "succeeded" and (args.out or args.last_frame_out):
        task["local_files"] = download_task(task, args)
        save_receipt(args.receipt, task, True)
    return task


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "create":
        return create_task(args)
    if args.command == "download":
        require(bool(args.out or args.last_frame_out), "download 需要 --out 或 --last-frame-out")
        preflight_files(args)
    client = Client(args.http_timeout)
    if args.command == "list":
        return client.request("GET", query=list_query(args))
    if args.command == "delete":
        result = client.request("DELETE", task_path(args.id))
        return {"id": args.id, "delete_response": result}
    if args.command == "wait":
        return wait_task(client, args.id, args.wait_timeout, args.poll_interval)
    task = client.get(args.id)
    if args.command == "download":
        task["local_files"] = download_task(task, args)
    return task


def add_creation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request", help="完整官方请求 JSON 文件；model 可省略，不可改为其他模型")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--first-frame")
    parser.add_argument("--last-frame")
    for kind in ("image", "video", "audio"):
        parser.add_argument(f"--reference-{kind}", action="append")
    parser.add_argument("--omni-reference-task-type", choices=TASK_TYPES)
    parser.add_argument("--resolution", choices=("480p", "720p", "1080p"))
    parser.add_argument("--ratio", choices=RATIOS)
    parser.add_argument("--output-format", choices=("mp4", "mov"))
    for name in ("duration", "execution-expires-after", "priority"):
        parser.add_argument(f"--{name}", type=int)
    for name in ("generate-audio", "watermark", "return-last-frame", "web-search"):
        parser.add_argument(f"--{name}", action=argparse.BooleanOptionalAction)
    parser.add_argument("--callback-url")
    parser.add_argument("--safety-identifier")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--receipt", help="立即保存任务 ID，等待结束后更新为任务结果")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"官方 Seedance 视频任务 CLI；固定模型 {MODEL}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("create", "get", "list", "delete", "wait", "download"):
        command = commands.add_parser(name)
        command.add_argument("--http-timeout", type=float, default=60)
        if name in {"get", "delete", "wait", "download"}:
            command.add_argument("id")
        if name in {"create", "wait"}:
            command.add_argument("--wait-timeout", type=float, default=600)
            command.add_argument("--poll-interval", type=float, default=10)
        if name in {"create", "download"}:
            command.add_argument("--out")
            command.add_argument("--last-frame-out")
            command.add_argument("--force", action="store_true")
        if name == "create":
            add_creation_options(command)
        if name == "list":
            command.add_argument("--page-num", type=int, default=1)
            command.add_argument("--page-size", type=int, default=20)
            command.add_argument("--status", choices=("queued", "running", "cancelled", "succeeded", "failed"))
            command.add_argument("--endpoint-id", help="filter.model 是 ep- 推理接入点 ID，非 Model ID")
            command.add_argument("--service-tier", choices=("default", "flex"))
            command.add_argument("--task-id", action="append")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        for key in ("http_timeout", "wait_timeout", "poll_interval"):
            value = getattr(args, key, 1)
            require(math.isfinite(value) and value > 0, f"{key} 必须为有限正数")
        require(getattr(args, "poll_interval", 1) <= 60, "poll_interval 不能超过 60 秒")
        result = run(args)
        emit(result)
        return 1 if args.command in {"create", "wait"} and result.get("status") in TERMINAL - {"succeeded"} else 0
    except (ValueError, OSError, RuntimeError) as exc:
        emit({"error": str(exc)}, error=True)
        return 1
    except KeyboardInterrupt:
        emit({"error": "本地操作已中断；已提交的任务不会自动取消，可通过已输出的 ID 查询"}, error=True)
        return 130


if __name__ == "__main__":
    sys.exit(main())
