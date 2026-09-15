"""Check installed metadata and imports without opening or executing a ROM."""
from importlib import metadata
import json
from pathlib import Path
import re
import sys
import platform

if platform.python_version() != sys.argv[2]:
    raise SystemExit(f"Expected Python {sys.argv[2]}, got {platform.python_version()}")

lock = Path(sys.argv[1]).read_text()
expected = dict(re.findall(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", lock, re.MULTILINE))
versions = {name: metadata.version(name) for name in expected}
mismatches = {name: {"expected": wanted, "actual": versions[name]}
              for name, wanted in expected.items() if versions[name] != wanted}
if mismatches:
    raise SystemExit(json.dumps({"version_mismatches": mismatches}))

import numpy
from PIL import Image
from nes_py.nes_env import NESEnv

Image.fromarray(numpy.zeros((2, 2, 3), dtype=numpy.uint8))
print(json.dumps({"python": sys.version.split()[0], "executable": sys.executable,
                  "packages": versions, "imports": "ok", "rom_executed": False,
                  "reference_core_equivalence": "unverified"}, indent=2))
