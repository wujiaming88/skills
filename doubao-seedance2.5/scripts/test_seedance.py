"""真实本地 HTTP 契约测试；不访问方舟、不产生付费生成请求。"""

from __future__ import annotations

import io
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import unittest
from collections import deque
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import seedance
import seedance_payload as payload

SCRIPT = Path(seedance.__file__)
VIDEO = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42" + b"test-content"
PNG = b"\x89PNG\r\n\x1a\n" + b"test-content"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"test-content"


class Handler(BaseHTTPRequestHandler):
    responses: ClassVar[deque[tuple[int, Any, dict[str, str]]]] = deque()
    requests: ClassVar[list[dict[str, Any]]] = []

    def handle_request(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.requests.append({"method": self.command, "path": self.path,
                              "headers": dict(self.headers), "body": json.loads(raw) if raw else None})
        status, body, headers = self.responses.popleft() if self.responses else (500, {"unexpected": True}, {})
        encoded = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        if "Content-Length" not in headers:
            self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:
        self.handle_request()

    def do_GET(self) -> None:
        self.handle_request()

    def do_DELETE(self) -> None:
        self.handle_request()

    def log_message(self, format: str, *args: object) -> None:
        """测试服务静默，防止打印请求头中的临时测试凭据。"""


class MediaResponse(io.BytesIO):
    def __init__(self, body: bytes, length: int | None = None) -> None:
        super().__init__(body)
        self.headers = {"Content-Length": str(len(body) if length is None else length)}


class SeedanceTest(unittest.TestCase):
    server: ClassVar[ThreadingHTTPServer]
    thread: ClassVar[threading.Thread]
    base_url: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}/api/v3/contents/generations/tasks"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        Handler.responses = deque()
        Handler.requests = []
        self.key = secrets.token_hex(24)
        self.env_patch = patch.dict(os.environ, {seedance.KEY_ENV: self.key})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.url_patch = patch.object(seedance, "API_URL", self.base_url)
        self.url_patch.start()
        self.addCleanup(self.url_patch.stop)

    def queue(self, body: Any, status: int = 200, **headers: str) -> None:
        Handler.responses.append((status, body, headers))

    def cli(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = seedance.main(list(args))
        self.assertNotIn(self.key, stdout.getvalue() + stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue()

    def text_body(self, **options: Any) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "花朵绽放"}], **options}

    def reference(self, kind: str = "image", role: str | None = None) -> dict[str, Any]:
        return {"type": f"{kind}_url", f"{kind}_url": {"url": f"https://media.example.com/{kind}"},
                "role": role or f"reference_{kind}"}

    def test_cli_subprocess_dry_run_without_key(self) -> None:
        env = {key: value for key, value in os.environ.items() if key != seedance.KEY_ENV}
        result = subprocess.run([sys.executable, str(SCRIPT), "create", "--prompt", "花朵", "--dry-run"],
                                capture_output=True, text=True, env=env, check=False, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        result_body = json.loads(result.stdout)
        self.assertEqual(result_body["body"]["model"], payload.MODEL)
        self.assertTrue(result_body["url"].startswith("https://ark.cn-beijing.volces.com/"))

    def test_create_auth_body_and_immediate_id(self) -> None:
        self.queue({"id": "task-1"})
        code, stdout, stderr = self.cli("create", "--prompt", "花朵", "--duration", "5", "--no-generate-audio")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), {"id": "task-1"})
        request = Handler.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["headers"]["Authorization"], f"Bearer {self.key}")
        self.assertEqual(request["body"], {"model": payload.MODEL, "duration": 5,
                                         "generate_audio": False, "content": [{"type": "text", "text": "花朵"}]})
        self.assertIn('"status": "submitted"', stderr)

    def test_request_json_preserves_all_supported_fields_and_order(self) -> None:
        body = self.text_body(omni_reference_task_type="reference", resolution="1080p", ratio="9:16",
                              duration=30, generate_audio=True, watermark=True, output_format="mov",
                              return_last_frame=True, callback_url="https://callback.example.com/hook",
                              execution_expires_after=3600, priority=9, safety_identifier="user-hash",
                              service_tier="default")
        body["content"] += [self.reference("audio"), self.reference("video"), self.reference()]
        self.queue({"id": "task-all"})
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "request.json"
            file.write_text(json.dumps(body), encoding="utf-8")
            code, _, stderr = self.cli("create", "--request", str(file))
        self.assertEqual(code, 0, stderr)
        self.assertEqual(Handler.requests[0]["body"], {"model": payload.MODEL, **body})

    def test_web_search_is_limited_to_text_input(self) -> None:
        self.queue({"id": "text-search"})
        code, _, stderr = self.cli("create", "--prompt", "玻璃蛙的微距镜头", "--web-search")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(Handler.requests[0]["body"]["tools"], [{"type": "web_search"}])
        with self.assertRaisesRegex(ValueError, "联网搜索.*纯文本"):
            payload.validate_payload({"content": [self.reference()], "tools": [{"type": "web_search"}]})

    def test_model_override_and_unsupported_parameters_rejected(self) -> None:
        invalid = [{"model": "other"}, {"resolution": "4k"}, {"service_tier": "flex"},
                   {"fps": 30}, {"negative_prompt": "blur"}, {"language": "zh"}]
        invalid += [{key: 1} for key in payload.UNSUPPORTED]
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(ValueError):
                payload.validate_payload(self.text_body(**options))

    def test_scalar_boundaries_and_types(self) -> None:
        for options in ({"duration": 4}, {"duration": 30}, {"duration": -1}, {"priority": 0},
                        {"priority": 9}, {"execution_expires_after": 259200}):
            self.assertEqual(payload.validate_payload(self.text_body(**options))["model"], payload.MODEL)
        for options in ({"duration": 3}, {"duration": 31}, {"duration": True}, {"duration": 4.5},
                        {"priority": 10}, {"execution_expires_after": 3599}, {"generate_audio": "true"},
                        {"ratio": []}, {"safety_identifier": "x" * 65}, {"tools": [{"type": "other"}]}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                payload.validate_payload(self.text_body(**options))

    def test_fifty_references_and_audio_only(self) -> None:
        items = [self.reference()] * 30 + [self.reference("video")] * 10 + [self.reference("audio")] * 10
        self.assertEqual(len(payload.validate_payload({"content": items})["content"]), 50)
        self.assertEqual(len(payload.validate_payload({"content": [self.reference("audio")]})["content"]), 1)
        for kind, count in (("image", 31), ("video", 11), ("audio", 11)):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                payload.validate_payload({"content": [self.reference(kind)] * count})

    def test_frame_modes_constraints(self) -> None:
        first, last = self.reference(role="first_frame"), self.reference(role="last_frame")
        body = payload.validate_payload({"content": [first, last]})
        self.assertEqual(body["ratio"], "adaptive")
        for content in ([last], [first, first], [first, self.reference()], [first, self.reference("audio")]):
            with self.subTest(content=content), self.assertRaises(ValueError):
                payload.validate_payload({"content": content})
        with self.assertRaises(ValueError):
            payload.validate_payload({"content": [first], "ratio": "16:9"})

    def test_edit_extend_constraints_and_defaults(self) -> None:
        for mode in ("edit", "extend"):
            body = payload.validate_payload({"content": [self.reference("video")], "omni_reference_task_type": mode})
            self.assertEqual(body["ratio"], "adaptive")
            if mode == "edit":
                self.assertEqual(body["duration"], -1)
            with self.assertRaises(ValueError):
                payload.validate_payload({"content": [self.reference()], "omni_reference_task_type": mode})
        with self.assertRaises(ValueError):
            payload.validate_payload({"content": [self.reference("video")], "omni_reference_task_type": "edit", "duration": 5})

    def test_local_image_audio_and_asset_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image, audio = Path(directory) / "image.png", Path(directory) / "sound.wav"
            image.write_bytes(PNG)
            audio.write_bytes(b"RIFF-test-audio")
            code, stdout, stderr = self.cli("create", "--reference-image", str(image), "--reference-audio", str(audio), "--dry-run")
            self.assertEqual(code, 0, stderr)
            self.assertIn("data:image/png;base64,<omitted>", stdout)
            self.assertIn("data:audio/wav;base64,<omitted>", stdout)
            self.assertEqual(payload.media_source("asset://approved", "video"), "asset://approved")
        self.assertEqual(Handler.requests, [])

    def test_invalid_content_sources(self) -> None:
        invalid = [{"content": []}, {"content": [{"type": "text", "text": " "}]},
                   {"content": [{"type": "draft_task", "draft_task": {"id": "task-1"}}]},
                   {"content": [{"type": [], "text": "x"}]}]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ValueError):
                payload.validate_payload(body)
        for source, kind in (("data:video/mp4;base64,AAAA", "video"), ("file:///etc/hosts", "image"),
                             ("data:image/png;base64,!?", "image"), ("https://u:p@example.com/a", "image")):
            with self.subTest(source=source), self.assertRaises(ValueError):
                payload.validate_source(source, kind)
        with self.assertRaises(ValueError):
            payload.media_source("local.mp4", "video")

    def test_size_limits(self) -> None:
        payload.check_media_size("audio", 15 * 1024 * 1024)
        for kind, size in (("audio", 15 * 1024 * 1024 + 1), ("image", 30 * 1024 * 1024), ("image", 0)):
            with self.assertRaises(ValueError):
                payload.check_media_size(kind, size)
        with patch.object(payload, "MAX_BODY_BYTES", 16), self.assertRaises(ValueError):
            payload.validate_payload(self.text_body())

    def test_conflicting_json_and_flags_do_not_submit(self) -> None:
        code, _, stderr = self.cli("create", "--request", "unused.json", "--duration", "5")
        self.assertEqual(code, 1)
        self.assertIn("不可与生成参数混用", stderr)
        self.assertEqual(Handler.requests, [])

    def test_missing_key_has_no_fallback(self) -> None:
        with patch.dict(os.environ, {"ARK_API_KEY": self.key, "SEEDANCE-API-KEY": self.key}, clear=True):
            code, _, stderr = self.cli("get", "task-1")
        self.assertEqual(code, 1)
        self.assertIn("SEEDANCE_API_KEY", stderr)
        self.assertEqual(Handler.requests, [])

    def test_new_environment_name_authenticates_without_legacy_fallback(self) -> None:
        self.queue({"id": "task-1", "status": "succeeded"})
        # 两个变量同时存在时，只能采用用户指定的新变量。
        env = {"SEEDANCE_API_KEY": self.key, "SEEDANCE-API-KEY": secrets.token_hex(24)}
        with patch.dict(os.environ, env, clear=True):
            code, stdout, stderr = self.cli("get", "task-1")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["status"], "succeeded")
        self.assertEqual(Handler.requests[0]["headers"]["Authorization"], f"Bearer {self.key}")

    def test_http_error_redacts_secret_and_does_not_retry(self) -> None:
        self.queue({"error": {"message": self.key}}, 429)
        code, _, stderr = self.cli("create", "--prompt", "花朵")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 429", stderr)
        self.assertIn("[REDACTED]", stderr)
        self.assertEqual(len(Handler.requests), 1)

    def test_auth_redirect_blocked(self) -> None:
        self.queue({}, 302, Location=self.base_url + "/leak")
        code, _, stderr = self.cli("get", "task-1")
        self.assertEqual(code, 1)
        self.assertIn("阻止", stderr)
        self.assertEqual(len(Handler.requests), 1)

    def test_malformed_response_and_missing_id(self) -> None:
        for response in (b"not-json", [], {}, {"error": {"message": "invalid"}}):
            self.queue(response)
            code, _, _ = self.cli("create", "--prompt", "花朵")
            self.assertEqual(code, 1)
        self.assertEqual(len(Handler.requests), 4)

    def test_truncated_http_response_is_reported_without_retry(self) -> None:
        self.queue(b'{"id":', **{"Content-Length": "99"})
        code, _, stderr = self.cli("create", "--prompt", "花朵")
        self.assertEqual(code, 1)
        self.assertIn("创建结果未知", stderr)
        self.assertEqual(len(Handler.requests), 1)

    def test_list_all_filters_repeats_ids_and_keeps_response(self) -> None:
        expected = {"items": [{"id": "a", "usage": {"total_tokens": 123}}], "total": 1}
        self.queue(expected)
        code, stdout, stderr = self.cli("list", "--page-num", "2", "--page-size", "500", "--status", "succeeded",
                                        "--endpoint-id", "ep-example", "--service-tier", "default", "--task-id", "a", "--task-id", "b")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), expected)
        query = parse_qs(urlsplit(Handler.requests[0]["path"]).query)
        self.assertEqual(query, {"page_num": ["2"], "page_size": ["500"], "filter.status": ["succeeded"],
                                 "filter.model": ["ep-example"], "filter.service_tier": ["default"], "filter.task_ids": ["a", "b"]})

    def test_invalid_pagination_and_wait_arguments(self) -> None:
        for args in (("list", "--page-num", "0"), ("list", "--page-size", "501"),
                     ("wait", "id", "--poll-interval", "nan"), ("wait", "id", "--wait-timeout", "0")):
            self.assertEqual(self.cli(*args)[0], 1)
        self.assertEqual(Handler.requests, [])

    def test_get_preserves_metadata_and_escapes_id(self) -> None:
        expected = {"id": "a/b", "status": "failed", "error": {"code": "InvalidParameter.TaskTypeMismatch"},
                    "usage": {"tool_usage": {"web_search": 1}}, "new_metadata": 7}
        self.queue(expected)
        code, stdout, _ = self.cli("get", "a/b")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), expected)
        self.assertTrue(Handler.requests[0]["path"].endswith("/a%2Fb"))

    def test_wait_transitions_preserve_usage(self) -> None:
        self.queue({"id": "t", "status": "queued"})
        self.queue({"id": "t", "status": "running"})
        self.queue({"id": "t", "status": "succeeded", "usage": {"total_tokens": 321}})
        with patch.object(seedance.time, "sleep"):
            code, stdout, stderr = self.cli("wait", "t")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["usage"]["total_tokens"], 321)
        self.assertEqual([r["method"] for r in Handler.requests], ["GET"] * 3)

    def test_wait_terminal_failures_exit_nonzero(self) -> None:
        for state in ("failed", "expired", "cancelled"):
            self.queue({"id": "t", "status": state, "error": {"message": "detail"}})
            code, stdout, _ = self.cli("wait", "t")
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(stdout)["status"], state)

    def test_wait_timeout_retains_receipt_and_never_recreates(self) -> None:
        self.queue({"id": "recoverable"})
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "task.json"
            with patch.object(seedance.time, "monotonic", side_effect=[0, 1000]):
                code, _, stderr = self.cli("create", "--prompt", "花朵", "--wait", "--receipt", str(receipt))
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(receipt.read_text()), {"id": "recoverable"})
            self.assertIn("recoverable", stderr)
        self.assertEqual([r["method"] for r in Handler.requests], ["POST"])

    def test_unknown_state_is_error(self) -> None:
        self.queue({"id": "t", "status": "mystery"})
        code, _, stderr = self.cli("wait", "t")
        self.assertEqual(code, 1)
        self.assertIn("未知状态", stderr)

    def test_delete_empty_and_result_response(self) -> None:
        for body in (b"", {"Result": {}}):
            self.queue(body)
            code, stdout, _ = self.cli("delete", "t")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout)["delete_response"], {} if not body else body)
        self.assertEqual([r["method"] for r in Handler.requests], ["DELETE", "DELETE"])

    def test_existing_output_stops_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "keep.mp4"
            output.write_bytes(b"keep")
            code, _, _ = self.cli("create", "--prompt", "花朵", "--out", str(output))
            self.assertEqual(code, 1)
            self.assertEqual(output.read_bytes(), b"keep")
        self.assertEqual(Handler.requests, [])

    def test_output_collision_and_missing_last_frame_option(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "file.mp4")
            self.assertEqual(self.cli("create", "--prompt", "花朵", "--out", output, "--receipt", output)[0], 1)
            self.assertEqual(self.cli("create", "--prompt", "花朵", "--last-frame-out", output)[0], 1)
        self.assertEqual(Handler.requests, [])

    def test_download_signature_length_and_no_auth(self) -> None:
        for content, is_image in ((VIDEO, False), (PNG, True)):
            with tempfile.TemporaryDirectory() as directory, patch.object(seedance, "build_opener") as make_opener:
                make_opener.return_value.open.return_value = MediaResponse(content)
                output = Path(directory) / "output"
                seedance.download_file("https://media.example.com/out", output, 1, False, image=is_image)
                self.assertEqual(output.read_bytes(), content)
                request = make_opener.return_value.open.call_args.args[0]
                self.assertNotIn("Authorization", request.headers)

    def test_download_failure_never_publishes_partial_file(self) -> None:
        for content, length in ((b"<html>error</html>", None), (VIDEO, 999)):
            with tempfile.TemporaryDirectory() as directory, patch.object(seedance, "build_opener") as make_opener:
                output = Path(directory) / "out.mp4"
                make_opener.return_value.open.return_value = MediaResponse(content, length)
                with self.assertRaises(ValueError):
                    seedance.download_file("https://media.example.com/out", output, 1, False)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_live_jpeg_last_frame_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(seedance, "build_opener") as make_opener:
            make_opener.return_value.open.return_value = MediaResponse(JPEG)
            output = Path(directory) / "last.jpg"
            seedance.download_file("https://media.example.com/last-frame.png", output, 1, False, image=True)
            self.assertEqual(output.read_bytes(), JPEG)

    def test_last_frame_extension_mismatch_is_explained(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(seedance, "build_opener") as make_opener:
            make_opener.return_value.open.return_value = MediaResponse(JPEG)
            output = Path(directory) / "last.png"
            with self.assertRaisesRegex(ValueError, "JPEG.*jpg"):
                seedance.download_file("https://media.example.com/last-frame.png", output, 1, False, image=True)
            self.assertFalse(output.exists())

    def test_download_url_and_redirect_require_https(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            seedance.download_file("file:///etc/hosts", Path(directory) / "out", 1, False)
        with self.assertRaises(ValueError):
            seedance.MediaRedirect().redirect_request(Request("https://example.com"), None, 302, "", {}, "http://example.com")

    def test_create_wait_download_and_receipt_end_to_end(self) -> None:
        self.queue({"id": "t"})
        task = {"id": "t", "status": "succeeded", "content": {"video_url": "https://media.example.com/out.mp4"}}
        self.queue(task)
        original = seedance.build_opener
        with tempfile.TemporaryDirectory() as directory:
            output, receipt = Path(directory) / "out.mp4", Path(directory) / "task.json"
            with patch.object(seedance, "build_opener") as make_opener:
                media_opener = unittest.mock.Mock()
                media_opener.open.return_value = MediaResponse(VIDEO)
                make_opener.side_effect = lambda handler: media_opener if isinstance(handler, seedance.MediaRedirect) else original(handler)
                code, stdout, stderr = self.cli("create", "--prompt", "花朵", "--out", str(output), "--receipt", str(receipt))
            self.assertEqual(code, 0, stderr)
            self.assertEqual(output.read_bytes(), VIDEO)
            self.assertEqual(json.loads(receipt.read_text()), json.loads(stdout))
        self.assertEqual([r["method"] for r in Handler.requests], ["POST", "GET"])


if __name__ == "__main__":
    unittest.main()
