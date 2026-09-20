"""Seedream 5.0 Pro 请求校验与本地图片编码。"""

from __future__ import annotations

import base64
import importlib.util
import io
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from PIL import Image

# HEIC/HEIF 解码可选；未安装时由图片校验给出明确安装提示。
if importlib.util.find_spec("pillow_heif") is not None:
    import pillow_heif

    pillow_heif.register_heif_opener()

MODEL = "doubao-seedream-5-0-pro-260628"
FIELDS = {"model", "prompt", "image", "layer_decomposition", "size",
          "optimize_prompt_options", "output_format", "background", "response_format", "watermark"}
FORMATS = {"JPEG": "jpeg", "PNG": "png", "WEBP": "webp", "BMP": "bmp",
           "TIFF": "tiff", "GIF": "gif", "HEIF": "heif", "HEIC": "heic"}
MAX_INPUT_BYTES = 30 * 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def http_url(value: Any, *, https_only: bool = False) -> str:
    require(isinstance(value, str), "图片 URL 必须是字符串")
    parsed = urlsplit(value)
    schemes = {"https"} if https_only else {"http", "https"}
    require(parsed.scheme in schemes and bool(parsed.hostname), "图片 URL 协议或域名无效")
    require(not parsed.username and not parsed.password, "图片 URL 不得包含账号或密码")
    require(not any(c.isspace() or ord(c) < 32 for c in value), "图片 URL 含空白或控制字符")
    return value


def inspect_image(raw: bytes) -> dict[str, Any]:
    """完整解码验证，保持原始像素、方向及透明通道，不自动转码。"""
    try:
        with Image.open(io.BytesIO(raw)) as image:
            info = {"format": image.format, "width": image.width, "height": image.height,
                    "alpha": "A" in image.getbands() or "transparency" in image.info}
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError("无法完整解码图片；HEIC/HEIF 本地输入需要 pillow-heif 解码插件") from exc
    return info


def check_image(raw: bytes, *, layers: bool, transparent: bool) -> dict[str, Any]:
    require(0 < len(raw) <= MAX_INPUT_BYTES, "每张输入图片须非空且不超过 30 MB")
    info = inspect_image(raw)
    width, height = info["width"], info["height"]
    allowed = {"JPEG", "PNG"} if layers else set(FORMATS)
    require(info["format"] in allowed, "输入图片格式不适用于当前模式")
    require(width > 14 and height > 14, "输入图片宽高必须大于 14 像素")
    require((262144 if layers else 196) <= width * height <= 36000000, "输入图片像素总数超限")
    require(1 / 16 <= width / height <= 16, "输入图片宽高比须在 1/16 到 16 之间")
    if transparent:
        require(info["format"] != "JPEG" and info["alpha"], "透明编辑需要已有透明通道的输入图片")
    return info


