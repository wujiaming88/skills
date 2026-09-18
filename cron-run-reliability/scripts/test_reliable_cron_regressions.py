#!/usr/bin/env python3
"""FIFO and real bisect regressions; no external Git remotes or Git config overrides."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("reliable_cron.py")


class ReliableCronRegressionTests(unittest.TestCase):
    def helper(self, *args: str, timeout: float = 10):
        # subprocess.run kills and reaps only its own child if the outer bound fires.
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                            capture_output=True, text=True, timeout=timeout)
        self.assertEqual(len(cp.stdout.splitlines()), 1, cp.stdout)
        self.assertEqual(cp.stderr, "")
        return cp.returncode, json.loads(cp.stdout)

    def git(self, repo: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                              text=True, check=True, timeout=10).stdout.strip()

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"), "POSIX FIFO required")
    def test_fifo_no_writer_check_files_and_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / "no-writer.fifo"
            os.mkfifo(fifo)
            # Do not open or write the FIFO in the fixture.
            for command, expected_exit, expected_status, extra in (
                ("check-files", 2, "FILES_INVALID", []),
                ("wait", 0, "WAIT_TIMEOUT", ["--timeout", "0.15", "--interval", "0.03"]),
            ):
                for flag in ("--file", "--glob"):
                    with self.subTest(command=command, flag=flag):
                        rc, result = self.helper(command, flag, str(fifo), *extra, timeout=1)
                        self.assertEqual(rc, expected_exit)
                        self.assertEqual(result["status"], expected_status)
                        self.assertFalse(result["ok"])
                        invalid = (result["invalidFiles"] if flag == "--file" else
                                   result["invalidGlobMatches"][str(fifo)])
                        self.assertEqual(invalid[str(fifo)], "not-regular-file")

    def bisect_scenario(self, linked: bool):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin, base = root / "origin.git", root / "base"
            self.git(root, "init", "--bare", str(origin))
            self.git(root, "init", "-b", "main", str(base))
            for index in range(4):
                (base / "tracked.txt").write_text(f"commit {index}\n")
                self.git(base, "add", "tracked.txt")
                self.git(base, "commit", "-m", f"fixture {index}")
            self.git(base, "remote", "add", "origin", str(origin))
            self.git(base, "push", "-u", "origin", "main")
            repo = base
            if linked:
                self.git(base, "checkout", "-b", "parking")
                repo = root / "linked"
                self.git(base, "worktree", "add", str(repo), "main")
                self.assertTrue((repo / ".git").is_file())
            self.assertEqual(self.git(repo, "remote", "get-url", "origin"), str(origin))
            for stage in ("before", "during", "after"):
                if stage == "during":
                    self.git(repo, "bisect", "start", "--no-checkout", "HEAD", "HEAD~3")
                elif stage == "after":
                    self.git(repo, "bisect", "reset")
                self.assertEqual(self.git(repo, "symbolic-ref", "--short", "HEAD"), "main")
                self.assertEqual(self.git(repo, "status", "--porcelain=v1"), "")
                raw = self.git(repo, "rev-parse", "--git-path", "BISECT_START")
                marker = Path(raw) if os.path.isabs(raw) else repo / raw
                self.assertEqual(marker.exists(), stage == "during")
                for live in (False, True):
                    with self.subTest(linked=linked, stage=stage, live=live):
                        extra = ["--verify-remote"] if live else []
                        rc, result = self.helper("check-git", "--repo", str(repo),
                                                 "--branch", "main", *extra)
                        self.assertEqual(result["checkedOutBranch"], "main")
                        self.assertTrue(result["branchMatches"])
                        self.assertTrue(result["synced"])
                        self.assertFalse(result["concurrentChangeDetected"])
                        if stage == "during":
                            self.assertEqual(rc, 2)
                            self.assertEqual(result["status"], "GIT_INVALID")
                            self.assertFalse(result["ok"])
                            self.assertFalse(result["clean"])
                            self.assertIn("BISECT_START", result["inProgress"])
                        else:
                            self.assertEqual(rc, 0)
                            self.assertEqual(result["status"], "GIT_OK")
                            self.assertTrue(result["ok"])
                            self.assertTrue(result["clean"])
                            self.assertEqual(result["inProgress"], [])

    def test_bisect_no_checkout_main(self):
        self.bisect_scenario(linked=False)

    def test_bisect_no_checkout_linked_worktree(self):
        self.bisect_scenario(linked=True)


if __name__ == "__main__":
    if "--helper" in sys.argv:
        position = sys.argv.index("--helper")
        SCRIPT = Path(sys.argv[position + 1]).resolve(strict=True)
        del sys.argv[position:position + 2]
    unittest.main()
