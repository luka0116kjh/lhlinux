"""Check installer boundaries without downloads or changing real user environments."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/setup-nes-env.sh"


class EnvironmentSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lh env ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / ".local/share/lhlinux"
        self.env = {**os.environ, "HOME": str(self.root)}

    def run_setup(self, *args):
        return subprocess.run(["/bin/bash", str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def test_check_missing_environment_does_not_create_directories(self):
        result = self.run_setup("--check")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(self.base.exists())

    def test_unmanaged_environment_preserved(self):
        environment = self.base / "envs/nes-py-9.0.1"
        environment.mkdir(parents=True)
        sentinel = environment / "user-file"
        sentinel.write_text("preserve this")
        result = self.run_setup()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("unmanaged", result.stderr)
        self.assertEqual(sentinel.read_text(), "preserve this")
        self.assertFalse((environment / ".lhlinux-managed").exists())

    def test_symlink_environment_preserved(self):
        destination = self.root / "other-environment"
        destination.mkdir()
        (destination / ".lhlinux-managed").write_text("lhlinux-nes-v1\n")
        environment = self.base / "envs/nes-py-9.0.1"
        environment.parent.mkdir(parents=True)
        environment.symlink_to(destination, target_is_directory=True)
        result = self.run_setup()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(environment.is_symlink())
        self.assertEqual(list(destination.iterdir()), [destination / ".lhlinux-managed"])

    def test_invalid_options_fail_before_changes(self):
        self.assertEqual(self.run_setup("--invalid").returncode, 2)
        self.assertFalse(self.base.exists())
