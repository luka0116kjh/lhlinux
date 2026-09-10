"""Mock external AI CLIs; tests do not log in or make paid requests."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "lhlinux"
spec = importlib.util.spec_from_file_location("context", ROOT / "scripts/lib/context.py")
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


class AICommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lhlinux ai ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.record = self.root / "record.json"
        self.target = self.root / "chall;$(touch INJECTED)"
        self.target.write_bytes(b"\x7fELF\x00fixture strings\n")
        self.env = {**os.environ, "PATH": str(self.bin), "NO_COLOR": "1",
                    "LH_TEST_RECORD": str(self.record), "OPENAI_API_KEY": "secret-must-not-appear"}
        for helper in ("readlink", "timeout", "head", "jq", "python3", "mktemp", "rm", "cat"):
            if path := shutil.which(helper):
                (self.bin / helper).symlink_to(path)

    def run_cli(self, *args):
        return subprocess.run(["/bin/bash", str(CLI), *map(str, args)],
                              cwd=self.root, env=self.env, capture_output=True, text=True, timeout=20)

    def provider(self, name, version_code=0, result_code=0, daemon_code=0, delay=0, execution_delay=0):
        path = self.bin / name
        path.write_text(f'''#!{sys.executable}
import json, os, sys, time
if '--version' in sys.argv:
    time.sleep({delay})
    if {version_code} == 0: print('\\033[32m{name} 1.2.3\\033[0m')
    sys.exit({version_code})
if sys.argv[1:] == ['list']:
    sys.exit({daemon_code})
with open(os.environ['LH_TEST_RECORD'], 'w') as stream:
    json.dump({{'argv': sys.argv[1:], 'stdin': sys.stdin.read()}}, stream)
time.sleep({execution_delay})
print('provider response')
print('provider diagnostic', file=sys.stderr)
sys.exit({result_code})
''')
        path.chmod(0o755)
        return path

    def test_none_installed_json_exit_one(self):
        result = self.run_cli("ai", "check", "--json", "--no-color")
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout)["providers"]
        self.assertEqual(len(data), 4)
        self.assertTrue(all(not p["installed"] for p in data))
        self.assertNotIn("secret-must-not-appear", result.stdout + result.stderr)

    def test_version_failure_does_not_hide_installation(self):
        self.provider("codex", version_code=1)
        self.provider("claude")
        result = self.run_cli("ai", "check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)["providers"]
        self.assertTrue(rows[0]["installed"])
        self.assertEqual(rows[0]["version"], "unknown")
        self.assertEqual(rows[1]["version"], "claude 1.2.3")
        self.assertNotIn("\x1b", result.stdout)

    def test_nonexecutable_and_daemon_failure(self):
        self.provider("codex").chmod(0o644)
        self.provider("ollama", daemon_code=1)
        result = self.run_cli("ai", "check", "--json")
        self.assertEqual(result.returncode, 1)
        rows = json.loads(result.stdout)["providers"]
        self.assertFalse(rows[0]["installed"])
        self.assertTrue(rows[2]["installed"])
        self.assertFalse(rows[2]["available"])
        self.assertEqual(rows[2]["daemon"], "unreachable")

    def test_hung_version_is_bounded_and_other_providers_checked(self):
        self.provider("codex", delay=10)
        self.provider("claude")
        start = time.monotonic()
        result = self.run_cli("ai", "check", "--json")
        self.assertLess(time.monotonic() - start, 7)
        rows = json.loads(result.stdout)["providers"]
        self.assertEqual(rows[0]["version"], "unknown")
        self.assertTrue(rows[1]["installed"])

    def test_dry_run_needs_no_provider_and_never_runs_target(self):
        self.target.write_text("#!/bin/sh\ntouch INJECTED\n")
        self.target.chmod(0o755)
        result = self.run_cli("reversing", "ask", self.target, "--dry-run", "--max-bytes", "2048",
                              "--", "설명해 주세요; $(touch INJECTED)")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(hashlib.sha256(self.target.read_bytes()).hexdigest(), result.stdout)
        self.assertIn("### additional question", result.stdout)
        self.assertLessEqual(len(result.stdout.encode()), 2048)
        self.assertFalse((self.root / "INJECTED").exists())
        self.assertFalse(self.record.exists())

    def test_target_and_option_errors(self):
        self.assertEqual(self.run_cli("reversing", "ask", self.root, "--dry-run").returncode, 1)
        self.assertEqual(self.run_cli("reversing", "ask", self.root / "absent", "--dry-run").returncode, 1)
        for option, value in [("--strings-limit", "0"), ("--max-bytes", "oops"),
                              ("--timeout", "0"), ("--disasm-limit", "999999999")]:
            result = self.run_cli("reversing", "ask", self.target, "--dry-run", option, value)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_missing_provider_exit_two_and_install_hint(self):
        result = self.run_cli("reversing", "ask", "codex", self.target)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Install:", result.stderr)

    def test_codex_receives_stdin_only_and_streams_unchanged(self):
        self.provider("codex", result_code=37)
        result = self.run_cli("reversing", "ask", "codex", self.target, "--", "a unique question")
        self.assertEqual(result.returncode, 37, result.stderr)
        record = json.loads(self.record.read_text())
        self.assertIn("a unique question", record["stdin"])
        self.assertNotIn("a unique question", " ".join(record["argv"]))
        self.assertNotIn(str(self.target), record["argv"])
        self.assertEqual(record["argv"][-1], "-")
        self.assertIn("read-only", record["argv"])
        self.assertEqual(result.stdout, "provider response\n")
        self.assertIn("provider diagnostic", result.stderr)
        self.assertNotIn("secret-must-not-appear", result.stdout + result.stderr + self.record.read_text())

    def test_automatic_priority_and_broken_runtime_skipped(self):
        self.provider("codex", version_code=127)
        self.provider("claude")
        self.provider("ollama")
        result = self.run_cli("reversing", "ask", self.target)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Selected provider: claude", result.stderr)
        argv = json.loads(self.record.read_text())["argv"]
        self.assertIn("--print", argv)
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.provider("codex")
        result = self.run_cli("reversing", "ask", self.target)
        self.assertIn("Selected provider: codex", result.stderr)

    def test_local_requires_explicit_model_and_passes_it_as_one_argument(self):
        self.provider("ollama")
        result = self.run_cli("reversing", "ask", "local", self.target)
        self.assertEqual(result.returncode, 2)
        result = self.run_cli("reversing", "ask", "local", self.target, "--model", "--help")
        self.assertEqual(result.returncode, 2)
        result = self.run_cli("reversing", "ask", "local", self.target, "--model", "fixture:model")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text())["argv"], ["run", "fixture:model", "--nowordwrap"])

    def test_provider_timeout_and_private_prompt_cleanup(self):
        temporary = self.root / "private"
        temporary.mkdir()
        self.env["TMPDIR"] = str(temporary)
        self.provider("codex", execution_delay=10)
        result = self.run_cli("reversing", "ask", "codex", self.target, "--timeout", "1")
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertEqual(list(temporary.iterdir()), [])

    def test_r2ai_plugin_adapter_uses_fixed_command_not_repl(self):
        plugin = self.root / "r2ai.so"
        plugin.touch()
        path = self.bin / "r2"
        path.write_text(f'''#!{sys.executable}
import json, os, sys
if 'Lcj' in sys.argv:
    print(json.dumps([{{'name':'r2ai','version':'1.4.4','path':{str(plugin)!r}}}]))
else:
    with open(os.environ['LH_TEST_RECORD'], 'w') as stream:
        json.dump({{'argv':sys.argv[1:],'stdin':sys.stdin.read()}}, stream)
    print('plugin response')
''')
        path.chmod(0o755)
        result = self.run_cli("reversing", "ask", "r2ai", self.target)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(self.record.read_text())
        self.assertIn("r2ai -i /dev/stdin", record["argv"])
        self.assertIn("# lhlinux static analysis", record["stdin"])

    def test_help_routes(self):
        for args in [("--help",), ("ai", "--help"), ("reversing", "--help"), ("reversing", "ask", "--help")]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("lhlinux", result.stdout)


class ContextTests(unittest.TestCase):
    def test_multibyte_budget_preserves_sections_and_marks_truncation(self):
        text = context.assemble("File: test\nSize: 1\nSHA256: hash\n",
                                [("strings", "한글" * 3000), ("objdump", "A" * 3000)], "질문" * 1000, 2048)
        self.assertLessEqual(len(text.encode()), 2048)
        self.assertIn("### strings", text)
        self.assertIn("### objdump", text)
        self.assertIn("### additional question", text)
        self.assertIn("[truncated]", text)

    def test_collection_bounds_lines_bytes_and_timeout(self):
        text = context.collect([sys.executable, "-c", "print('line\\n' * 10000)"], 4096, line_limit=3)
        self.assertEqual(text.count("line"), 3)
        self.assertIn("[truncated]", text)
        text = context.collect([sys.executable, "-c", "print('A' * 10000)"], 128)
        self.assertLessEqual(len(text.encode()), 128)
        self.assertIsNone(context.collect([sys.executable, "-c", "import time; time.sleep(2)"], 128, timeout=0.1))
        self.assertIsNone(context.collect([sys.executable, "-c", "raise SystemExit(4)"], 128))

    def test_context_tools_use_argument_arrays_and_never_the_target_as_program(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "--untrusted;$(touch marker)"
            target.write_bytes(b"\x7fELF\0hello")
            calls = []

            def fake_collect(argv, limit, **kwargs):
                calls.append(argv)
                return "000 <main>:\n000 <_start>:\nfixture"

            with patch.object(context, "collect", side_effect=fake_collect):
                text = context.build_context(target)
            self.assertEqual({argv[0] for argv in calls}, {"file", "strings", "readelf", "objdump"})
            self.assertTrue(all(argv[-1].startswith("/proc/self/fd/") for argv in calls))
            self.assertIn(hashlib.sha256(target.read_bytes()).hexdigest(), text)


if __name__ == "__main__":
    unittest.main()
