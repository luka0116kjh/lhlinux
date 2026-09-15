"""Exercise bounded command logging with harmless synthetic subprocesses."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

CLI = Path(__file__).resolve().parents[1] / "scripts/lhlinux"


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lh run ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def command(self, *args):
        return ["/bin/bash", str(CLI), "run", "--log-dir", str(self.root / "logs"), *map(str, args)]

    def run_cli(self, *args):
        return subprocess.run(self.command(*args), cwd=self.root, capture_output=True, text=True, timeout=10)

    def test_literal_arguments_full_logs_private_metadata_and_exit_code(self):
        result = self.run_cli("--json", "--", sys.executable, "-c",
                              "import sys; print(repr(sys.argv[1:])); print('err', file=sys.stderr); sys.exit(37)",
                              "", "a b", "$(touch INJECTED)", "private-argument")
        self.assertEqual(result.returncode, 37, result.stderr)
        data = json.loads(result.stdout)
        folder = Path(data["log_directory"])
        self.assertIn("private-argument", (folder / "stdout.log").read_text())
        self.assertNotIn("private-argument", (folder / "result.json").read_text())
        self.assertIsNone(data["argv"])
        self.assertEqual((folder / "stderr.log").read_text(), "err\n")
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        self.assertEqual((folder / "stdout.log").stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.root / "INJECTED").exists())

    def test_large_output_is_saved_but_preview_is_short(self):
        result = self.run_cli("--", sys.executable, "-c", "print('A' * 50000); print('END')")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(len(result.stdout), 5000)
        self.assertIn("END", result.stdout)
        folders = list((self.root / "logs").iterdir())
        self.assertEqual((folders[0] / "stdout.log").stat().st_size, 50005)

    def test_timeout_also_stops_child_process(self):
        marker = self.root / "child-finished"
        child = f"import time; from pathlib import Path; time.sleep(2); Path({str(marker)!r}).touch()"
        code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(10)"
        result = self.run_cli("--timeout", "1", "--json", "--", sys.executable, "-c", code)
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertEqual(json.loads(result.stdout)["stop_reason"], "timeout")
        time.sleep(1.2)
        self.assertFalse(marker.exists())

    def test_combined_output_budget(self):
        result = self.run_cli("--max-output-bytes", "1024", "--json", "--", sys.executable,
                              "-c", "import os; os.write(1,b'A'*600); os.write(2,b'B'*600)")
        self.assertEqual(result.returncode, 125, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["stop_reason"], "output_limit")
        self.assertEqual(sum(data["bytes_saved"].values()), 1024)

    def test_distinct_runs_cwd_and_explicit_argument_recording(self):
        folder = self.root / "working directory"
        folder.mkdir()
        seen = []
        for _ in range(2):
            result = self.run_cli("--cwd", folder, "--record-command", "--json", "--",
                                  sys.executable, "-c", "import os; print(os.getcwd())")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            seen.append(data["log_directory"])
            self.assertEqual(data["cwd"], str(folder))
            self.assertIsNotNone(data["argv"])
        self.assertNotEqual(seen[0], seen[1])

    def test_missing_executable_invalid_options_and_closed_stdin(self):
        result = self.run_cli("--json", "--", "./does-not-exist")
        self.assertEqual(result.returncode, 127, result.stderr)
        self.assertEqual(json.loads(result.stdout)["stop_reason"], "launch_error")
        self.assertEqual(self.run_cli("--timeout", "0", "--", "true").returncode, 2)
        self.assertEqual(self.run_cli("--").returncode, 2)
        result = self.run_cli("--", sys.executable, "-c", "import sys; print(len(sys.stdin.read()))")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\n0\n", result.stdout)

    def test_sigterm_writes_a_result(self):
        process = subprocess.Popen(self.command("--json", "--", sys.executable, "-c", "import time; time.sleep(10)"),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not list((self.root / "logs").glob("*/stdout.log")):
                if time.monotonic() > deadline:
                    self.fail("runner did not start")
                time.sleep(0.02)
            os.kill(process.pid, signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143, stderr)
            self.assertEqual(json.loads(stdout)["stop_reason"], "signal")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_logger_starts_with_stale_python_environment_variables(self):
        result = subprocess.run(self.command("--json", "--", "/bin/true"),
                                env={**os.environ, "PYTHONHOME": "/invalid-python-home",
                                     "PYTHONPATH": "/invalid-python-path"},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["exit_code"], 0)
