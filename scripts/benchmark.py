"""Train and evaluate without a running web server."""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
os.environ.setdefault("OMP_NUM_THREADS","1")
import argparse
import json
from pathlib import Path
import platform
import time
from faultline.ml.detector import Detector
from faultline.benchmark import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs",type=int,default=60)
    parser.add_argument("--count",type=int,default=24)
    parser.add_argument("--output",type=Path,default=Path("data/benchmark.json"))
    args = parser.parse_args()
    if not 20<=args.epochs<=200 or not 3<=args.count<=48:
        parser.error("epochs must be 20..200; count must be 3..48")
    start = time.perf_counter()
    model = Detector.train(epochs=args.epochs)
    result = evaluate(model,range(200,200+args.count))
    result["provenance"] = {"model":model.metadata,"python":platform.python_version(),"platform":platform.system(),
        "elapsed_seconds":round(time.perf_counter()-start,3)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result["metrics"],indent=2))
    print(f"Saved complete evidence to {args.output.resolve()}")


if __name__=="__main__":
    main()
