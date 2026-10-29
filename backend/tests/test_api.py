import time
import pytest
from fastapi.testclient import TestClient
from faultline.api import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    with TestClient(create_app(tmp_path_factory.mktemp("api"))) as client:
        yield client


def await_job(client, job_id):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            assert job["status"] == "completed", job
            return job
        time.sleep(.03)
    pytest.fail("job did not terminate")


def test_bootstrap_health_topology_and_durable_run(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/topology").json()["services"]) == 8
    runs = client.get("/api/runs").json()
    assert runs
    run = client.get(f'/api/runs/{runs[0]["id"]}').json()
    assert run["result"]["diagnosis"]["root_service"] == "database"
    assert client.get(f'/api/runs/{run["id"]}/report').text.startswith("# Faultline")
    assert "attachment" in client.get(f'/api/runs/{run["id"]}/export').headers["content-disposition"]


def test_async_run_lifecycle_repair_and_idempotency(client):
    payload = {"scenario": {"name": "API smoke", "seed": 991, "fault": {"service": "payments", "kind": "errors"}}}
    headers = {"Idempotency-Key": "smoke-create"}
    response = client.post("/api/runs", json=payload, headers=headers)
    assert response.status_code == 202
    duplicate = client.post("/api/runs", json=payload, headers=headers)
    assert duplicate.json()["id"] == response.json()["id"]
    changed = {"scenario": {"name": "different"}}
    assert client.post("/api/runs", json=changed, headers=headers).status_code == 409
    job = await_job(client, response.json()["id"])
    run_id = job["result"]["run_id"]
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["result"]["diagnosis"]["root_service"] == "payments"
    repair = client.post(f"/api/runs/{run_id}/replay", json={"service":"payments","at":100})
    assert repair.status_code == 200
    assert repair.json()["latency_reduction_pct"] > 0
    assert client.post(f"/api/runs/{run_id}/replay", json={"service":"payments","at":999}).status_code == 422


def test_train_and_benchmark_are_real_jobs(client):
    response = client.post("/api/models/train", json={"epochs":20,"seed":19})
    job = await_job(client,response.json()["id"])
    model = client.get(f'/api/models/{job["result"]["model_id"]}').json()
    assert len(model["metadata"]["curve"]) == 20
    bench = client.post("/api/benchmarks", json={"count":3,"model_id":model["id"]})
    result = await_job(client,bench.json()["id"])["result"]
    assert result["case_count"] == 3
    assert result["metrics"]["neural"]["healthy_points"] == 5664


def test_api_rejects_bad_input_and_missing_resources(client):
    assert client.post("/api/runs",json={"scenario":{"traffic":8}}).status_code == 422
    assert client.get("/api/runs/no-such-run").status_code == 404
    assert client.post("/api/runs",json={"scenario":{},"model_id":"../escape"}).status_code == 404
    assert client.get("/api/not-a-route").status_code == 404


def test_empty_idempotency_key_rejected_before_storage(client):
    for _ in range(2):
        assert client.post("/api/runs",json={"scenario":{}},headers={"Idempotency-Key":""}).status_code == 422


def test_same_http_retry_survives_default_model_change(client):
    payload = {"scenario":{"name":"Stable retry","seed":149}}
    headers = {"Idempotency-Key":"stable-after-model-change"}
    first = client.post("/api/runs",json=payload,headers=headers).json()
    benchmark = client.post("/api/benchmarks",json={"count":3},headers={"Idempotency-Key":"stable-benchmark"}).json()
    train = client.post("/api/models/train",json={"epochs":20,"seed":22}).json()
    await_job(client,train["id"])
    retry = client.post("/api/runs",json=payload,headers=headers)
    assert retry.status_code == 202
    assert retry.json()["id"] == first["id"]
    retry_benchmark = client.post("/api/benchmarks",json={"count":3},headers={"Idempotency-Key":"stable-benchmark"})
    assert retry_benchmark.status_code == 202
    assert retry_benchmark.json()["id"] == benchmark["id"]


def test_configured_frontend_works_in_installed_package_layout(tmp_path, monkeypatch):
    dist = tmp_path/"built-ui"
    (dist/"assets").mkdir(parents=True)
    (dist/"index.html").write_text("<html>delivery fixture</html>",encoding="utf-8")
    (dist/"assets"/"app.js").write_text("console.log('fixture')",encoding="utf-8")
    monkeypatch.setenv("FAULTLINE_FRONTEND_DIR",str(dist))
    with TestClient(create_app(tmp_path/"data",bootstrap=False)) as web:
        assert "delivery fixture" in web.get("/").text
        assert web.get("/assets/app.js").status_code == 200
        assert web.get("/api/missing").status_code == 404


def test_report_preserves_workload_abstention_reason(client):
    created = client.post("/api/runs",json={"scenario":{"traffic":2,"seed":133}}).json()
    job = await_job(client,created["id"])
    run_id = job["result"]["run_id"]
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["result"]["quality"]["status"] == "outside-support"
    report = client.get(f"/api/runs/{run_id}/report").text
    assert run["result"]["quality"]["message"] in report
