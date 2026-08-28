#!/usr/bin/env python3
"""Bounded waiting and mechanical validation for long isolated Cron jobs."""

from __future__ import annotations

import argparse
import glob
import ipaddress
import json
import math
import multiprocessing
import os
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_INTERRUPTED = 130
MAX_WAIT_SECONDS = 86_400.0
MAX_INTERVAL_SECONDS = 3_600.0
MAX_IO_TIMEOUT_SECONDS = 300.0
MAX_TOTAL_HTTP_SECONDS = 1_800.0
MAX_ATTEMPTS = 20
MAX_URLS = 20
PROCESS_GRACE_SECONDS = 0.1

_active_git_processes: set[subprocess.Popen[str]] = set()
_active_http_processes: set[multiprocessing.Process] = set()


class CliError(Exception):
    pass


class InterruptedRun(Exception):
    pass


class PublicUrlError(Exception):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit("ARGUMENT_ERROR", False, error=message)
        raise SystemExit(EXIT_INVALID)


def emit(status_name: str, ok: bool, **details: object) -> None:
    print(json.dumps({"status": status_name, "ok": ok, **details}, ensure_ascii=False, sort_keys=True), flush=True)


def require_absolute(raw: str, kind: str) -> None:
    if not Path(os.path.expanduser(raw)).is_absolute():
        raise CliError(f"{kind} must be absolute: {raw}")


def expand(raw: str) -> str:
    return os.path.abspath(os.path.expanduser(raw))


def inspect_regular_file(raw: str, min_bytes: int) -> tuple[str, str | None, int | None]:
    path = expand(raw)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return path, "missing", None
    except OSError as exc:
        try:
            info = os.lstat(path)
        except FileNotFoundError:
            return path, "missing", None
        except OSError as stat_exc:
            return path, f"os-error:{stat_exc.__class__.__name__}", None
        if stat.S_ISLNK(info.st_mode):
            return path, "symlink-not-allowed", None
        if not stat.S_ISREG(info.st_mode):
            return path, "not-regular-file", None
        return path, f"open-error:{exc.__class__.__name__}", None
    try:
        info = os.fstat(descriptor)
    except OSError as exc:
        return path, f"fstat-error:{exc.__class__.__name__}", None
    finally:
        os.close(descriptor)
    if not stat.S_ISREG(info.st_mode):
        return path, "not-regular-file", None
    if info.st_size < min_bytes:
        return path, "too-small", int(info.st_size)
    return path, None, int(info.st_size)


def inspect_requirements(files: list[str], patterns: list[str], min_bytes: int) -> dict[str, Any]:
    missing_files: list[str] = []
    invalid_files: dict[str, str] = {}
    file_sizes: dict[str, int] = {}
    missing_globs: list[str] = []
    matched_globs: dict[str, list[str]] = {}
    invalid_glob_matches: dict[str, dict[str, str]] = {}

    for raw in files:
        path, error, size = inspect_regular_file(raw, min_bytes)
        if error == "missing":
            missing_files.append(path)
        elif error:
            invalid_files[path] = error
        elif size is not None:
            file_sizes[path] = size

    for raw_pattern in patterns:
        pattern = os.path.expanduser(raw_pattern)
        try:
            candidates = sorted(set(glob.glob(pattern)))
        except (OSError, RuntimeError) as exc:
            candidates = []
            invalid_glob_matches[raw_pattern] = {raw_pattern: f"glob-error:{exc.__class__.__name__}"}
        valid: list[str] = []
        invalid: dict[str, str] = {}
        for candidate in candidates:
            path, error, _size = inspect_regular_file(candidate, min_bytes)
            if error:
                invalid[path] = error
            else:
                valid.append(path)
        matched_globs[raw_pattern] = valid
        if invalid:
            invalid_glob_matches[raw_pattern] = invalid
        if not candidates:
            missing_globs.append(raw_pattern)

    return {
        "evidenceScope": "point-in-time opened-file metadata; paths may change after inspection",
        "missingFiles": missing_files,
        "invalidFiles": invalid_files,
        "fileSizes": file_sizes,
        "missingGlobs": missing_globs,
        "matchedGlobs": matched_globs,
        "invalidGlobMatches": invalid_glob_matches,
    }


