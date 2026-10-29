"""Short SQLite transactions; atomic admission and idempotency."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid


class Conflict(Exception):
    pass


class Capacity(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                  payload TEXT NOT NULL, idempotency_key TEXT UNIQUE, input_hash TEXT NOT NULL,
                  progress REAL NOT NULL DEFAULT 0, result TEXT, error TEXT,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS models (
                  id TEXT PRIMARY KEY, artifact TEXT NOT NULL, sha256 TEXT NOT NULL,
                  metadata TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (
                  id TEXT PRIMARY KEY, job_id TEXT UNIQUE NOT NULL, model_id TEXT NOT NULL,
                  scenario TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        result = dict(row)
        for field in ("payload", "result", "metadata", "scenario"):
            if field in result and result[field] is not None:
                result[field] = json.loads(result[field])
        return result

    def submit(self, kind, payload, key=None, identity_payload=None):
        if key == "":
            raise ValueError("Idempotency key must be nonempty")
        payload_text = canonical(payload)
        identity = payload_text if identity_payload is None else canonical(identity_payload)
        fingerprint = hashlib.sha256((kind+":"+identity).encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if key:
                existing = db.execute("SELECT * FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
                if existing:
                    if existing["input_hash"] != fingerprint:
                        raise Conflict("Idempotency key already belongs to a different request")
                    return self.decode(existing), False
            count = db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            if count >= 8:
                raise Capacity("Worker queue is full. Retry after an active job finishes.")
            job_id = uuid.uuid4().hex
            timestamp = now()
            db.execute("INSERT INTO jobs(id,kind,status,payload,idempotency_key,input_hash,created_at,updated_at) VALUES(?,?,'queued',?,?,?,?,?)",
                       (job_id,kind,payload_text,key,fingerprint,timestamp,timestamp))
            return self.decode(db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()), True

    def update_job(self, job_id, **fields):
        if not fields or set(fields)-{"status","progress","result","error"}:
            raise ValueError("Unsupported job update")
        values = [canonical(v) if k=="result" else v for k,v in fields.items()]
        assignments = ",".join(k+"=?" for k in fields)
        with self.connection() as db:
            db.execute(f"UPDATE jobs SET {assignments},updated_at=? WHERE id=?", (*values,now(),job_id))

    def job(self, job_id):
        with self.connection() as db:
            return self.decode(db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone())

    def jobs(self):
        with self.connection() as db:
            return [self.decode(r) for r in db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100")]

    def recover(self):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status='failed',error='Interrupted by server restart. Submit a new job to retry.',updated_at=? WHERE status IN ('queued','running')",(now(),))

    def add_model(self, model_id, artifact, sha256, metadata):
        with self.connection() as db:
            db.execute("INSERT INTO models VALUES(?,?,?,?,?)",(model_id,str(artifact),sha256,canonical(metadata),now()))

    @staticmethod
    def finish(db, job_id, result):
        changed = db.execute("UPDATE jobs SET status='completed',progress=1,result=?,updated_at=? WHERE id=? AND status IN ('queued','running')",
                            (canonical(result),now(),job_id)).rowcount
        if changed != 1:
            raise Conflict("Only an active job can publish a result")

    def complete_model(self, job_id, model_id, artifact, sha256, metadata):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO models VALUES(?,?,?,?,?)",(model_id,str(artifact),sha256,canonical(metadata),now()))
            self.finish(db,job_id,{"model_id":model_id})

    def complete_run(self, job_id, model_id, scenario, result):
        run_id = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?)",(run_id,job_id,model_id,canonical(scenario),canonical(result),now()))
            self.finish(db,job_id,{"run_id":run_id})
        return run_id

    def models(self):
        with self.connection() as db:
            return [self.decode(r) for r in db.execute("SELECT * FROM models ORDER BY created_at DESC")]

    def model(self, model_id):
        with self.connection() as db:
            return self.decode(db.execute("SELECT * FROM models WHERE id=?",(model_id,)).fetchone())

    def add_run(self, job_id, model_id, scenario, result):
        run_id = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?)",(run_id,job_id,model_id,canonical(scenario),canonical(result),now()))
        return run_id

    def runs(self):
        with self.connection() as db:
            rows = db.execute("SELECT id,model_id,scenario,created_at,json_extract(result,'$.summary') AS result FROM runs ORDER BY created_at DESC LIMIT 100")
            return [self.decode(r) for r in rows]

    def run(self, run_id):
        with self.connection() as db:
            return self.decode(db.execute("SELECT * FROM runs WHERE id=?",(run_id,)).fetchone())
