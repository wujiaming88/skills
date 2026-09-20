"""使用本地 HTTP 服务和真实图片文件验证契约；不调用付费模型。"""

from __future__ import annotations

import base64
import io
import json
import os
import secrets
import tempfile
import threading
import unittest
from collections import deque
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import patch
from urllib.request import Request

import seedream
import seedream_io as transport
import seedream_payload as payload
from PIL import Image


def picture(format: str = "PNG", mode: str = "RGBA", size: tuple[int, int] = (512, 512)) -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size).save(buffer, format=format)
    return buffer.getvalue()


def data_uri(raw: bytes, format: str = "png") -> str:
    return f"data:image/{format};base64,{base64.b64encode(raw).decode()}"


def image_item(raw: bytes | None = None, **extra: Any) -> dict[str, Any]:
    return {"b64_json": base64.b64encode(raw if raw is not None else picture()).decode(), **extra}


class Handler(BaseHTTPRequestHandler):
    responses: ClassVar[deque[tuple[int, bytes | dict[str, Any], dict[str, str]]]] = deque()
    requests: ClassVar[list[dict[str, Any]]] = []

    def handle_request(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.requests.append({"method": self.command, "path": self.path,
                              "headers": dict(self.headers), "body": json.loads(body) if body else None})
        status, response, headers = self.responses.popleft() if self.responses else (500, {}, {})
        raw = response if isinstance(response, bytes) else json.dumps(response).encode()
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        if "Content-Length" not in headers:
            self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        self.handle_request()

    def do_GET(self) -> None:
        self.handle_request()

    def log_message(self, format: str, *args: object) -> None:
        """避免把临时测试凭据输出到控制台。"""


class PayloadTest(unittest.TestCase):
    def test_defaults_and_prompt_preserved(self) -> None:
        text = "海报文字：你好 Hello مرحبا" * 40
        body = payload.prepare_payload({"prompt": text}, "generate")
        self.assertEqual(body["model"], "doubao-seedream-5-0-pro-260628")
        self.assertEqual(body["prompt"], text)
        self.assertEqual(body["size"], "2K")
        self.assertTrue(body["watermark"])
        self.assertNotIn("image", body)

    def test_all_ten_fields_and_image_order(self) -> None:
        images = [f"https://example.com/{i}.png" for i in range(10)]
        body = {"model": payload.MODEL, "prompt": "融合图1与图10", "image": images,
                "layer_decomposition": False, "size": "1.5K", "watermark": False,
                "background": "opaque", "output_format": "png", "response_format": "b64_json",
                "optimize_prompt_options": {"mode": "fast"}}
        self.assertEqual(payload.prepare_payload(body, "edit"), body)
        self.assertEqual(set(body), payload.FIELDS)

    def test_reject_unsupported_fields(self) -> None:
        fields = ["n", "seed", "mask", "quality", "strength", "negative_prompt", "guidance_scale",
                  "tools", "stream", "sequential_image_generation", "sequential_image_generation_options"]
        for field in fields:
            with self.subTest(field=field), self.assertRaises(ValueError):
                payload.prepare_payload({"prompt": "画猫", field: False}, "generate")

    def test_reject_invalid_types_and_model(self) -> None:
        options = [{"model": "other"}, {"watermark": 1}, {"background": []}, {"size": None},
                   {"layer_decomposition": 0}, {"prompt": " "}, {"prompt": 42},
                   {"optimize_prompt_options": {"mode": "quality"}}, {"output_format": "webp"},
                   {"optimize_prompt_options": {"mode": "standard", "extra": True}}]
        for option in options:
            with self.subTest(option=option), self.assertRaises(ValueError):
                payload.prepare_payload({"prompt": "画猫", **option}, "generate")

    def test_image_count_and_mode_mismatch(self) -> None:
        uri = "https://example.com/input.png"
        for mode, count in [("generate", 1), ("edit", 0), ("edit", 11), ("layers", 0), ("layers", 2)]:
            with self.subTest(mode=mode, count=count), self.assertRaises(ValueError):
                payload.prepare_payload({"prompt": "改图", "image": [uri] * count}, mode)
        with self.assertRaises(ValueError):
            payload.prepare_payload({"prompt": "改图", "image": uri, "layer_decomposition": True}, "edit")

    def test_normal_size_boundaries(self) -> None:
        for size in ["1K", "1.5K", "2K", "960x960", "4096x256", "256x4096", "2150x2150"]:
            with self.subTest(size=size):
                payload.validate_size(size, layers=False)
        for size in ["4K", "3K", "auto", "959x960", "2151x2150", "4097x256", "256x4097"]:
            with self.subTest(size=size), self.assertRaises(ValueError):
                payload.validate_size(size, layers=False)

    def test_layers_optional_prompt_and_tiers(self) -> None:
        body = payload.prepare_payload({"image": data_uri(picture())}, "layers")
        self.assertTrue(body["layer_decomposition"])
        self.assertEqual(body["size"], "auto")
        self.assertNotIn("prompt", body)
        for size in ["auto", "1K", "1.5K", "2K"]:
            payload.validate_size(size, layers=True)
        with self.assertRaises(ValueError):
            payload.validate_size("1024x1024", layers=True)

    def test_local_input_unchanged_and_preview_redacted(self) -> None:
        raw = picture()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "输入.png"
            path.write_bytes(raw)
            body = payload.prepare_payload({"prompt": "编辑", "image": str(path)}, "edit", local=True)
        self.assertEqual(body["image"], data_uri(raw))
        self.assertNotIn(base64.b64encode(raw).decode(), json.dumps(payload.preview_payload(body)))

    def test_data_uri_and_path_rejection(self) -> None:
        for image in ["data:image/PNG;base64,AAAA", data_uri(picture(), "jpeg"),
                      "data:image/png;base64,!!!", "some/local/path.png", None]:
            with self.subTest(image=str(image)[:50]), self.assertRaises(ValueError):
                payload.prepare_payload({"prompt": "编辑", "image": image}, "edit")

    def test_transparent_rules(self) -> None:
        transparent = {"prompt": "改颜色", "background": "transparent", "image": data_uri(picture())}
        body = payload.prepare_payload(transparent, "edit")
        self.assertEqual(body["output_format"], "png")
        for extra in [{"image": data_uri(picture("JPEG", "RGB"), "jpeg")},
                      {"image": data_uri(picture(mode="RGB"))}, {"output_format": "jpeg"},
                      {"image": [transparent["image"]] * 2}]:
            with self.subTest(extra=str(extra)[:40]), self.assertRaises(ValueError):
                payload.prepare_payload({**transparent, **extra}, "edit")
        with self.assertRaises(ValueError):
            payload.prepare_payload({"prompt": "透明猫", "background": "transparent"}, "generate")

    def test_input_formats_and_limits(self) -> None:
        for format in ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF"]:
            with self.subTest(format=format):
                payload.check_image(picture(format, "RGB"), layers=False, transparent=False)
        for raw, layers in [(picture(size=(14, 20)), False), (picture(size=(600, 20)), False),
                            (picture(size=(511, 512)), True), (picture("WEBP"), True), (b"bad", False)]:
            with self.subTest(layers=layers, length=len(raw)), self.assertRaises(ValueError):
                payload.check_image(raw, layers=layers, transparent=False)
        with patch.object(payload, "MAX_INPUT_BYTES", 10), self.assertRaises(ValueError):
            payload.check_image(picture(), layers=False, transparent=False)

    def test_url_rules(self) -> None:
        payload.http_url("http://example.com/a.png")
        for url in ["file:///tmp/a", "https://u:p@example.com/a", "https://", "https://example.com/a b"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                payload.http_url(url)

    @unittest.skipUnless(payload.importlib.util.find_spec("pillow_heif"), "可选HEIF插件未安装")
    def test_heif_decoding_and_mime_aliases(self) -> None:
        raw = picture("HEIF", "RGB")
        for format in ["heic", "heif"]:
            body = payload.prepare_payload({"prompt": "调光", "image": data_uri(raw, format)}, "edit")
            self.assertEqual(body["image"], data_uri(raw, format))


class IntegrationTest(unittest.TestCase):
    server: ClassVar[ThreadingHTTPServer]
    thread: ClassVar[threading.Thread]
    base: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        Handler.requests, Handler.responses = [], deque()
        self.key = secrets.token_urlsafe(24)
        for setting in [patch.dict(os.environ, {transport.KEY_ENV: self.key}, clear=True),
                        patch.object(transport, "API_URL", self.base + "/api/v3/images/generations")]:
            setting.start()
            self.addCleanup(setting.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.out = self.root / "result"

    def queue(self, body: bytes | dict[str, Any], status: int = 200, **headers: str) -> None:
        Handler.responses.append((status, body, headers))

    def cli(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = seedream.main(list(args))
        self.assertNotIn(self.key, stdout.getvalue() + stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue()

    def generate(self, *args: str) -> tuple[int, str, str]:
        return self.cli("generate", "--prompt", "中文招贴", "--out", str(self.out), *args)

    def test_real_post_and_b64_delivery(self) -> None:
        self.queue({"data": [image_item(size="512x512", output_format="png")], "usage": {"total_tokens": 42}})
        code, stdout, _ = self.generate("--response-format", "b64_json", "--no-watermark")
        self.assertEqual(code, 0)
        sent = Handler.requests[0]
        self.assertEqual(sent["path"], "/api/v3/images/generations")
        self.assertEqual(sent["headers"]["Authorization"], f"Bearer {self.key}")
        self.assertEqual(sent["headers"]["Content-Type"], "application/json")
        self.assertEqual(sent["body"]["model"], payload.MODEL)
        self.assertFalse(sent["body"]["watermark"])
        self.assertEqual((self.out / "image-00.png").read_bytes(), picture())
        self.assertEqual(json.loads(stdout)["usage"]["total_tokens"], 42)

    def test_edit_posts_data_uri(self) -> None:
        source = self.root / "source.png"
        source.write_bytes(picture())
        self.queue({"data": [image_item()]})
        code, _, _ = self.cli("edit", "--image", str(source), "--prompt", "图1<point>500 500</point>换成花",
                              "--background", "transparent", "--out", str(self.out))
        self.assertEqual(code, 0)
        self.assertEqual(Handler.requests[0]["body"]["image"], data_uri(picture()))
        self.assertEqual(Handler.requests[0]["body"]["output_format"], "png")

    def test_layer_metadata_and_all_files_preserved(self) -> None:
        base = image_item(picture("JPEG", "RGB"), z_index=0, output_format="jpeg")
        layer = image_item(z_index=1, output_format="png", name="../标题", description="独立文字",
                           bounding_box={"absolute": [1, 2, 101, 52], "normalized": [2, 4, 197, 102]})
        response = {"data": [base, layer], "usage": {"generated_images": 2}, "future_field": {"x": 7}}
        self.queue(response)
        code, stdout, _ = self.cli("layers", "--image", "https://example.com/a.png", "--out", str(self.out))
        self.assertEqual(code, 0)
        manifest = json.loads(stdout)
        self.assertEqual(len(manifest["files"]), 2)
        self.assertEqual(manifest["files"][1]["metadata"]["bounding_box"], layer["bounding_box"])
        self.assertTrue((self.out / "image-00.jpeg").is_file())
        self.assertEqual(transport.read_json(self.out / "response.json"), response)
        self.assertFalse((self.root / "标题").exists())

    def test_raw_request_and_conflict(self) -> None:
        request = self.root / "request.json"
        request.write_text(json.dumps({"prompt": "油画", "size": "1.5K"}))
        code, stdout, _ = self.cli("generate", "--request", str(request), "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["request"]["size"], "1.5K")
        code, _, _ = self.cli("generate", "--request", str(request), "--prompt", "冲突", "--dry-run")
        self.assertEqual(code, 1)
        self.assertEqual(Handler.requests, [])

    def test_dry_run_no_key_or_network(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            code, stdout, _ = self.generate("--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stdout)["dry_run"])
        self.assertFalse(self.out.exists())
        self.assertEqual(Handler.requests, [])

    def test_only_seedream_key_accepted(self) -> None:
        with patch.dict(os.environ, {"ARK_API_KEY": self.key, "SEEDANCE_API_KEY": self.key}, clear=True):
            code, _, stderr = self.generate()
        self.assertEqual(code, 1)
        self.assertIn("SEEDREAM_API_KEY", stderr)
        self.assertEqual(Handler.requests, [])

    def test_collision_before_post(self) -> None:
        self.out.mkdir()
        preserved = self.out / "keep.txt"
        preserved.write_text("keep")
        code, _, _ = self.generate()
        self.assertEqual(code, 1)
        self.assertEqual(preserved.read_text(), "keep")
        self.assertEqual(Handler.requests, [])

    def test_rejected_inputs_before_post(self) -> None:
        for args in [("--size", "4K"), ("--timeout", "nan"), ("--background", "transparent")]:
            with self.subTest(args=args):
                self.assertEqual(self.generate(*args)[0], 1)
        self.assertEqual(Handler.requests, [])

    def test_http_error_redaction_no_retry(self) -> None:
        self.queue({"error": {"message": self.key}}, status=429)
        code, _, stderr = self.generate()
        self.assertEqual(code, 1)
        self.assertIn("HTTP 429", stderr)
        self.assertEqual(len(Handler.requests), 1)
        self.assertNotIn(self.key, (self.out / "failure.json").read_text())

    def test_api_redirect_blocked(self) -> None:
        self.queue({}, status=307, Location=self.base + "/redirected")
        self.assertEqual(self.generate()[0], 1)
        self.assertEqual(len(Handler.requests), 1)

    def test_api_timeout_no_retry(self) -> None:
        with patch.object(transport, "build_opener") as opener:
            opener.return_value.open.side_effect = TimeoutError("timeout")
            code, _, stderr = self.generate()
        self.assertEqual(code, 1)
        self.assertIn("生成结果未知", stderr)
        self.assertEqual(opener.return_value.open.call_count, 1)

    def test_business_error_and_malformed_response(self) -> None:
        for index, response in enumerate([{ "error": {"code": "Failed", "message": "拒绝"}},
                                          {"data": []}, {"data": [None]}, b"not json"]):
            with self.subTest(response=response):
                self.out = self.root / str(index)
                self.queue(response)
                self.assertEqual(self.generate()[0], 1)
                self.assertTrue((self.out / "response.json").exists())

    def test_output_validation_failures(self) -> None:
        cases = [image_item(b"not image"), {"b64_json": "!!"}, {"error": {"code": "Failed"}},
                 image_item(output_format="jpeg"), image_item(size="1x1"), {}]
        for index, item in enumerate(cases):
            with self.subTest(index=index):
                self.out = self.root / str(index)
                self.queue({"data": [item]})
                self.assertEqual(self.generate()[0], 1)
                self.assertFalse(transport.read_json(self.out / "manifest.json")["complete"])
                self.assertEqual(list(self.out.glob("image-*")), [])

    def test_url_download_no_authorization_and_redirect(self) -> None:
        self.queue({"data": [{"url": self.base + "/media"}]})
        self.queue(b"", status=302, Location=self.base + "/image")
        self.queue(picture())
        with patch.object(transport, "http_url", side_effect=self.local_media_url):
            code, _, _ = self.generate()
        self.assertEqual(code, 0)
        self.assertEqual([r["method"] for r in Handler.requests], ["POST", "GET", "GET"])
        for request in Handler.requests[1:]:
            self.assertNotIn("Authorization", request["headers"])

    def local_media_url(self, url: str, *, https_only: bool = False) -> str:
        if url.startswith(self.base + "/"):
            return url
        return payload.http_url(url, https_only=https_only)

    def test_media_requires_https_and_blocks_downgrade(self) -> None:
        with self.assertRaises(ValueError):
            transport.fetch_image("http://example.com/a.png", 1)
        with self.assertRaises(ValueError):
            transport.MediaRedirect().redirect_request(Request("https://example.com/a"), None, 302,
                                                         "Found", {}, "http://example.com/b")

    def test_partial_download_and_recovery_without_key(self) -> None:
        response = {"data": [image_item(z_index=0), {"url": self.base + "/retry", "z_index": 1,
                    "bounding_box": {"absolute": [0, 0, 100, 100]}}]}
        source = self.root / "response.json"
        transport.save_json(source, response)
        self.queue(b"bad image")
        with patch.object(transport, "http_url", side_effect=self.local_media_url):
            code, _, _ = self.cli("download", "--response", str(source), "--out", str(self.out))
            self.assertEqual(code, 1)
            manifest = transport.read_json(self.out / "manifest.json")
            self.assertFalse(manifest["complete"])
            self.assertEqual(len(manifest["files"]), 1)
            self.queue(picture())
            with patch.dict(os.environ, {}, clear=True):
                code, _, _ = self.cli("download", "--response", str(source), "--out", str(self.root / "recovered"))
        self.assertEqual(code, 0)
        self.assertTrue(all(request["method"] == "GET" for request in Handler.requests))

    def test_truncated_and_oversized_download(self) -> None:
        self.queue(picture(), **{"Content-Length": str(len(picture()) + 10)})
        with patch.object(transport, "http_url", side_effect=self.local_media_url), self.assertRaises(ValueError):
            transport.fetch_image(self.base + "/truncated", 1)
        self.queue(picture())
        with (patch.object(transport, "http_url", side_effect=self.local_media_url),
              patch.object(transport, "MAX_OUTPUT_BYTES", 10), self.assertRaises(ValueError)):
            transport.fetch_image(self.base + "/oversized", 1)

    def test_missing_alpha_detected(self) -> None:
        self.queue({"data": [image_item(picture(mode="RGB"))]})
        code, _, _ = self.cli("edit", "--image", data_uri(picture()), "--prompt", "调整颜色",
                              "--background", "transparent", "--out", str(self.out))
        self.assertEqual(code, 1)
        self.assertFalse((self.out / "image-00.png").exists())

    def test_malformed_layer_box_is_clean_error(self) -> None:
        self.queue({"data": [image_item(z_index=0), image_item(z_index=1, bounding_box="bad")]})
        code, _, stderr = self.cli("layers", "--image", "https://example.com/a.png", "--out", str(self.out))
        self.assertEqual(code, 1)
        self.assertIn("bounding_box", stderr)
        self.assertTrue((self.out / "response.json").exists())

    def test_non_utf8_response_is_preserved(self) -> None:
        self.queue(b"\xffinvalid")
        self.assertEqual(self.generate()[0], 1)
        self.assertTrue((self.out / "response.json").is_file())

    def test_download_invalid_layer_metadata_rejected(self) -> None:
        cases = [[image_item(z_index="one")],
                 [image_item(z_index=0), image_item(z_index=1)]]
        source = self.root / "saved.json"
        for index, data in enumerate(cases):
            with self.subTest(index=index):
                transport.save_json(source, {"data": data})
                code, _, _ = self.cli("download", "--response", str(source), "--out", str(self.root / str(index)))
                self.assertEqual(code, 1)

    def test_full_sixteen_layers_and_base(self) -> None:
        data = [image_item(z_index=0)] + [
            image_item(z_index=index, bounding_box={"absolute": [0, 0, 100, 100]})
            for index in range(1, 17)]
        self.queue({"data": data})
        code, stdout, _ = self.cli("layers", "--image", "https://example.com/a.png", "--out", str(self.out))
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(stdout)["files"]), 17)
        self.assertEqual(len(list(self.out.glob("image-*.png"))), 17)
        with self.assertRaises(ValueError):
            transport.response_items({"data": data + [data[-1]]}, layers=True)


if __name__ == "__main__":
    unittest.main()