def requirements_ok(result: dict[str, Any]) -> bool:
    return not any((result["missingFiles"], result["invalidFiles"], result["missingGlobs"], result["invalidGlobMatches"]))


def command_wait(args: argparse.Namespace) -> int:
    deadline = time.monotonic() + args.timeout
    checks = 0
    while True:
        checks += 1
        result = inspect_requirements(args.file, args.glob, args.min_bytes)
        if requirements_ok(result):
            emit("DONE", True, checks=checks, **result)
            return EXIT_OK
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            emit("WAIT_TIMEOUT", False, checks=checks, **result)
            return EXIT_OK
        time.sleep(min(args.interval, remaining))


def command_check_files(args: argparse.Namespace) -> int:
    result = inspect_requirements(args.file, args.glob, args.min_bytes)
    ok = requirements_ok(result)
    emit("FILES_OK" if ok else "FILES_INVALID", ok, **result)
    return EXIT_OK if ok else EXIT_INVALID


def process_group_exists(process: subprocess.Popen[str]) -> bool:
    try:
        os.killpg(process.pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def stop_git_process_group(process: subprocess.Popen[str]) -> None:
    if process_group_exists(process):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.communicate(timeout=PROCESS_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    if process_group_exists(process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.communicate(timeout=PROCESS_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def run_git(repo: Path, timeout: float, *arguments: str, check: bool = True) -> str:
    env = dict(os.environ)
    env.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"})
    process = subprocess.Popen(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=env,
    )
    _active_git_processes.add(process)
    try:
        stdout, _stderr = process.communicate(timeout=timeout)
        if check and process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, ["git", *arguments])
        return stdout.strip()
    finally:
        stop_git_process_group(process)
        _active_git_processes.discard(process)


def short_git_error(exc: BaseException) -> str:
    if isinstance(exc, subprocess.TimeoutExpired):
        return "Git command timed out"
    if isinstance(exc, subprocess.CalledProcessError):
        return f"Git command failed with exit {exc.returncode}"
    if isinstance(exc, OSError):
        return f"Git process error: {exc.__class__.__name__}"
    return f"Git validation error: {exc.__class__.__name__}"


def git_in_progress(repo: Path, timeout: float) -> list[str]:
    states: list[str] = []
    for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-apply", "rebase-merge"):
        raw = run_git(repo, timeout, "rev-parse", "--git-path", name)
        path = Path(raw if os.path.isabs(raw) else repo / raw)
        if path.exists():
            states.append(name)
    return states


def git_snapshot(repo: Path, timeout: float) -> dict[str, Any]:
    branch = run_git(repo, timeout, "symbolic-ref", "--quiet", "--short", "HEAD", check=False) or None
    return {
        "head": run_git(repo, timeout, "rev-parse", "HEAD"),
        "branch": branch,
        "porcelain": run_git(repo, timeout, "status", "--porcelain=v1", "--untracked-files=all"),
        "inProgress": git_in_progress(repo, timeout),
    }


def command_check_git(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser().resolve()
    try:
        if run_git(repo, args.command_timeout, "rev-parse", "--is-inside-work-tree") != "true":
            raise RuntimeError("not a Git worktree")
        before = git_snapshot(repo, args.command_timeout)
        if args.verify_remote:
            ref = f"refs/heads/{args.branch}"
            remote_output = run_git(repo, args.command_timeout, "ls-remote", "--exit-code", args.remote, ref)
            remote_head = remote_output.splitlines()[0].split()[0]
            source = f"live:{args.remote}/{args.branch}"
        else:
            remote_head = run_git(repo, args.command_timeout, "rev-parse", args.remote_ref)
            source = f"cached:{args.remote_ref}"
        after = git_snapshot(repo, args.command_timeout)
    except (OSError, RuntimeError, IndexError, subprocess.SubprocessError) as exc:
        emit("GIT_ERROR", False, repo=str(repo), error=short_git_error(exc))
        return EXIT_INVALID

    stable = before == after
    clean = stable and before["porcelain"] == "" and not before["inProgress"]
    branch_ok = stable and before["branch"] == args.branch
    synced = stable and before["head"] == remote_head
    ok = clean and branch_ok and synced
    emit("GIT_OK" if ok else "GIT_INVALID", ok, repo=str(repo), clean=clean,
         checkedOutBranch=after["branch"], expectedBranch=args.branch, branchMatches=branch_ok,
         inProgress=after["inProgress"], concurrentChangeDetected=not stable,
         synced=synced, localHead=after["head"], remoteHead=remote_head, remoteSource=source)
    return EXIT_OK if ok else EXIT_INVALID


def parse_http_url(url: str) -> urllib.parse.SplitResult:
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise PublicUrlError("invalid HTTP(S) URL") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise PublicUrlError("invalid HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise PublicUrlError("embedded credentials are not allowed")
    if port is not None and not 1 <= port <= 65535:
        raise PublicUrlError("invalid port")
    return parsed


def sanitize_url(url: str) -> str:
    parsed = parse_http_url(url)
    host = parsed.hostname or ""
    try:
        if isinstance(ipaddress.ip_address(host.split("%", 1)[0]), ipaddress.IPv6Address):
            host = f"[{host}]"
    except ValueError:
        pass
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def validate_public_http_url(url: str) -> urllib.parse.SplitResult:
    parsed = parse_http_url(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise PublicUrlError("destination resolution failed") from exc
    if not addresses:
        raise PublicUrlError("destination resolution returned no addresses")
    for address in addresses:
        raw_address = address[4][0].split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise PublicUrlError("destination resolution returned an invalid address") from exc
        if not ip.is_global:
            raise PublicUrlError("destination is not public")
    return parsed


class PublicAddressPolicy:
    def __init__(self) -> None:
        self._resolver = socket.getaddrinfo
        self._addresses: dict[tuple[str, int], list[Any]] = {}

    def validate(self, url: str) -> urllib.parse.SplitResult:
        parsed = parse_http_url(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self.getaddrinfo(parsed.hostname or "", port, type=socket.SOCK_STREAM)
        return parsed

    def getaddrinfo(self, host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        key = (host.rstrip(".").lower(), int(port))
        if key not in self._addresses:
            try:
                addresses = self._resolver(host, port, *args, **kwargs)
            except OSError as exc:
                raise PublicUrlError("destination resolution failed") from exc
            if not addresses:
                raise PublicUrlError("destination resolution returned no addresses")
            for address in addresses:
                raw_address = address[4][0].split("%", 1)[0]
                try:
                    ip = ipaddress.ip_address(raw_address)
                except ValueError as exc:
                    raise PublicUrlError("destination resolution returned an invalid address") from exc
                if not ip.is_global:
                    raise PublicUrlError("destination is not public")
            self._addresses[key] = addresses
        return self._addresses[key]


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, policy: PublicAddressPolicy | None = None) -> None:
        super().__init__()
        self.policy = policy

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        target = urllib.parse.urljoin(request.full_url, new_url)
        if self.policy is None:
            validate_public_http_url(target)
        else:
            self.policy.validate(target)
        return super().redirect_request(request, file_pointer, code, message, headers, target)


def safe_http_error(exc: BaseException) -> str:
    if isinstance(exc, PublicUrlError):
        return str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"network error: {exc.reason.__class__.__name__}"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "network timeout"
    return f"HTTP validation error: {exc.__class__.__name__}"


def http_worker(url: str, socket_timeout: float, connection: Any) -> None:
    policy = PublicAddressPolicy()
    original_resolver = socket.getaddrinfo
    try:
        policy.validate(url)
        socket.getaddrinfo = policy.getaddrinfo
        request = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-Cron-Validator/1.0"})
        opener = urllib.request.build_opener(PublicRedirectHandler(policy))
        with opener.open(request, timeout=socket_timeout) as response:
            final_url = str(response.geturl())
            policy.validate(final_url)
            connection.send({"status": int(response.status), "finalUrl": sanitize_url(final_url), "error": ""})
    except Exception as exc:
        status_code = int(exc.code) if isinstance(exc, urllib.error.HTTPError) else None
        connection.send({"status": status_code, "finalUrl": "", "error": safe_http_error(exc)})
    finally:
        socket.getaddrinfo = original_resolver
        connection.close()


def stop_http_process(process: multiprocessing.Process) -> None:
    if process.is_alive():
        process.terminate()
    process.join(timeout=PROCESS_GRACE_SECONDS)
    if process.is_alive() and hasattr(process, "kill"):
        process.kill()
        process.join(timeout=PROCESS_GRACE_SECONDS)


def hard_timed_http_request(url: str, deadline: float, request_timeout: float) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        receive.close()
        send.close()
        return {"status": None, "finalUrl": "", "error": "wall-clock request timeout"}
    process = context.Process(target=http_worker, args=(url, min(request_timeout, remaining), send), daemon=True)
    started = False
    try:
        process.start()
        started = True
        _active_http_processes.add(process)
        send.close()
        remaining = deadline - time.monotonic()
        if remaining > 0 and receive.poll(remaining):
            try:
                return receive.recv()
            except EOFError:
                return {"status": None, "finalUrl": "", "error": "HTTP worker exited without a result"}
        return {"status": None, "finalUrl": "", "error": "wall-clock request timeout"}
    finally:
        receive.close()
        send.close()
        if started:
            stop_http_process(process)
            _active_http_processes.discard(process)


def command_check_http(args: argparse.Namespace) -> int:
    deadline = time.monotonic() + args.total_timeout
    results: list[dict[str, Any]] = []
    for raw_url in args.url:
        try:
            display_url = sanitize_url(raw_url)
        except PublicUrlError:
            display_url = "<invalid-url>"
        entry: dict[str, Any] = {"url": display_url, "status": None, "finalUrl": "", "attempts": 0, "error": ""}
        try:
            parse_http_url(raw_url)
        except PublicUrlError as exc:
            entry["error"] = str(exc)
            results.append(entry)
            continue
        for attempt in range(1, args.attempts + 1):
            if deadline - time.monotonic() <= 0:
                entry["error"] = "total HTTP validation timeout"
                break
            entry["attempts"] = attempt
            attempt_deadline = min(deadline, time.monotonic() + args.request_timeout)
            result = hard_timed_http_request(raw_url, attempt_deadline, args.request_timeout)
            if time.monotonic() >= deadline and result.get("status") is None:
                result["error"] = "total HTTP validation timeout"
            entry.update(result)
            status_code = result.get("status")
            if isinstance(status_code, int) and 200 <= status_code < 300:
                break
            if attempt < args.attempts and args.interval > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    entry["error"] = "total HTTP validation timeout"
                    break
                time.sleep(min(args.interval, remaining))
        results.append(entry)

    ok = all(isinstance(item["status"], int) and 200 <= item["status"] < 300 for item in results)
    emit("HTTP_OK" if ok else "HTTP_INVALID", ok, results=results)
    return EXIT_OK if ok else EXIT_INVALID


def add_requirements(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--file", action="append", default=[], help="Required absolute regular file; repeatable")
    parser.add_argument("--glob", action="append", default=[], help="Absolute glob; all matches must be valid")
    parser.add_argument("--min-bytes", type=int, default=1)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=JsonArgumentParser)
    wait_parser = subparsers.add_parser("wait", help="Bounded wait; timeout is a nonfatal checkpoint")
    add_requirements(wait_parser)
    wait_parser.add_argument("--timeout", type=float, default=600)
    wait_parser.add_argument("--interval", type=float, default=30)
    wait_parser.set_defaults(func=command_wait)
    files_parser = subparsers.add_parser("check-files", help="Immediate strict artifact validation")
    add_requirements(files_parser)
    files_parser.set_defaults(func=command_check_files)
    git_parser = subparsers.add_parser("check-git", help="Require target branch, clean worktree, and matching target ref")
    git_parser.add_argument("--repo", required=True)
    git_parser.add_argument("--remote-ref", default="origin/main", help="Cached ref when live verification is off")
    git_parser.add_argument("--remote", default="origin")
    git_parser.add_argument("--branch", default="main", help="Required currently checked-out branch and live target branch")
    git_parser.add_argument("--verify-remote", action="store_true")
    git_parser.add_argument("--command-timeout", type=float, default=30)
    git_parser.set_defaults(func=command_check_git)
    http_parser = subparsers.add_parser("check-http", help="Bounded public HTTP(S) 2xx validation")
    http_parser.add_argument("--url", action="append", required=True)
    http_parser.add_argument("--attempts", type=int, default=3)
    http_parser.add_argument("--interval", type=float, default=10)
    http_parser.add_argument("--request-timeout", type=float, default=20)
    http_parser.add_argument("--total-timeout", type=float, default=300)
    http_parser.set_defaults(func=command_check_http)
    return parser


def finite(name: str, value: float, *, allow_zero: bool, maximum: float) -> None:
    invalid_sign = value < 0 or (not allow_zero and value == 0)
    if not math.isfinite(value) or invalid_sign or value > maximum:
        relation = ">= 0" if allow_zero else "> 0"
        raise CliError(f"{name} must be finite, {relation}, and <= {maximum:g}")


def validate_args(args: argparse.Namespace) -> None:
    if hasattr(args, "min_bytes") and args.min_bytes < 1:
        raise CliError("--min-bytes must be >= 1")
    if hasattr(args, "timeout"):
        finite("--timeout", args.timeout, allow_zero=True, maximum=MAX_WAIT_SECONDS)
    if hasattr(args, "interval"):
        finite("--interval", args.interval, allow_zero=args.command == "check-http", maximum=MAX_INTERVAL_SECONDS)
    if hasattr(args, "request_timeout"):
        finite("--request-timeout", args.request_timeout, allow_zero=False, maximum=MAX_IO_TIMEOUT_SECONDS)
    if hasattr(args, "total_timeout"):
        finite("--total-timeout", args.total_timeout, allow_zero=False, maximum=MAX_TOTAL_HTTP_SECONDS)
    if hasattr(args, "command_timeout"):
        finite("--command-timeout", args.command_timeout, allow_zero=False, maximum=MAX_IO_TIMEOUT_SECONDS)
    if hasattr(args, "attempts") and not 1 <= args.attempts <= MAX_ATTEMPTS:
        raise CliError(f"--attempts must be between 1 and {MAX_ATTEMPTS}")
    if hasattr(args, "url") and len(args.url) > MAX_URLS:
        raise CliError(f"at most {MAX_URLS} --url values are allowed")
    if args.command in {"wait", "check-files"}:
        if not args.file and not args.glob:
            raise CliError("at least one --file or --glob is required")
        for value in args.file:
            require_absolute(value, "--file")
        for value in args.glob:
            require_absolute(value, "--glob")
    if args.command == "check-git":
        require_absolute(args.repo, "--repo")


def cleanup_workers() -> None:
    for process in list(_active_http_processes):
        stop_http_process(process)
        _active_http_processes.discard(process)
    for process in list(_active_git_processes):
        stop_git_process_group(process)
        _active_git_processes.discard(process)


def interruption_handler(_signum: int, _frame: Any) -> None:
    raise InterruptedRun


def main() -> int:
    signal.signal(signal.SIGINT, interruption_handler)
    signal.signal(signal.SIGTERM, interruption_handler)
    try:
        parser = build_parser()
        args = parser.parse_args()
        validate_args(args)
        return int(args.func(args))
    except CliError as exc:
        emit("ARGUMENT_ERROR", False, error=str(exc))
        return EXIT_INVALID
    except InterruptedRun:
        cleanup_workers()
        emit("INTERRUPTED", False)
        return EXIT_INTERRUPTED
    except Exception as exc:
        cleanup_workers()
        emit("INTERNAL_ERROR", False, error=f"{exc.__class__.__name__}")
        return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
