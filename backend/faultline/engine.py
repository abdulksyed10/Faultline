"""One-process execution owner with immutable, hashed model artifacts."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import logging
from pathlib import Path
import uuid
import numpy as np
from .store import Store
from .schemas import Scenario, Fault
from .simulator import simulate
from .ml.detector import Detector
from .analysis import analyze
from .benchmark import evaluate

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.model_dir = self.data_dir / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.data_dir/"faultline.db")
        self.store.recover()
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="faultline")

    def register(self, detector, job_id=None):
        model_id = uuid.uuid4().hex
        target = self.model_dir/f"{model_id}.npz"
        temp = self.model_dir/f"{model_id}.tmp"
        try:
            detector.save(temp)
            digest = hashlib.sha256(temp.read_bytes()).hexdigest()
            temp.replace(target)
            if job_id:
                self.store.complete_model(job_id,model_id,target.name,digest,detector.metadata)
            else:
                self.store.add_model(model_id,target.name,digest,detector.metadata)
        except Exception:
            temp.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise
        return model_id

    def load_model(self, model_id=None):
        models = self.store.models() if model_id is None else []
        record = models[0] if models else self.store.model(model_id)
        if record is None:
            raise KeyError("Model not found")
        path = self.model_dir / record["artifact"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Model artifact integrity check failed")
        return record["id"], Detector.load(path)

    def bootstrap(self):
        if not self.store.models():
            self.register(Detector.train())
        if not self.store.runs():
            model_id = self.store.models()[0]["id"]
            scenario = Scenario(name="Connection pool exhaustion", seed=42, fault=Fault(service="database",kind="saturation"))
            job,_ = self.store.submit("run", {"scenario":scenario.model_dump(),"model_id":model_id})
            self.execute(job["id"])

    def submit(self, kind, payload, key=None, identity_payload=None):
        job,created = self.store.submit(kind,payload,key,identity_payload)
        if created:
            self.worker.submit(self.execute,job["id"])
        return job

    def execute(self, job_id):
        job = self.store.job(job_id)
        self.store.update_job(job_id,status="running",progress=.01)
        payload = job["payload"]
        def progress(done,total):
            self.store.update_job(job_id,progress=round(.02+.94*done/total,3))
        try:
            if job["kind"] == "train":
                detector = Detector.train(**payload,progress=progress)
                self.register(detector,job_id)
                return
            elif job["kind"] == "run":
                model_id,detector = self.load_model(payload["model_id"])
                scenario = Scenario.model_validate(payload["scenario"])
                telemetry = simulate(scenario)
                analysis = analyze(telemetry,detector)
                healthy = simulate(scenario.model_copy(update={"fault":None}))
                analysis["simulator_reference"] = {"gateway_latency":np.round(healthy.values[:,0,0],3).tolist(),
                    "label":"Same-seed healthy simulator reference; excluded from diagnosis"}
                self.store.complete_run(job_id,model_id,scenario.model_dump(),analysis)
                return
            elif job["kind"] == "benchmark":
                _,detector = self.load_model(payload["model_id"])
                result = evaluate(detector, range(200,200+payload["count"]),progress)
                result["model_id"] = payload["model_id"]
            else:
                raise ValueError("Unknown job kind")
            self.store.update_job(job_id,status="completed",progress=1,result=result)
        except Exception:
            logger.exception("Job %s failed",job_id)
            self.store.update_job(job_id,status="failed",error="Computation failed. See server logs for details; submit a new job to retry.")

    def close(self):
        self.worker.shutdown(wait=True,cancel_futures=False)
