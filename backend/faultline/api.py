from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .engine import Engine
from .store import Conflict, Capacity
from .schemas import RunRequest, TrainRequest, BenchmarkRequest, Repair, Scenario
from .topology import topology
from .analysis import compare_repair


def create_app(data_dir: Path | None = None, bootstrap=True) -> FastAPI:
    directory = data_dir or Path(os.environ.get("FAULTLINE_DATA_DIR",Path(__file__).resolve().parents[2]/"data"))

    @asynccontextmanager
    async def lifespan(app):
        engine = Engine(directory)
        app.state.engine = engine
        try:
            if bootstrap:
                engine.bootstrap()
            yield
        finally:
            engine.close()

    app = FastAPI(title="Faultline laboratory",version="0.1.0",lifespan=lifespan,
                  description="Single-user local incident experiments. Synthetic data; no hosted model APIs.")

    def engine(request: Request) -> Engine:
        return request.app.state.engine

    def found(value, label):
        if value is None:
            raise HTTPException(404,f"{label} not found")
        return value

    def model_id(worker, requested):
        models = worker.store.models()
        chosen = requested or (models[0]["id"] if models else None)
        found(worker.store.model(chosen),"Model")
        return chosen

    def submit(worker,kind,payload,key,identity_payload=None):
        try:
            return worker.submit(kind,payload,key,identity_payload)
        except Conflict as exc:
            raise HTTPException(409,str(exc)) from exc
        except Capacity as exc:
            raise HTTPException(503,str(exc),headers={"Retry-After":"3"}) from exc

    @app.get("/api/health")
    def health(request: Request):
        return {"status":"ok","version":"0.1.0","mode":"local-single-user","models":len(engine(request).store.models())}

    @app.get("/api/topology")
    def graph():
        return topology()

    @app.get("/api/presets")
    def presets():
        return [
            {"name":"Connection pool exhaustion","description":"A database bottleneck echoes across the checkout path.","scenario":{"name":"Connection pool exhaustion","seed":42,"fault":{"service":"database","kind":"saturation"}}},
            {"name":"Payment provider timeout","description":"A latency spike in payments puts checkout under pressure.","scenario":{"name":"Payment provider timeout","seed":91,"fault":{"service":"payments","kind":"latency"}}},
            {"name":"Inventory error burst","description":"An error burst reaches both discovery and checkout.","scenario":{"name":"Inventory error burst","seed":123,"fault":{"service":"inventory","kind":"errors"}}},
            {"name":"Healthy control","description":"A fault-free workload to inspect false alarms.","scenario":{"name":"Healthy control","seed":133}},
        ]

    @app.get("/api/runs")
    def runs(request: Request):
        return engine(request).store.runs()

    @app.post("/api/runs",status_code=202)
    def create_run(body:RunRequest,request:Request,idempotency_key:str|None=Header(default=None,min_length=1,max_length=120)):
        worker = engine(request)
        payload = body.model_dump()
        payload["model_id"] = model_id(worker,body.model_id)
        return submit(worker,"run",payload,idempotency_key,body.model_dump())

    @app.get("/api/runs/{run_id}")
    def run(run_id:str,request:Request):
        return found(engine(request).store.run(run_id),"Experiment")

    @app.get("/api/runs/{run_id}/export")
    def export(run_id:str,request:Request):
        record = found(engine(request).store.run(run_id),"Experiment")
        return JSONResponse(record,headers={"Content-Disposition":f'attachment; filename="faultline-{record["id"][:8]}.json"'})

    @app.get("/api/runs/{run_id}/report",response_class=PlainTextResponse)
    def report(run_id:str,request:Request):
        record = found(engine(request).store.run(run_id),"Experiment")
        result = record["result"]
        ranking = result["diagnosis"]["ranking"]
        quality = result.get("quality", {}).get("message", "Archived analysis predates workload support checks. Create a new experiment with a newly trained model before interpreting its origin diagnosis.")
        rows = "\n".join(f'| {r["service"]} | {r["evidence"]:.3f}Ã— | {r["onset"] if r["onset"] is not None else "â€”"} |' for r in ranking)
        text = f'# Faultline investigation\n\nExperiment: {record["scenario"]["name"]}\n\nRun: {record["id"]}\nModel: {record["model_id"]}\nSeed: {record["scenario"]["seed"]}\n\nStatus: {result["diagnosis"]["status"]}\nLikely origin: {result["diagnosis"]["root_service"] or "inconclusive"}\nPeak gateway response: {result["summary"]["peak_gateway_latency"]} ms\n\nWorkload support: {quality}\n\n| Service | Residual evidence | Onset (s) |\n|---|---:|---:|\n{rows}\n\nEvidence is a calibrated residual ratio, not a causal probability. This experiment uses a known structural synthetic graph. Healthy references and repairs use the simulator and are excluded from diagnosis. No production generalization has been established.\n'
        return PlainTextResponse(text,headers={"Content-Disposition":f'attachment; filename="faultline-{record["id"][:8]}.md"'})

    @app.post("/api/runs/{run_id}/replay")
    def replay(run_id:str,body:Repair,request:Request):
        worker = engine(request)
        record = found(worker.store.run(run_id),"Experiment")
        scenario = Scenario.model_validate(record["scenario"])
        if body.at >= scenario.steps:
            raise HTTPException(422,"Repair time must be inside the experiment")
        _,detector = worker.load_model(record["model_id"])
        return compare_repair(scenario,body,detector)

    @app.get("/api/jobs")
    def jobs(request:Request):
        return engine(request).store.jobs()

    @app.get("/api/jobs/{job_id}")
    def job(job_id:str,request:Request):
        return found(engine(request).store.job(job_id),"Job")

    @app.get("/api/models")
    def models(request:Request):
        return engine(request).store.models()

    @app.get("/api/models/{selected_id}")
    def model(selected_id:str,request:Request):
        return found(engine(request).store.model(selected_id),"Model")

    @app.post("/api/models/train",status_code=202)
    def train(body:TrainRequest,request:Request,idempotency_key:str|None=Header(default=None,min_length=1,max_length=120)):
        return submit(engine(request),"train",body.model_dump(),idempotency_key)

    @app.post("/api/benchmarks",status_code=202)
    def benchmark(body:BenchmarkRequest,request:Request,idempotency_key:str|None=Header(default=None,min_length=1,max_length=120)):
        worker = engine(request)
        payload = body.model_dump()
        payload["model_id"] = model_id(worker,body.model_id)
        return submit(worker,"benchmark",payload,idempotency_key,body.model_dump())

    dist = Path(os.environ.get("FAULTLINE_FRONTEND_DIR",Path(__file__).resolve().parents[2]/"frontend"/"dist"))
    if (dist/"assets").is_dir():
        app.mount("/assets",StaticFiles(directory=dist/"assets"),name="assets")

    @app.get("/{path:path}",include_in_schema=False)
    def frontend(path:str):
        if path.startswith("api/") or path=="api":
            raise HTTPException(404,"API route not found")
        if path=="favicon.svg" and (dist/path).is_file():
            return FileResponse(dist/path)
        if "." in path:
            raise HTTPException(404,"Asset not found")
        if (dist/"index.html").is_file():
            return FileResponse(dist/"index.html")
        return PlainTextResponse("Faultline API is running. Start the frontend with npm run dev, or build frontend assets. API documentation: /docs")

    return app
