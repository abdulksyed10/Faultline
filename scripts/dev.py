"""Run the production-shaped local app; optional --hot starts Vite too."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hot",action="store_true",help="Also start Vite at http://127.0.0.1:5173")
    parser.add_argument("--port",type=int,default=8000)
    args = parser.parse_args()
    python = ROOT/".venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not python.exists():
        raise SystemExit("Run python scripts/setup.py first")
    if args.hot and args.port!=8000:
        raise SystemExit("Hot mode's proxy expects backend port 8000")
    npm = shutil.which("npm.cmd" if os.name=="nt" else "npm")
    if not args.hot and not (ROOT/"frontend/dist/index.html").exists():
        if not npm:
            raise SystemExit("Node/npm is required to build the frontend")
        subprocess.run([npm,"run","build"],cwd=ROOT/"frontend",check=True)
    env = dict(os.environ,OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1")
    processes = []
    try:
        processes.append(subprocess.Popen([str(python),"-m","faultline","--port",str(args.port)],cwd=ROOT,env=env))
        if args.hot:
            if not npm:
                raise SystemExit("npm is required for hot mode")
            processes.append(subprocess.Popen([npm,"run","dev"],cwd=ROOT/"frontend",env=env))
        print(f"Open http://127.0.0.1:{5173 if args.hot else args.port} — first startup trains the default model.")
        while all(p.poll() is None for p in processes):
            time.sleep(.3)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__=="__main__":
    main()
