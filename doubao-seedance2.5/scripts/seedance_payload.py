"""Seedance 2.5 请求构造与模型专属校验，仅使用 Python 标准库。"""

from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MODEL = "doubao-seedance-2-5-260628"
MAX_BODY_BYTES = 64 * 1024 * 1024
RATIOS = ("16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive")
TASK_TYPES = ("auto", "reference", "edit", "extend")
FIELDS = {
    "model", "content", "omni_reference_task_type", "resolution", "ratio",
    "duration", "generate_audio", "watermark", "output_format",
    "return_last_frame", "callback_url", "execution_expires_after",
    "priority", "safety_identifier", "tools", "service_tier",
}
UNSUPPORTED = {"seed", "frames", "camera_fixed", "draft"}
MIME_TYPES = {
    "image": {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp",
              "bmp": "bmp", "tif": "tiff", "tiff": "tiff", "gif": "gif",
              "heic": "heic", "heif": "heif"},
    "audio": {"wav": "wav", "mp3": "mp3"},
}


def require(condition: bool, message: str) -> None:
    """在请求边界拒绝无效参数，避免计费后才发现配置错误。"""
    if not condition:
        raise ValueError(message)


def http_url(value: str, *, https_only: bool = False) -> str:
    """拒绝非网络协议、URL 内嵌账号及控制字符。"""
    parsed = urlsplit(value)
    schemes = {"https"} if https_only else {"http", "https"}
    require(parsed.scheme in schemes and bool(parsed.hostname), "需要有效的公网 HTTP(S) URL")
    require(not parsed.username and not parsed.password, "URL 不允许内嵌账号或密码")
    require(not any(ord(char) < 33 for char in value), "URL 不允许空白或控制字符")
    return value


def check_media_size(kind: str, size: int) -> None:
    """图片严格小于 30 MiB，音频不超过 15 MiB。"""
    limit = (30 if kind == "image" else 15) * 1024 * 1024
    require(size > 0, "素材为空")
    require(size < limit if kind == "image" else size <= limit, f"{kind} 素材超过大小上限")


def validate_source(source: str, kind: str) -> str:
    """校验官方支持的 URL、asset ID、图片/音频 Data URI。"""
    require(isinstance(source, str) and bool(source), "素材来源必须是非空字符串")
    if source.startswith("asset://"):
        require(bool(source[8:]) and not any(c.isspace() for c in source), "asset ID 无效")
        return source
    if not source.startswith("data:"):
        return http_url(source)
    require(kind in MIME_TYPES, "视频仅支持公网 URL 或 asset://，不支持 Base64")
    header, separator, encoded = source.partition(",")
    accepted = {f"data:{kind}/{mime};base64" for mime in MIME_TYPES[kind].values()}
    if kind == "audio":
        accepted.add("data:audio/mpeg;base64")
    require(bool(separator) and header in accepted, "Data URI 的 MIME 或 Base64 格式无效")
    require(len(encoded) <= MAX_BODY_BYTES, "Base64 素材超过请求体大小限制")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("素材 Base64 编码无效") from exc
    check_media_size(kind, len(data))
    return source


def media_source(source: str, kind: str) -> str:
    """CLI 的本地图片/音频转 Data URI；视频必须事先有可访问来源。"""
    if source.startswith(("http://", "https://", "asset://", "data:")):
        return validate_source(source, kind)
    require(kind in MIME_TYPES, "本地视频请先上传到用户指定的存储，再传公网 URL 或 asset://")
    path = Path(source).expanduser()
    suffix = path.suffix.lower().lstrip(".")
    require(suffix in MIME_TYPES[kind], f"不支持的 {kind} 文件格式：{path.suffix}")
    check_media_size(kind, path.stat().st_size)
    data = path.read_bytes()
    check_media_size(kind, len(data))
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{kind}/{MIME_TYPES[kind][suffix]};base64,{encoded}"


def media_item(source: str, kind: str, role: str) -> dict[str, Any]:
    key = f"{kind}_url"
    return {"type": key, key: {"url": media_source(source, kind)}, "role": role}


def validate_content_item(item: Any) -> str:
    """返回素材角色，保留调用方的原始 content 顺序。"""
    require(isinstance(item, dict), "content 元素必须是对象")
    kind = item.get("type")
    require(isinstance(kind, str), "content.type 必须是字符串")
    if kind == "text":
        require(set(item) == {"type", "text"}, "文本元素只接受 type、text")
        require(isinstance(item["text"], str) and bool(item["text"].strip()), "提示词不能为空")
        return "text"
    roles = {"image_url": {"first_frame", "last_frame", "reference_image"},
             "video_url": {"reference_video"}, "audio_url": {"reference_audio"}}
    require(kind in roles, "content.type 仅支持 text/image_url/video_url/audio_url；2.5 不支持 draft_task")
    require(set(item) <= {"type", kind, "role"}, "素材元素包含未知字段")
    value = item.get(kind)
    require(isinstance(value, dict) and set(value) == {"url"}, f"{kind} 必须包含 url")
    validate_source(value["url"], kind.removesuffix("_url"))
    default = "first_frame" if kind == "image_url" else f"reference_{kind.removesuffix('_url')}"
    role = item.get("role", default)
    require(isinstance(role, str) and role in roles[kind], f"{kind} 的 role 无效")
    return role


