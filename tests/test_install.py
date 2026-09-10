"""Exercise installation helpers only, without installing packages or services."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


LIBRARY = Path(__file__).resolve().parents[1] / "scripts/lib/install.sh"


class InstallHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lhlinux install ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.write_text("original example\n")
        self.target = self.root / "target"

    def run_helper(self, function, *args, env=None):
        return subprocess.run(
            ["/bin/bash", "-eu", "-o", "pipefail", "-c",
             'source "$1"; shift; "$@"', "test", str(LIBRARY), function, *map(str, args)],
            capture_output=True, text=True, timeout=5, env=env)

    def install_example(self):
        result = self.run_helper("install_example", self.source, self.target, os.getuid(), os.getgid())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_new_example_installed_but_user_edits_preserved_on_resume(self):
        self.install_example()
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        self.target.write_text("user's work\n")
        self.install_example()
        self.assertEqual(self.target.read_text(), "user's work\n")

    def test_existing_symlinks_and_directories_preserved(self):
        for kind in ("symlink", "dangling", "directory"):
            with self.subTest(kind=kind):
                self.target = self.root / kind
                if kind == "directory":
                    self.target.mkdir()
                else:
                    self.target.symlink_to(self.source if kind == "symlink" else self.root / "absent")
                self.install_example()
                self.assertEqual(self.source.read_text(), "original example\n")
                self.assertTrue(self.target.is_dir() if kind == "directory" else self.target.is_symlink())

    def fetch(self, payload, *, fail=False):
        binary = self.root / "bin"
        binary.mkdir(exist_ok=True)
        curl = binary / "curl"
        # Match the helper's curl argument contract; never access the network.
        curl.write_text("#!/bin/bash\n" + ("exit 22\n" if fail else 'printf %s "$PAYLOAD" > "$5"\n'))
        curl.chmod(0o755)
        env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "PAYLOAD": payload}
        expected = hashlib.sha256(b"verified archive").hexdigest()
        return self.run_helper("fetch", "https://example.invalid/archive", self.target, expected, env=env)

    def test_invalid_cache_replaced_only_after_verification(self):
        self.target.write_text("interrupted download")
        result = self.fetch("wrong archive")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_text(), "interrupted download")
        result = self.fetch("verified archive")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.target.read_text(), "verified archive")
        self.assertFalse(Path(f"{self.target}.part").exists())

    def test_valid_cache_skips_download(self):
        self.target.write_text("verified archive")
        result = self.fetch("", fail=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_failed_download_does_not_publish_archive(self):
        result = self.fetch("", fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())
