"""PyInstaller 打包脚本"""

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconsole",
    "--add-data", "assets;assets",
    "--paths", "src",
    "--collect-all", "rocopath",
    "--collect-all", "ortools",
    "--name", "rocopath",
    "src/rocopath/main.py",
]

print(f"Running: {' '.join(cmd)}")
subprocess.run(cmd, cwd=str(PROJECT_DIR), check=True)
print("Build complete.")