def prepare_image(value: Any, *, layers: bool, transparent: bool, local: bool) -> str:
    require(isinstance(value, str) and bool(value), "image 元素必须是非空字符串")
    if value.startswith(("https://", "http://")):
        return http_url(value)
    if value.startswith("data:"):
        match = re.fullmatch(r"data:image/(jpeg|png|webp|bmp|tiff|gif|heic|heif);base64,(.+)", value)
        require(match is not None, "Data URI 必须使用小写图片格式及 Base64 编码")
        assert match is not None
        require(len(match[2]) <= (MAX_INPUT_BYTES + 2) // 3 * 4, "Base64 输入超过 30 MB")
        raw = base64.b64decode(match[2], validate=True)
        info = check_image(raw, layers=layers, transparent=transparent)
        aliases = {"heic", "heif"} if info["format"] in {"HEIF", "HEIC"} else {FORMATS[info["format"]]}
        require(match[1] in aliases, "Data URI 声明格式与实际图片不符")
        return value
    require(local, "请求 JSON 的 image 仅支持 URL/Data URI；本地路径请使用 --image")
    path = Path(value).expanduser()
    require(path.is_file(), "本地输入图片不存在或不是文件")
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    info = check_image(raw, layers=layers, transparent=transparent)
    return f"data:image/{FORMATS[info['format']]};base64,{base64.b64encode(raw).decode('ascii')}"


def validate_size(size: Any, *, layers: bool) -> None:
    require(isinstance(size, str), "size 必须是字符串")
    if size in {"1K", "1.5K", "2K"} or layers and size == "auto":
        return
    require(not layers, "图层拆分 size 仅支持 auto/1K/1.5K/2K")
    require(re.fullmatch(r"[1-9]\d{0,5}x[1-9]\d{0,5}", size) is not None,
            "size 仅支持 1K/1.5K/2K 或 WIDTHxHEIGHT")
    width, height = map(int, size.split("x"))
    require(921600 <= width * height <= 4624220, "输出像素总数须在 921600 到 4624220 之间")
    require(1 / 16 <= width / height <= 16, "输出宽高比须在 1/16 到 16 之间")


def validate_options(body: dict[str, Any], layers: bool) -> None:
    enums = {"background": {"opaque", "transparent"}, "output_format": {"jpeg", "png"},
             "response_format": {"url", "b64_json"}}
    for field, choices in enums.items():
        value = body.get(field)
        require(isinstance(value, str) and value in choices, f"{field} 值不受支持")
    require(type(body["watermark"]) is bool, "watermark 必须是布尔值")
    options = body["optimize_prompt_options"]
    require(isinstance(options, dict) and set(options) == {"mode"}, "提示词优化仅支持 mode 字段")
    require(isinstance(options["mode"], str) and options["mode"] in {"standard", "fast"},
            "提示词优化 mode 仅支持 standard/fast")
    validate_size(body["size"], layers=layers)


def prepare_payload(source: Any, mode: str, *, local: bool = False) -> dict[str, Any]:
    require(isinstance(source, dict), "请求必须是 JSON 对象")
    require(not set(source) - FIELDS, f"Pro 不支持这些字段：{', '.join(sorted(set(source) - FIELDS))}")
    layers = mode == "layers"
    require(mode in {"generate", "edit", "layers"}, "未知生成模式")
    require(source.get("model", MODEL) == MODEL, f"模型固定为 {MODEL}")
    require(type(source.get("layer_decomposition", layers)) is bool, "layer_decomposition 必须是布尔值")
    require(source.get("layer_decomposition", layers) == layers, "layer_decomposition 与命令不一致")
    transparent = source.get("background", "opaque") == "transparent"
    body = {"model": MODEL, "layer_decomposition": layers, "size": "auto" if layers else "2K",
            "optimize_prompt_options": {"mode": "standard"}, "background": "opaque",
            "output_format": "png" if transparent else "jpeg", "response_format": "url",
            "watermark": True, **source}
    if "prompt" in body:
        require(isinstance(body["prompt"], str) and bool(body["prompt"].strip()), "prompt 必须是非空字符串")
    require(layers or "prompt" in body, "文生图/图生图必须提供 prompt")
    validate_options(body, layers)
    images = body.get("image", [])
    images = [images] if isinstance(images, str) else images
    require(isinstance(images, list), "image 必须是字符串或字符串数组")
    limits = {"generate": (0, 0), "edit": (1, 10), "layers": (1, 1)}
    lower, upper = limits[mode]
    require(lower <= len(images) <= upper, f"{mode} 要求 {lower}–{upper} 张输入图片")
    if transparent:
        require(len(images) == 1, "透明模式要求单张带透明通道的参考图")
        require(body["output_format"] == "png", "透明输出必须使用 PNG")
    encoded = [prepare_image(v, layers=layers, transparent=transparent, local=local) for v in images]
    if encoded:
        body["image"] = encoded[0] if len(encoded) == 1 else encoded
    else:
        body.pop("image", None)
    return body


def preview_payload(body: dict[str, Any]) -> dict[str, Any]:
    preview = dict(body)
    if "image" in body:
        values = body["image"] if isinstance(body["image"], list) else [body["image"]]
        preview["image"] = [v.split(",", 1)[0] + ",[BASE64 OMITTED]" if v.startswith("data:") else v
                            for v in values]
    return preview
