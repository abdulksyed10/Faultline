from concurrent.futures import ThreadPoolExecutor
import pytest
from faultline.store import Store, Conflict, Capacity


def test_sqlite_durable_state_and_untrusted_text(tmp_path):
    path = tmp_path / "lab.db"
    store = Store(path)
    job, created = store.submit("run", {"name": "Robert'); DROP TABLE jobs;--"}, "key")
    assert created
    store.update_job(job["id"], status="completed", result={"ok": True})
    restored = Store(path).job(job["id"])
    assert restored["result"] == {"ok": True}
    assert restored["payload"]["name"].startswith("Robert")


def test_concurrent_idempotent_submissions_and_mismatch(tmp_path):
    store = Store(tmp_path / "lab.db")
    with ThreadPoolExecutor(max_workers=6) as pool:
        result = list(pool.map(lambda _: store.submit("run", {"seed": 2}, "same"), range(6)))
    assert len({job["id"] for job, _ in result}) == 1
    assert sum(created for _, created in result) == 1
    with pytest.raises(Conflict):
        store.submit("run", {"seed": 3}, "same")


def test_capacity_and_interrupted_recovery(tmp_path):
    store = Store(tmp_path / "lab.db")
    for _ in range(8):
        store.submit("run", {})
    with pytest.raises(Capacity):
        store.submit("run", {})
    store.recover()
    assert all(j["status"] == "failed" and "Interrupted" in j["error"] for j in store.jobs())
    assert store.submit("run", {})[1]


def test_idempotency_uses_original_request_when_execution_default_changes(tmp_path):
    store = Store(tmp_path / "lab.db")
    identity = {"scenario":{"seed":42},"model_id":None}
    first,_ = store.submit("run", {"scenario":{"seed":42},"model_id":"first"}, "key", identity)
    second,created = store.submit("run", {"scenario":{"seed":42},"model_id":"second"}, "key", identity)
    assert not created
    assert second["id"] == first["id"]
    assert second["payload"]["model_id"] == "first"


def test_result_registration_rolls_back_when_terminal_job_write_fails(tmp_path):
    import sqlite3
    store = Store(tmp_path / "lab.db")
    train,_ = store.submit("train", {})
    run,_ = store.submit("run", {})
    with store.connection() as db:
        db.execute("CREATE TRIGGER reject_completion BEFORE UPDATE ON jobs WHEN NEW.status='completed' BEGIN SELECT RAISE(ABORT,'simulated commit failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        store.complete_model(train["id"], "model", "model.npz", "hash", {})
    with pytest.raises(sqlite3.IntegrityError):
        store.complete_run(run["id"], "model", {}, {})
    assert store.models() == []
    assert store.runs() == []
    assert store.job(train["id"])["status"] == "queued"
