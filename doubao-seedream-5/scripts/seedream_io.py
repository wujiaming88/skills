"""同步 HTTP 调用、完整响应留存和可恢复的图片下载。"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from seedream_payload import http_url, inspect_image, require

API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
KEY_ENV = "SEEDREAM_API_KEY"
# 本地资源保护值，不是官方 API 的图片规格限制。
MAX_RESPONSE_BYTES = 512 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024 * 1024


def redact(text: str) -> str:
    secret = os.environ.get(KEY_ENV, "")
    return text.replace(secret, "[REDACTED]") if secret else text


def encode_json(value: Any) -> str:
    return redact(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)) + "\n"


def save_json(path: Path, value: Any) -> None:
    path.write_text(encode_json(value), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    require(path.stat().st_size <= MAX_RESPONSE_BYTES, "JSON 文件超过本地 512 MB 限制")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "JSON 内容必须是对象")
    return value


def prepare_output(path: Path) -> Path:
    """先占用全新目录，写权限或碰撞问题在付费请求前暴露。"""
    path = path.expanduser().absolute()
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    with tempfile.TemporaryFile(dir=path):
        pass
    return path


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        raise ValueError("认证 API 返回重定向，已阻止 Bearer 转发")


class MediaRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> Request | None:
        http_url(newurl, https_only=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_bounded(response: Any, maximum: int) -> bytes:
    length = response.headers.get("Content-Length")
    require(length is None or 0 <= int(length) <= maximum, "响应大小超过本地资源限制")
    raw = response.read(maximum + 1)
    require(len(raw) <= maximum, "响应大小超过本地资源限制")
    require(length is None or len(raw) == int(length), "响应下载不完整")
    return raw


def post_images(body: dict[str, Any], directory: Path, timeout: float) -> dict[str, Any]:
    key = os.environ.get(KEY_ENV, "")
    require(bool(key.strip()), f"未配置 {KEY_ENV}；请在本地安全设置环境变量")
    require(key.isascii() and not any(c.isspace() or ord(c) < 33 for c in key), f"{KEY_ENV} 格式无效")
    request = Request(API_URL, data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      method="POST")
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = read_bounded(response, MAX_RESPONSE_BYTES)
    except HTTPError as exc:
        detail = redact(exc.read(8192).decode("utf-8", errors="replace"))
        raise RuntimeError(f"HTTP {exc.code}; request_id={exc.headers.get('X-Request-Id', '')}; {detail}") from exc
    except (URLError, TimeoutError, OSError, HTTPException, ValueError) as exc:
        raise RuntimeError(f"生成结果未知：{exc}；未自动重试，不要盲目再次提交") from exc
    # 先保存响应，再做业务判定；下载失败不必重新付费生成。
    (directory / "response.json").write_text(redact(raw.decode("utf-8", errors="replace")), encoding="utf-8")
    try:
        result = json.loads(raw)
    except ValueError as exc:
        raise RuntimeError("API 返回非 JSON 内容，已留存；生成结果未知，不要盲目重新提交") from exc
    require(isinstance(result, dict), "API 响应必须是 JSON 对象")
    return result


def fetch_image(url: str, timeout: float) -> bytes:
    http_url(url, https_only=True)
    # 使用独立请求，不携带生成 API 的认证头。
    with build_opener(MediaRedirect()).open(Request(url), timeout=timeout) as response:
        return read_bounded(response, MAX_OUTPUT_BYTES)


def layer_response(data: list[dict[str, Any]]) -> bool:
    return len(data) > 1 or any("bounding_box" in item or item.get("z_index") not in (None, 0) for item in data)


def response_items(response: dict[str, Any], *, layers: bool | None = None) -> list[dict[str, Any]]:
    require(not response.get("error"), f"API 错误：{response.get('error')}")
    data = response.get("data")
    require(isinstance(data, list) and 1 <= len(data) <= 17, "响应 data 必须包含 1–17 张图片")
    require(all(isinstance(item, dict) for item in data), "响应 data 元素必须是对象")
    if layers is None:
        layers = layer_response(data)
    if layers is False:
        require(len(data) == 1, "Pro 普通生成应返回一张图片")
    if layers is True:
        indices = [item.get("z_index") for item in data]
        require(all(type(z) is int and 0 <= z <= 16 for z in indices), "图层 z_index 无效")
        require(0 in indices and len(set(indices)) == len(indices), "缺少底图或图层 z_index 重复")
        for item in data:
            if item["z_index"] > 0:
                bounds = item.get("bounding_box")
                require(isinstance(bounds, dict), "图层 bounding_box 必须是对象")
                box = bounds.get("absolute")
                require(isinstance(box, list) and len(box) == 4 and all(type(n) is int for n in box),
                        "图层缺少有效 absolute bounding_box")
                require(0 <= box[0] < box[2] and 0 <= box[1] < box[3], "图层 bounding_box 范围无效")
    return data


def item_bytes(item: dict[str, Any], timeout: float) -> bytes:
    require(not item.get("error"), f"图片错误：{item.get('error')}")
    if "b64_json" in item:
        encoded = item["b64_json"]
        require(isinstance(encoded, str) and len(encoded) <= (MAX_OUTPUT_BYTES + 2) // 3 * 4,
                "图片 Base64 无效或超过本地限制")
        return base64.b64decode(encoded, validate=True)
    require(isinstance(item.get("url"), str), "图片响应缺少 url/b64_json")
    return fetch_image(item["url"], timeout)


def write_image(directory: Path, index: int, item: dict[str, Any], timeout: float,
                *, transparent: bool, layers: bool) -> dict[str, Any]:
    raw = item_bytes(item, timeout)
    require(0 < len(raw) <= MAX_OUTPUT_BYTES, "输出图片为空或超过本地限制")
    info = inspect_image(raw)
    require(info["format"] in {"JPEG", "PNG"}, "输出图片实际格式不是 JPEG/PNG")
    actual = info["format"].lower()
    require(item.get("output_format", actual) == actual, "响应 output_format 与实际图片不符")
    actual_size = f"{info['width']}x{info['height']}"
    require(item.get("size", actual_size) == actual_size, "响应 size 与实际图片尺寸不符")
    alpha_required = transparent or layers and item.get("z_index", 0) > 0
    require(not alpha_required or actual == "png" and info["alpha"], "预期透明 PNG，但产物无透明通道")
    path = directory / f"image-{index:02d}.{actual}"
    fd, name = tempfile.mkstemp(prefix=".image-", dir=directory)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as destination:
            destination.write(raw)
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"index": index, "file": str(path), "actual": info,
            "metadata": {k: v for k, v in item.items() if k != "b64_json"}}


def save_images(response: dict[str, Any], directory: Path, timeout: float,
                *, layers: bool | None = None, transparent: bool = False) -> dict[str, Any]:
    data = response_items(response, layers=layers)
    layered = layers is True or layers is None and layer_response(data)
    files, errors = [], []
    for index, item in enumerate(data):
        try:
            files.append(write_image(directory, index, item, timeout, transparent=transparent, layers=layered))
        except (ValueError, OSError, HTTPException) as exc:
            errors.append({"index": index, "error": redact(str(exc))})
    manifest = {"complete": not errors, "files": files, "errors": errors,
                "response": str(directory / "response.json"), "usage": response.get("usage"),
                "model": response.get("model"), "layer_decomposition": layered}
    save_json(directory / "manifest.json", manifest)
    require(not errors, f"仅成功保存 {len(files)}/{len(data)} 张图片；请查看 manifest.json，使用 download 恢复")
    return manifest
