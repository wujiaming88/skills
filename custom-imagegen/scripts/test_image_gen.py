#!/usr/bin/env python3
"""custom-imagegen 的接口契约测试。"""

from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from typing import Any, ClassVar
import unittest

SCRIPT = Path(__file__).with_name("image_gen.py")
LIVE_SMOKE_SCRIPT = Path(__file__).with_name("live_smoke_test.py")
PNG_BYTES = b"\x89PNG\r\n\x1a\ncontract-test"


class FakeImageHandler(BaseHTTPRequestHandler):
    """记录请求并返回测试配置指定的响应。"""

    response_status: ClassVar[int] = 200
    response_body: ClassVar[dict[str, Any] | str] = {}
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        request: dict[str, Any] = {
            "method": "POST",
            "path": self.path,
            "headers": dict(self.headers),
            "body": raw_body,
        }
        if content_type.startswith("application/json"):
            request["json"] = json.loads(raw_body)
        self.__class__.requests.append(request)
        self.send_response(self.__class__.response_status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        body = self.__class__.response_body
        encoded = body if isinstance(body, str) else json.dumps(body)
        self.wfile.write(encoded.encode("utf-8"))

    def do_GET(self) -> None:
        self.__class__.requests.append(
            {"method": "GET", "path": self.path, "headers": dict(self.headers)}
        )
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(PNG_BYTES)

    def log_message(self, format: str, *args: object) -> None:
        return


class CustomImageCliTest(unittest.TestCase):
    """从真实 CLI 边界验证序列化、HTTP 和文件写入。"""

    server: ThreadingHTTPServer
    thread: threading.Thread
    base_url: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeImageHandler)
        port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{port}/openai/v1"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        FakeImageHandler.requests = []
        FakeImageHandler.response_status = 200
        FakeImageHandler.response_body = {
            "created": 0,
            "data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}],
        }

    def _run(
        self,
        *args: str,
        include_key: bool = True,
        model: str = "test-image-model",
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["CUSTOM_IMAGE_API_BASE_URL"] = self.base_url
        env["CUSTOM_IMAGE_MODEL"] = model
        if include_key:
            env["CUSTOM_IMAGE_API_KEY"] = "secret-contract-key"
        else:
            env.pop("CUSTOM_IMAGE_API_KEY", None)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_base64_response_writes_image_and_sends_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.png"
            result = self._run(
                "generate",
                "--prompt",
                "night market",
                "--no-augment",
                "--out",
                str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), PNG_BYTES)

        request = FakeImageHandler.requests[0]
        self.assertEqual(request["path"], "/openai/v1/images/generations")
        self.assertEqual(request["headers"]["Authorization"], "Bearer secret-contract-key")
        self.assertEqual(
            request["json"],
            {"model": "test-image-model", "prompt": "night market", "n": 1},
        )

    def test_url_response_does_not_forward_authorization(self) -> None:
        FakeImageHandler.response_body = {"data": [{"url": f"{self.base_url}/download.png"}]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "download.png"
            result = self._run("generate", "--prompt", "lake", "--out", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), PNG_BYTES)

        download = FakeImageHandler.requests[1]
        self.assertEqual(download["method"], "GET")
        self.assertNotIn("Authorization", download["headers"])

    def test_http_error_redacts_api_key(self) -> None:
        FakeImageHandler.response_status = 401
        FakeImageHandler.response_body = "invalid secret-contract-key"
        result = self._run("generate", "--prompt", "lake", "--out", "unused.png")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 401", result.stderr)
        self.assertIn("[REDACTED]", result.stderr)
        self.assertNotIn("secret-contract-key", result.stderr)
        self.assertEqual(len(FakeImageHandler.requests), 1)

    def test_dry_run_needs_no_key_and_prints_no_secret(self) -> None:
        result = self._run(
            "generate",
            "--prompt",
            "lake",
            "--dry-run",
            include_key=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["model"], "test-image-model")
        self.assertNotIn("api_key", preview)
        self.assertEqual(FakeImageHandler.requests, [])

    def test_existing_output_stops_before_billable_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.png"
            output.write_bytes(b"keep")
            result = self._run("generate", "--prompt", "lake", "--out", str(output))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_bytes(), b"keep")
            self.assertEqual(FakeImageHandler.requests, [])

    def test_edit_sends_images_mask_and_options_as_multipart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.png"
            second = root / "second.png"
            mask = root / "mask.png"
            output = root / "edited.png"
            first.write_bytes(PNG_BYTES + b"-first")
            second.write_bytes(PNG_BYTES + b"-second")
            mask.write_bytes(PNG_BYTES + b"-mask")
            result = self._run(
                "edit",
                "--image",
                str(first),
                "--image",
                str(second),
                "--mask",
                str(mask),
                "--prompt",
                "combine the objects",
                "--input-fidelity",
                "high",
                "--out",
                str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), PNG_BYTES)

        request = FakeImageHandler.requests[0]
        self.assertEqual(request["path"], "/openai/v1/images/edits")
        self.assertIn("multipart/form-data", request["headers"]["Content-Type"])
        body = request["body"]
        for expected in (
            b"first.png",
            b"second.png",
            b"mask.png",
            b"combine the objects",
            b"test-image-model",
            b"input_fidelity",
            b"high",
            PNG_BYTES + b"-first",
            PNG_BYTES + b"-second",
            PNG_BYTES + b"-mask",
        ):
            self.assertIn(expected, body)

    def test_edit_rejects_more_than_sixteen_images_before_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            arguments = ["edit", "--prompt", "combine", "--out", str(root / "out.png")]
            for index in range(17):
                image = root / f"input-{index}.png"
                image.write_bytes(PNG_BYTES)
                arguments.extend(["--image", str(image)])
            result = self._run(*arguments)

        self.assertEqual(result.returncode, 1)
        self.assertIn("at most 16", result.stderr)
        self.assertEqual(FakeImageHandler.requests, [])

    def test_gpt_image_2_accepts_valid_sizes(self) -> None:
        for size in ("auto", "1024x640", "3072x1024", "3840x2160"):
            with self.subTest(size=size):
                result = self._run(
                    "generate",
                    "--prompt",
                    "fixed size",
                    "--size",
                    size,
                    "--dry-run",
                    model="azure/gpt-image-2",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["size"], size)

    def test_gpt_image_2_omits_size_when_unspecified(self) -> None:
        result = self._run(
            "generate",
            "--prompt",
            "automatic size",
            "--dry-run",
            model="azure/gpt-image-2",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("size", json.loads(result.stdout))

    def test_gpt_image_2_rejects_invalid_sizes_before_request(self) -> None:
        invalid_sizes = ("1024", "1025x1024", "3856x1024", "3088x1024", "800x800", "3840x3840")
        for size in invalid_sizes:
            with self.subTest(size=size):
                result = self._run(
                    "generate",
                    "--prompt",
                    "invalid size",
                    "--size",
                    size,
                    "--dry-run",
                    model="azure/gpt-image-2",
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("size", result.stderr.lower())
                self.assertEqual(FakeImageHandler.requests, [])

    def test_custom_model_keeps_provider_specific_size_pass_through(self) -> None:
        result = self._run(
            "generate",
            "--prompt",
            "provider size",
            "--size",
            "square",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["size"], "square")

    def test_extra_json_cannot_override_declared_request_options(self) -> None:
        result = self._run(
            "generate",
            "--prompt",
            "invalid override",
            "--extra-json",
            '{"size":"800x800"}',
            "--dry-run",
            model="azure/gpt-image-2",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("reserved fields: size", result.stderr)
        self.assertEqual(FakeImageHandler.requests, [])

    def test_gpt_image_2_rejects_unsupported_input_fidelity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "input.png"
            image.write_bytes(PNG_BYTES)
            result = self._run(
                "edit",
                "--image",
                str(image),
                "--prompt",
                "preserve details",
                "--input-fidelity",
                "high",
                "--dry-run",
                model="azure/gpt-image-2",
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("input_fidelity", result.stderr)
        self.assertEqual(FakeImageHandler.requests, [])

    def test_gpt_image_2_rejects_transparent_background(self) -> None:
        result = self._run(
            "generate",
            "--prompt",
            "transparent cutout",
            "--background",
            "transparent",
            "--dry-run",
            model="azure/gpt-image-2-2026-04-21",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("transparent", result.stderr)
        self.assertEqual(FakeImageHandler.requests, [])

    def test_live_smoke_requires_explicit_billable_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(LIVE_SMOKE_SCRIPT), "--out-dir", directory],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--confirm-billable", result.stderr)
        self.assertEqual(FakeImageHandler.requests, [])

    def test_generate_batch_runs_distinct_jobs_sequentially(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jobs = root / "jobs.jsonl"
            jobs.write_text(
                '{"prompt":"first prompt","out":"first.png"}\n'
                '{"prompt":"second prompt","out":"second.png"}\n',
                encoding="utf-8",
            )
            output_dir = root / "output"
            result = self._run(
                "generate-batch",
                "--input",
                str(jobs),
                "--out-dir",
                str(output_dir),
                "--no-augment",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((output_dir / "first.png").read_bytes(), PNG_BYTES)
            self.assertEqual((output_dir / "second.png").read_bytes(), PNG_BYTES)

        prompts = [request["json"]["prompt"] for request in FakeImageHandler.requests]
        self.assertEqual(prompts, ["first prompt", "second prompt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