def validate_content(content: Any) -> list[str]:
    require(isinstance(content, list) and bool(content), "content 必须是非空数组")
    roles = [validate_content_item(item) for item in content]
    for role, maximum in (("reference_image", 30), ("reference_video", 10), ("reference_audio", 10)):
        require(roles.count(role) <= maximum, f"{role} 最多 {maximum} 个")
    first, last = roles.count("first_frame"), roles.count("last_frame")
    require(first <= 1 and last <= 1, "首帧和尾帧各最多一张")
    require(not last or first == 1, "尾帧必须搭配首帧")
    if first:
        require(not any(r.startswith("reference_") for r in roles), "首尾帧与全模态参考素材不可混用")
    return roles


def validate_options(body: dict[str, Any]) -> None:
    choices = {"resolution": ("480p", "720p", "1080p"), "ratio": RATIOS,
               "output_format": ("mp4", "mov"), "omni_reference_task_type": TASK_TYPES,
               "service_tier": ("default",)}
    for key, values in choices.items():
        if key in body:
            require(isinstance(body[key], str) and body[key] in values, f"{key} 必须为 {values}")
    for key in ("generate_audio", "watermark", "return_last_frame"):
        if key in body:
            require(type(body[key]) is bool, f"{key} 必须是 JSON boolean")
    for key, low, high in (("duration", 4, 30), ("execution_expires_after", 3600, 259200), ("priority", 0, 9)):
        if key in body:
            value = body[key]
            valid = type(value) is int and (low <= value <= high or (key == "duration" and value == -1))
            require(valid, f"{key} 超出范围 [{low}, {high}]" + (" 或 -1" if key == "duration" else ""))
    if "tools" in body:
        require(isinstance(body["tools"], list), "tools 必须是数组")
        require(all(tool == {"type": "web_search"} for tool in body["tools"]), "仅支持 tools: [{\"type\":\"web_search\"}]")
    if "callback_url" in body:
        require(isinstance(body["callback_url"], str), "callback_url 必须是字符串")
        http_url(body["callback_url"])
    if "safety_identifier" in body:
        value = body["safety_identifier"]
        require(isinstance(value, str) and 0 < len(value) <= 64 and value.isascii() and value.isprintable(),
                "safety_identifier 需为不超过 64 字符的非空可打印 ASCII 标识，建议使用哈希")


def validate_payload(body: Any) -> dict[str, Any]:
    """固定模型，并前置校验 2.5 的互斥场景与任务约束。"""
    require(isinstance(body, dict), "请求 JSON 必须是对象")
    unsupported = set(body) & UNSUPPORTED
    require(not unsupported, f"Seedance 2.5 不支持参数：{', '.join(sorted(unsupported))}")
    unknown = set(body) - FIELDS
    require(not unknown, f"未知字段：{', '.join(sorted(unknown))}；请先核对官方 API")
    body = {"model": MODEL, **body}
    require(body["model"] == MODEL, f"模型固定为 {MODEL}，不允许覆盖")
    roles = validate_content(body.get("content"))
    validate_options(body)
    if body.get("tools"):
        require(all(role == "text" for role in roles), "联网搜索仅适用于纯文本输入")
    task_type = body.get("omni_reference_task_type", "auto")
    if "omni_reference_task_type" in body:
        require(any(r.startswith("reference_") for r in roles), "omni_reference_task_type 仅用于全模态参考任务")
    if task_type in {"edit", "extend"}:
        require("reference_video" in roles, f"{task_type} 必须有参考视频")
    if "first_frame" in roles or task_type in {"edit", "extend"}:
        require(body.get("ratio", "adaptive") == "adaptive", "首尾帧/编辑/延长任务的 ratio 必须为 adaptive")
        body.setdefault("ratio", "adaptive")
    if task_type == "edit":
        require(body.get("duration", -1) == -1, "编辑任务的 duration 必须为 -1")
        body.setdefault("duration", -1)
    require(len(encode_payload(body)) <= MAX_BODY_BYTES, "请求体超过 64 MiB，请改用 URL 或 asset://")
    return body


def encode_payload(body: dict[str, Any]) -> bytes:
    return json.dumps(body, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def read_payload(path: str) -> dict[str, Any]:
    file = Path(path).expanduser()
    require(file.stat().st_size <= MAX_BODY_BYTES, "请求文件超过 64 MiB")
    return validate_payload(json.loads(file.read_text(encoding="utf-8")))


def preview_payload(value: Any) -> Any:
    """预览不输出素材 Base64，避免日志膨胀和暴露原始素材。"""
    if isinstance(value, dict):
        return {key: preview_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [preview_payload(item) for item in value]
    if isinstance(value, str) and value.startswith("data:"):
        return value.partition(",")[0] + ",<omitted>"
    return value
