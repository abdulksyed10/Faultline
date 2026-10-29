import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="Run the local Faultline laboratory")
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=8000)
    parser.add_argument("--data-dir",default=None)
    args = parser.parse_args()
    os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
    os.environ.setdefault("OMP_NUM_THREADS","1")
    if args.data_dir:
        os.environ["FAULTLINE_DATA_DIR"] = args.data_dir
    import uvicorn
    from .api import create_app
    uvicorn.run(create_app(),host=args.host,port=args.port)


if __name__ == "__main__":
    main()
