#!/usr/bin/env python3
"""Seedream 5.0 Pro CLI；Python 3.10+，依赖 Pillow。"""

from __future__ import annotations

import argparse
import math
import sys
from http.client import HTTPException
from pathlib import Path
from typing import Any

from seedream_io import (
    encode_json,
    post_images,
    prepare_output,
    read_json,
    save_images,
    save_json,
)
from seedream_payload import prepare_payload, preview_payload, require


def generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request", type=Path, help="完整官方请求 JSON；不可与生成参数混用")
    parser.add_argument("--prompt")
    parser.add_argument("--image", action="append", help="本地图片、URL 或 Data URI，按图号顺序重复传入")
    parser.add_argument("--size")
    parser.add_argument("--optimize", choices=["standard", "fast"])
    parser.add_argument("--output-format", choices=["jpeg", "png"])
    parser.add_argument("--background", choices=["opaque", "transparent"])
    parser.add_argument("--response-format", choices=["url", "b64_json"])
    parser.add_argument("--watermark", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--dry-run", action="store_true", help="仅校验并预览，不需要密钥且不联网")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name, help_text in [("generate", "文生图"), ("edit", "图生图/参考编辑"),
                            ("layers", "图层拆分"), ("download", "从保存的响应恢复下载，不重新生成")]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--out", type=Path, help="全新输出目录，拒绝覆盖已有目录")
        command.add_argument("--timeout", type=float, default=300, help="单次网络操作超时秒数，默认 300")
        if name == "download":
            command.add_argument("--response", type=Path, required=True)
        else:
            generation_arguments(command)
    return root


def request_body(args: argparse.Namespace) -> dict[str, Any]:
    names = ("prompt", "image", "size", "output_format", "background", "response_format", "watermark")
    supplied = {name: getattr(args, name) for name in names if getattr(args, name) is not None}
    if args.optimize is not None:
        supplied["optimize_prompt_options"] = {"mode": args.optimize}
    if args.request:
        require(not supplied, "--request 不能与生成参数混用")
        return prepare_payload(read_json(args.request.expanduser()), args.command)
    return prepare_payload(supplied, args.command, local=True)


def execute(args: argparse.Namespace) -> dict[str, Any]:
    require(math.isfinite(args.timeout) and args.timeout > 0, "timeout 必须是有限正数")
    if args.command == "download":
        response = read_json(args.response.expanduser())
        require(args.out is not None, "download 必须指定 --out 全新目录")
        directory = prepare_output(args.out)
        save_json(directory / "response.json", response)
        return save_images(response, directory, args.timeout)
    body = request_body(args)
    if args.dry_run:
        return {"dry_run": True, "request": preview_payload(body),
                "note": "URL 图片未下载检查；其尺寸、格式、透明通道及可达性仍需服务端验证"}
    require(args.out is not None, "生成时必须指定 --out 全新目录")
    directory = prepare_output(args.out)
    save_json(directory / "request-preview.json", preview_payload(body))
    try:
        response = post_images(body, directory, args.timeout)
        return save_images(response, directory, args.timeout, layers=args.command == "layers",
                           transparent=body["background"] == "transparent")
    except (ValueError, RuntimeError, OSError, HTTPException) as exc:
        save_json(directory / "failure.json", {"error": str(exc), "automatic_retry": False})
        raise


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = execute(args)
    except (ValueError, RuntimeError, OSError, HTTPException) as exc:
        print(encode_json({"error": str(exc)}), file=sys.stderr, end="")
        return 1
    print(encode_json(result), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
