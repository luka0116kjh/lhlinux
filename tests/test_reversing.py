"""Exercise CLI discovery with an isolated PATH; no system tools are removed."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "scripts" / "lhlinux"
TOOLS = ("strings", "readelf", "objdump", "gdb", "radare2", "r2ai", "python3")


class ReversingCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lhlinux check ")
        self.addCleanup(self.temp.cleanup)
        self.bin = Path(self.temp.name) / "bin"
        self.bin.mkdir()
        self.env = {**os.environ, "PATH": str(self.bin)}
        for helper in ("readlink", "timeout", "jq"):
            if path := shutil.which(helper):
                (self.bin / helper).symlink_to(path)

    def tool(self, name, body='printf "%s fixture 1.0\\n" "${0##*/}"\n'):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)
        return path

    def run_cli(self, *args):
        return subprocess.run(
            ["/bin/bash", str(CLI), *args], env=self.env,
            capture_output=True, text=True, timeout=15,
        )

    def plugin(self, *, metadata_path=True, loaded=True):
        folder = Path(self.temp.name) / "plugins with spaces"
        folder.mkdir()
        plugin = folder / "r2ai.so"
        plugin.touch()
        record = {"name": "r2ai", "version": "1.2.3"}
        if metadata_path:
            record["path"] = str(plugin)
        self.env.update(
            LH_TEST_PLUGIN_JSON=json.dumps([record] if loaded else []),
            LH_TEST_PLUGIN_DIR=str(folder),
            LH_TEST_PLUGIN_LIST="r2ai test plugin" if loaded else "other other plugin",
        )
        self.tool("r2", '''case "$*" in
  *Lcj*) printf '%s\\n' "$LH_TEST_PLUGIN_JSON" ;;
  *"-c Lc"*) printf '%s\\n' "$LH_TEST_PLUGIN_LIST" ;;
  *-NNH*) printf '%s\\n' "$LH_TEST_PLUGIN_DIR" ;;
  *) printf 'radare2 fixture 1.0\\n' ;;
esac
''')
        return plugin

    def test_all_installed_and_versions(self):
        for name in TOOLS:
            self.tool(name)
        result = self.run_cli("reversing", "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Installed: 7 / 7", result.stdout)
        self.assertIn("Missing:   0 / 7", result.stdout)
        for name in TOOLS:
            self.assertIn(str(self.bin / name), result.stdout)
        self.assertIn("fixture 1.0", self.run_cli("reversing", "versions").stdout)

    def test_all_missing_even_python_and_radare(self):
        result = self.run_cli("reversing", "check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("Not installed"), 7)
        self.assertIn("Installed: 0 / 7", result.stdout)

    def test_partial_missing_and_nonexecutable(self):
        self.tool("strings")
        self.tool("gdb").chmod(0o644)
        result = self.run_cli("reversing", "missing")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("[✓]", result.stdout)
        self.assertNotIn("strings", result.stdout)
        self.assertIn("Missing:   6 / 7", result.stdout)

    def test_radare_alias_and_plugin_without_python(self):
        plugin = self.plugin()
        result = self.run_cli("reversing", "check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(self.bin / "r2"), result.stdout)
        self.assertIn(f"{plugin} (radare2 plugin)", result.stdout)
        self.assertIn("Installed: 2 / 7", result.stdout)
        self.assertIn("1.2.3", self.run_cli("reversing", "versions").stdout)

    def test_plugin_without_jq(self):
        plugin = self.plugin()
        (self.bin / "jq").unlink(missing_ok=True)
        self.assertIn(f"{plugin} (radare2 plugin)", self.run_cli("reversing", "check").stdout)

    def test_older_plugin_metadata_without_path(self):
        plugin = self.plugin(metadata_path=False)
        self.assertIn(str(plugin), self.run_cli("reversing", "check").stdout)

    def test_unloaded_plugin_file_is_not_reported_installed(self):
        self.plugin(loaded=False)
        result = self.run_cli("reversing", "check")
        self.assertIn("Installed: 1 / 7", result.stdout)
        self.assertNotIn("(radare2 plugin)", result.stdout)

    def test_symlink_reports_real_path(self):
        real = self.tool("actual-gdb")
        (self.bin / "gdb").symlink_to(real)
        self.assertIn(str(real), self.run_cli("reversing", "check").stdout)

    def test_list_and_invalid_arguments(self):
        result = self.run_cli("reversing", "list")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), list(TOOLS))
        for args in [("reversing",), ("unknown", "check"), ("reversing", "oops"),
                     ("reversing", "check", "extra")]:
            self.assertEqual(self.run_cli(*args).returncode, 2)


if __name__ == "__main__":
    unittest.main()
