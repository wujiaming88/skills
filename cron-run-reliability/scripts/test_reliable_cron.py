#!/usr/bin/env python3
"""Regression, stability, and fault-handling tests for reliable_cron.py."""

from __future__ import annotations

import concurrent.futures
import importlib.util
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).with_name("reliable_cron.py")
WAIT_READY_LAUNCHER = """
import os
import pathlib
import sys

script = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(script.parent))
import reliable_cron

original_sleep = reliable_cron.time.sleep
ready_path = pathlib.Path(os.environ["RELIABLE_CRON_WAIT_READY"])

def ready_sleep(seconds):
    ready_path.touch()
    original_sleep(seconds)

reliable_cron.time.sleep = ready_sleep
sys.argv = sys.argv[1:]
raise SystemExit(reliable_cron.main())
"""
SPEC = importlib.util.spec_from_file_location("reliable_cron_under_test", SCRIPT)
assert SPEC and SPEC.loader
RELIABLE_CRON = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RELIABLE_CRON
SPEC.loader.exec_module(RELIABLE_CRON)


class TestHandler(BaseHTTPRequestHandler):
    retry_count = 0

    def do_GET(self) -> None:  # noqa: N802
        try:
            if self.path == "/ok":
                self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
            elif self.path == "/redirect":
                self.send_response(302); self.send_header("Location", "/ok"); self.end_headers()
            elif self.path == "/retry":
                type(self).retry_count += 1
                self.send_response(503 if type(self).retry_count < 3 else 200); self.end_headers()
            elif self.path == "/slow":
                time.sleep(0.3); self.send_response(200); self.end_headers()
            else:
                self.send_response(404); self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, _format: str, *args: object) -> None:
        return


class ReliableCronTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def run_helper(self, *args: str, timeout: float = 10, env: dict[str, str] | None = None):
        completed = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                   check=False, timeout=timeout, env=env)
        lines = completed.stdout.splitlines()
        self.assertEqual(len(lines), 1, completed.stdout)
        return completed, json.loads(lines[0])

    def git(self, repo: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def wait_for_file(self, path: Path, timeout: float = 2) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            time.sleep(0.01)
        self.fail(f"timed out waiting for {path}")

    def wait_for_process_ready(self, process: subprocess.Popen[str], path: Path, timeout: float = 2) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(f"helper exited before readiness: rc={process.returncode}, stdout={stdout!r}, stderr={stderr!r}")
            time.sleep(0.01)
        process.kill()
        stdout, stderr = process.communicate(timeout=2)
        self.fail(f"timed out waiting for helper readiness: stdout={stdout!r}, stderr={stderr!r}")

    def assert_process_stopped(self, process_id: int, timeout: float = 2) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                state = Path(f"/proc/{process_id}/stat").read_text(encoding="utf-8").split()[2]
            except (FileNotFoundError, ProcessLookupError):
                return
            if state == "Z":
                return
            time.sleep(0.02)
        self.fail(f"process {process_id} is still running")

    def init_git_pair(self, directory: Path) -> tuple[Path, Path]:
        remote, repo = directory / "remote.git", directory / "repo"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
        self.git(repo, "config", "user.email", "test@example.com"); self.git(repo, "config", "user.name", "Test")
        self.git(repo, "remote", "add", "origin", str(remote))
        (repo / "file.txt").write_text("one", encoding="utf-8")
        self.git(repo, "add", "file.txt"); self.git(repo, "commit", "-m", "initial"); self.git(repo, "push", "-u", "origin", "main")
        return repo, remote

    def test_wait_existing_and_delayed_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "delayed done"
            timer = threading.Timer(0.12, target.write_text, args=("ok",), kwargs={"encoding": "utf-8"}); timer.start()
            try:
                completed, payload = self.run_helper("wait", "--file", str(target), "--timeout", "1", "--interval", "0.03")
            finally:
                timer.join(timeout=1)
            self.assertEqual((completed.returncode, payload["status"]), (0, "DONE")); self.assertGreaterEqual(payload["checks"], 2)

    def test_wait_timeout_is_nonfatal_and_bounded(self) -> None:
        started = time.monotonic()
        completed, payload = self.run_helper("wait", "--file", "/definitely/missing", "--timeout", "0.12", "--interval", "0.03")
        self.assertEqual((completed.returncode, payload["status"]), (0, "WAIT_TIMEOUT")); self.assertLess(time.monotonic() - started, 1)

    def test_wait_interrupts_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for interrupt_signal in (signal.SIGINT, signal.SIGTERM):
                ready_path = Path(directory) / f"ready-{interrupt_signal.value}"
                env = dict(os.environ); env["RELIABLE_CRON_WAIT_READY"] = str(ready_path)
                process = subprocess.Popen(
                    [sys.executable, "-c", WAIT_READY_LAUNCHER, str(SCRIPT), "wait", "--file", "/missing",
                     "--timeout", "10", "--interval", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                )
                self.wait_for_process_ready(process, ready_path)
                process.send_signal(interrupt_signal)
                stdout, _ = process.communicate(timeout=2)
                self.assertEqual(process.returncode, 130)
                self.assertEqual(json.loads(stdout)["status"], "INTERRUPTED")

    def test_invalid_numeric_and_path_arguments_fail_fast_as_json(self) -> None:
        cases = [
            ("wait", "--file", "/missing", "--timeout=nan"),
            ("wait", "--file", "/missing", "--timeout=inf"),
            ("wait", "--file", "/missing", "--timeout=-inf"),
            ("wait", "--file", "/missing", "--timeout=86401"),
            ("wait", "--file", "/missing", "--interval=0"),
            ("check-files", "--file", "relative"),
            ("check-files", "--file", "/missing", "--min-bytes", "0"),
            ("check-http", "--url", self.base_url, "--attempts", "21"),
            ("check-http", "--url", self.base_url, "--request-timeout=nan"),
        ]
        for case in cases:
            completed, payload = self.run_helper(*case, timeout=2)
            self.assertEqual(completed.returncode, 2); self.assertEqual(payload["status"], "ARGUMENT_ERROR")

    def test_file_types_unicode_threshold_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); empty = root / "empty"; empty.touch(); folder = root / "folder"; folder.mkdir()
            good = root / "报告 文件.md"; good.write_text("abcd", encoding="utf-8"); link = root / "link"; link.symlink_to(good)
            for path in (empty, folder, link):
                completed, payload = self.run_helper("check-files", "--file", str(path))
                self.assertEqual(completed.returncode, 2); self.assertEqual(payload["status"], "FILES_INVALID")
            self.assertEqual(self.run_helper("check-files", "--file", str(good), "--min-bytes", "4")[0].returncode, 0)
            self.assertEqual(self.run_helper("check-files", "--file", str(good), "--min-bytes", "5")[0].returncode, 2)

    def test_glob_requires_matches_and_rejects_any_invalid_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); pattern = str(root / "part-*.md")
            self.assertEqual(self.run_helper("check-files", "--glob", pattern)[0].returncode, 2)
            (root / "part-1.md").write_text("ok", encoding="utf-8"); self.assertEqual(self.run_helper("check-files", "--glob", pattern)[0].returncode, 0)
            (root / "part-2.md").touch(); self.assertEqual(self.run_helper("check-files", "--glob", pattern)[0].returncode, 2)

    def test_concurrent_checks_and_real_file_replacement_race_do_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / "done"; outside = root / "outside"
            target.write_text("ok", encoding="utf-8"); outside.write_text("outside-secret", encoding="utf-8")
            def one(_index: int) -> bool:
                completed, payload = self.run_helper("check-files", "--file", str(target))
                return payload["status"] in {"FILES_OK", "FILES_INVALID"} and "point-in-time" in payload["evidenceScope"]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                self.assertTrue(all(pool.map(one, range(40))))
            stop = threading.Event()
            def churn() -> None:
                while not stop.is_set():
                    target.unlink(missing_ok=True)
                    try:
                        target.symlink_to(outside)
                    except FileExistsError:
                        pass
                    target.unlink(missing_ok=True)
                    try:
                        target.write_text("ok", encoding="utf-8")
                    except FileNotFoundError:
                        pass
            thread = threading.Thread(target=churn)
            thread.start()
            try:
                outcomes = [self.run_helper("check-files", "--file", str(target)) for _ in range(30)]
            finally:
                stop.set(); thread.join(timeout=2)
            self.assertTrue(all(item[0].returncode in (0, 2) for item in outcomes))
            self.assertTrue(all("point-in-time" in item[1]["evidenceScope"] for item in outcomes))

    def test_git_live_remote_clean_dirty_and_diverged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = self.init_git_pair(Path(directory))
            completed, payload = self.run_helper("check-git", "--repo", str(repo), "--verify-remote")
            self.assertEqual((completed.returncode, payload["status"]), (0, "GIT_OK"))
            (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
            self.assertEqual(self.run_helper("check-git", "--repo", str(repo), "--verify-remote")[0].returncode, 2)
            (repo / "dirty.txt").unlink(); (repo / "file.txt").write_text("two", encoding="utf-8")
            self.git(repo, "add", "file.txt"); self.git(repo, "commit", "-m", "local only")
            self.assertEqual(self.run_helper("check-git", "--repo", str(repo), "--verify-remote")[0].returncode, 2)

    def test_git_live_remote_detects_stale_tracking_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo, remote = self.init_git_pair(root); peer = root / "peer"
            subprocess.run(["git", "clone", "-b", "main", str(remote), str(peer)], check=True, capture_output=True)
            self.git(peer, "config", "user.email", "peer@example.com"); self.git(peer, "config", "user.name", "Peer")
            (peer / "peer.txt").write_text("new", encoding="utf-8"); self.git(peer, "add", "peer.txt"); self.git(peer, "commit", "-m", "remote ahead"); self.git(peer, "push")
            self.assertEqual(self.git(repo, "rev-parse", "HEAD"), self.git(repo, "rev-parse", "origin/main"))
            completed, payload = self.run_helper("check-git", "--repo", str(repo), "--verify-remote")
            self.assertEqual(completed.returncode, 2); self.assertFalse(payload["synced"])

    def test_git_nonrepo_missing_remote_redaction_timeout_and_descendant_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed, payload = self.run_helper("check-git", "--repo", str(root)); self.assertEqual((completed.returncode, payload["status"]), (2, "GIT_ERROR"))
            repo, _ = self.init_git_pair(root)
            self.assertEqual(self.run_helper("check-git", "--repo", str(repo), "--verify-remote", "--remote", "absent")[0].returncode, 2)
            fake_bin = root / "bin"; fake_bin.mkdir(); fake_git = fake_bin / "git"; child_file = root / "child.pid"
            fake_git.write_text(
                "#!/bin/sh\n"
                "echo 'https://user:top-secret@example.invalid/repo.git' >&2\n"
                "sleep 30 &\n"
                "echo $! > \"$CHILD_PID_FILE\"\n"
                "wait\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            env = dict(os.environ); env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"; env["CHILD_PID_FILE"] = str(child_file)
            started = time.monotonic()
            completed, payload = self.run_helper("check-git", "--repo", str(repo), "--command-timeout", "0.05", env=env)
            self.assertEqual((completed.returncode, payload["status"]), (2, "GIT_ERROR"))
            self.assertLess(time.monotonic() - started, 1)
            self.assertNotIn("top-secret", json.dumps(payload))
            self.wait_for_file(child_file)
            self.assert_process_stopped(int(child_file.read_text(encoding="utf-8")))

    def test_git_sigterm_cleans_descendants_and_reports_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo, _ = self.init_git_pair(root); fake_bin = root / "bin"; fake_bin.mkdir()
            child_file = root / "child.pid"; fake_git = fake_bin / "git"
            fake_git.write_text("#!/bin/sh\nsleep 30 &\necho $! > \"$CHILD_PID_FILE\"\nwait\n", encoding="utf-8")
            fake_git.chmod(0o755)
            env = dict(os.environ); env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"; env["CHILD_PID_FILE"] = str(child_file)
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), "check-git", "--repo", str(repo), "--command-timeout", "30"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            self.wait_for_file(child_file)
            process.send_signal(signal.SIGTERM)
            stdout, _ = process.communicate(timeout=2)
            self.assertEqual(process.returncode, 130)
            self.assertEqual(json.loads(stdout)["status"], "INTERRUPTED")
            self.assert_process_stopped(int(child_file.read_text(encoding="utf-8")))

    def test_git_requires_expected_checked_out_branch_and_rejects_detached_head(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = self.init_git_pair(Path(directory))
            self.git(repo, "switch", "-c", "feature")
            completed, payload = self.run_helper("check-git", "--repo", str(repo))
            self.assertEqual(completed.returncode, 2); self.assertFalse(payload["branchMatches"])
            completed, payload = self.run_helper("check-git", "--repo", str(repo), "--branch", "feature")
            self.assertEqual(completed.returncode, 0); self.assertTrue(payload["branchMatches"])
            self.git(repo, "checkout", "--detach")
            completed, payload = self.run_helper("check-git", "--repo", str(repo), "--branch", "feature")
            self.assertEqual(completed.returncode, 2); self.assertIsNone(payload["checkedOutBranch"])

    def test_git_detects_concurrent_commit_during_live_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo, _ = self.init_git_pair(root); fake_bin = root / "bin"; fake_bin.mkdir()
            marker = root / "ls-remote.started"; real_git = shutil.which("git"); self.assertIsNotNone(real_git)
            wrapper = fake_bin / "git"
            wrapper.write_text(
                "#!/bin/sh\n"
                "for arg in \"$@\"; do\n"
                "  if [ \"$arg\" = ls-remote ]; then touch \"$RACE_MARKER\"; sleep 0.4; fi\n"
                "done\n"
                f"exec {real_git} \"$@\"\n",
                encoding="utf-8",
            )
            wrapper.chmod(0o755)
            env = dict(os.environ); env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"; env["RACE_MARKER"] = str(marker)
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), "check-git", "--repo", str(repo), "--verify-remote"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            self.wait_for_file(marker)
            (repo / "file.txt").write_text("changed during validation", encoding="utf-8")
            self.git(repo, "add", "file.txt"); self.git(repo, "commit", "-m", "racing commit")
            stdout, _ = process.communicate(timeout=5); payload = json.loads(stdout)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(payload["status"], "GIT_INVALID")
            self.assertTrue(payload["concurrentChangeDetected"])

    def test_http_requires_only_public_resolved_destinations(self) -> None:
        public = (socket_family := 2, 1, 6, "", ("93.184.216.34", 443))
        private = (socket_family, 1, 6, "", ("10.0.0.2", 443))
        with mock.patch.object(RELIABLE_CRON.socket, "getaddrinfo", return_value=[public]):
            RELIABLE_CRON.validate_public_http_url("https://public.example/path")
        with mock.patch.object(RELIABLE_CRON.socket, "getaddrinfo", return_value=[public, private]):
            with self.assertRaises(RELIABLE_CRON.PublicUrlError):
                RELIABLE_CRON.validate_public_http_url("https://mixed.example/path")
        for url in ("http://127.0.0.1/", "http://[::1]/", "http://169.254.169.254/latest/meta-data/"):
            with self.assertRaises(RELIABLE_CRON.PublicUrlError):
                RELIABLE_CRON.validate_public_http_url(url)

    def test_http_worker_pins_validated_addresses_against_dns_rebinding(self) -> None:
        public = [(2, 1, 6, "", ("93.184.216.34", 443))]
        private = [(2, 1, 6, "", ("127.0.0.1", 443))]
        resolver = mock.Mock(side_effect=[public, private])
        with mock.patch.object(RELIABLE_CRON.socket, "getaddrinfo", resolver):
            policy = RELIABLE_CRON.PublicAddressPolicy()
            policy.validate("https://public.example/path")
            connected_addresses = policy.getaddrinfo("public.example", 443, type=RELIABLE_CRON.socket.SOCK_STREAM)
        self.assertEqual(connected_addresses, public)
        self.assertEqual(resolver.call_count, 1)

    def test_http_redirects_are_revalidated_before_following(self) -> None:
        handler = RELIABLE_CRON.PublicRedirectHandler()
        request = RELIABLE_CRON.urllib.request.Request("https://public.example/start")
        with self.assertRaises(RELIABLE_CRON.PublicUrlError):
            handler.redirect_request(request, None, 302, "Found", {}, "http://127.0.0.1/private")

    def test_http_worker_revalidates_final_url_and_redacts_errors(self) -> None:
        class Connection:
            def __init__(self) -> None:
                self.value = None
            def send(self, value: object) -> None:
                self.value = value
            def close(self) -> None:
                pass
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_args: object) -> None:
                pass
            def geturl(self) -> str:
                return "http://127.0.0.1/private?token=redirect-secret"
        class Opener:
            def open(self, _request: object, timeout: float):
                self.timeout = timeout
                return Response()
        public = [(2, 1, 6, "", ("93.184.216.34", 80))]
        connection = Connection()
        with mock.patch.object(RELIABLE_CRON.socket, "getaddrinfo", side_effect=[public, [(2, 1, 6, "", ("127.0.0.1", 80))]]), \
             mock.patch.object(RELIABLE_CRON.urllib.request, "build_opener", return_value=Opener()):
            RELIABLE_CRON.http_worker("http://public.example/start?token=request-secret", 1, connection)
        rendered = json.dumps(connection.value)
        self.assertIn("destination is not public", rendered)
        self.assertNotIn("request-secret", rendered)
        self.assertNotIn("redirect-secret", rendered)

    def test_http_retry_success_is_deterministic(self) -> None:
        args = RELIABLE_CRON.argparse.Namespace(
            url=["https://public.example/item?token=secret"], attempts=3, interval=0,
            request_timeout=1.0, total_timeout=2.0,
        )
        outcomes = [
            {"status": 503, "finalUrl": "", "error": "HTTP 503"},
            {"status": 503, "finalUrl": "", "error": "HTTP 503"},
            {"status": 200, "finalUrl": "https://public.example/item", "error": ""},
        ]
        output = io.StringIO()
        with mock.patch.object(RELIABLE_CRON, "hard_timed_http_request", side_effect=outcomes), redirect_stdout(output):
            return_code = RELIABLE_CRON.command_check_http(args)
        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["results"][0]["attempts"], 3)
        self.assertNotIn("secret", output.getvalue())

    def test_http_failure_invalid_secret_redaction_ipv6_and_total_timeout(self) -> None:
        completed, payload = self.run_helper("check-http", "--url", f"{self.base_url}/missing?token=secret", "--attempts", "1")
        rendered = json.dumps(payload); self.assertEqual(completed.returncode, 2); self.assertNotIn("secret", rendered)
        self.assertIn("destination is not public", rendered)
        for url in ("not-a-url", "file:///etc/passwd", "http://user:pass@example.com/"):
            completed, payload = self.run_helper("check-http", "--url", url, "--attempts", "1")
            self.assertEqual(completed.returncode, 2); self.assertEqual(payload["results"][0]["attempts"], 0)
        self.assertEqual(
            RELIABLE_CRON.sanitize_url("http://[2001:4860:4860::8888]:8080/path?q=secret"),
            "http://[2001:4860:4860::8888]:8080/path",
        )
        started = time.monotonic()
        completed, payload = self.run_helper(
            "check-http", "--url", "https://example.com/", "--attempts", "1",
            "--request-timeout", "1", "--total-timeout", "0.01",
        )
        elapsed = time.monotonic() - started
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(payload["results"][0]["error"], "total HTTP validation timeout")
        self.assertLess(elapsed, 0.5)
        started = time.monotonic()
        completed, payload = self.run_helper(
            "check-http", "--url", "https://example.com/", "--attempts", "1",
            "--request-timeout", "0.01", "--total-timeout", "1",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(payload["results"][0]["error"], "wall-clock request timeout")
        self.assertLess(time.monotonic() - started, 0.5)

    def test_operational_stdout_is_single_json_object(self) -> None:
        cases = [("wait", "--file", "/missing", "--timeout", "0"), ("check-files", "--file", "/missing"),
                 ("check-git", "--repo", "/missing"), ("check-http", "--url", "invalid", "--attempts", "1")]
        for case in cases:
            completed, payload = self.run_helper(*case)
            self.assertIn("status", payload); self.assertIn(completed.returncode, (0, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
