"""Workspace metadata tests against disposable local repositories."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "scripts/lhlinux"


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lh workspace ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "README.md").write_text("original\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True, timeout=10)

    def run_cli(self, *args):
        return subprocess.run(["/bin/bash", str(CLI), "workspace", *map(str, args)],
                              cwd=self.root, capture_output=True, text=True, timeout=10)

    def test_staged_unstaged_untracked_without_file_contents(self):
        (self.root / "README.md").write_text("secret-body-should-not-be-read\n")
        (self.root / "staged.txt").write_text("private staged contents\n")
        self.git("add", "staged.txt")
        (self.root / "untracked.txt").write_text("private untracked contents\n")
        result = self.run_cli("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["directory"], str(self.root))
        self.assertIn("README.md", data["entrypoints"])
        self.assertIn("untracked.txt", data["git"]["status"])
        self.assertIn("README.md", data["git"]["unstaged"])
        self.assertIn("staged.txt", data["git"]["staged"])
        self.assertNotIn("secret-body", result.stdout)
        self.assertNotIn("private", result.stdout)

    def test_large_status_is_bounded_and_marked(self):
        for index in range(120):
            (self.root / f"untracked-{index:03}.txt").touch()
        data = json.loads(self.run_cli("--json").stdout)
        self.assertIn("[truncated]", data["git"]["status"])
        self.assertLessEqual(len(data["git"]["status"].encode()), 4096)

    def test_non_repository_still_reports_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli(directory, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIsNone(data["git"]["status"])
        self.assertIn("python3", data["tools"])

    def test_external_diff_driver_is_not_executed(self):
        marker = self.root / "EXECUTED"
        driver = self.root / "diff-driver"
        driver.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
        driver.chmod(0o755)
        self.git("config", "diff.external", str(driver))
        self.git("config", "core.fsmonitor", str(driver))
        (self.root / "README.md").write_text("changed\n")
        result = self.run_cli("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_invalid_path_and_option(self):
        self.assertEqual(self.run_cli(self.root / "missing").returncode, 1)
        self.assertEqual(self.run_cli(self.root / "README.md").returncode, 1)
        self.assertEqual(self.run_cli("--unknown").returncode, 2)

    def test_special_path_and_terminal_control_characters(self):
        child = self.root / "space 한글;$(touch EXECUTED)\x1b[31m"
        child.mkdir()
        result = self.run_cli(child)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\x1b", result.stdout + result.stderr)
        self.assertFalse((self.root / "EXECUTED").exists())
