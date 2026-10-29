"""Cross-platform isolated setup: python scripts/setup.py."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ is required")
    environment = ROOT/".venv"
    if not environment.exists():
        venv.create(environment,with_pip=True)
    python = environment/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    subprocess.run([str(python),"-m","pip","install","-r","requirements-dev.lock"],cwd=ROOT,check=True)
    subprocess.run([str(python),"-m","pip","install","--no-deps","-e","."],cwd=ROOT,check=True)
    npm = shutil.which("npm.cmd" if os.name=="nt" else "npm")
    if not npm:
        raise SystemExit("Install Node.js 22.12+ (including npm), then run setup again")
    subprocess.run([npm,"ci","--no-audit","--no-fund"],cwd=ROOT/"frontend",check=True)
    subprocess.run([npm,"run","build"],cwd=ROOT/"frontend",check=True)
    print("\nReady. Run: python scripts/dev.py\nOpen: http://127.0.0.1:8000")


if __name__=="__main__":
    main()
