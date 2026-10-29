# Operation and deployment

The verified deployment shape is a single local Python process serving the built frontend. External integrations are deliberately last. This delivery did not create a remote repository, provision cloud resources, or publish the application.

## Local installation

Use Python 3.11+ and Node.js 22.12+. From the project directory:

```sh
python scripts/setup.py
python scripts/dev.py
```

Setup creates `.venv`, installs `requirements-dev.lock`, installs the package editable without resolving extra dependencies, runs `npm ci` from the lockfile and builds the frontend. It needs network access to package registries once. Subsequent application startup, training, diagnosis and evaluation need no internet or API keys.

`python scripts/dev.py --hot` starts the API on 8000 and Vite on 5173. Hot mode requires backend port 8000 because that is the configured proxy target. For a different production-shaped port use `python scripts/dev.py --port 8001`.

Direct invocation in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m faultline --host 127.0.0.1 --port 8000 --data-dir data
```

On Unix use `.venv/bin/python`. `FAULTLINE_DATA_DIR` selects the storage directory; `FAULTLINE_FRONTEND_DIR` selects compiled static assets. OpenBLAS/OMP thread counts default to one for this small workload. If you edit frontend source without hot mode, run `npm --prefix frontend run build` and reload the browser.

Initial startup trains the bootstrap model before accepting requests; later startup reuses existing artifacts. `/api/health` reports the local mode and registered model count. The development helper terminates its child processes on Ctrl+C.

## Container recipe (supplied, not locally built)

```sh
docker compose up --build
```

The multi-stage build compiles React with Node 22 and installs locked Python runtime dependencies in Python 3.11. A non-root user serves port 8000. Compose binds only `127.0.0.1:8000`, and the named volume `faultline-data` persists `/data`. The health check requests `/api/health`; the startup allowance is 45 seconds. A slow machine can take longer for first training.

**Verification status:** Docker Desktop's engine was stopped in the implementation environment. The Dockerfile and Compose file were inspected, and installed-layout static serving has an API regression test, but no successful container build/run is claimed. CI includes a container-build job; CI itself has not run because this directory was not published.

## Persistence and backup

For a simple consistent backup, stop the application, then copy the **entire data directory**, including `faultline.db` and `models/`. Copying only the database omits model artifacts. Copying a live SQLite main file while omitting its WAL can miss committed changes; prefer a stopped copy or implement SQLite's online backup API. Restore into a new directory and launch with `--data-dir` pointing there.

Do not delete models referenced by existing runs. There is no automatic retention, model garbage collection or migration framework beyond schema version 1. Lists show the latest 100 runs/jobs while records remain stored. A restored legacy model without workload support metadata can still load, but new diagnosis abstains until a supported model is trained. Stored historic analyses are not rewritten.

## Failure and capacity behavior

- Only **one application process and one background worker** are supported. Do not use `uvicorn --workers N` or multiple replicas against this data directory.
- At most eight queued/running training, run and benchmark jobs are admitted. Full queues return 503 and `Retry-After`.
- Restart marks unfinished jobs failed. Read the job's error and submit with a new idempotency key to retry.
- Artifact integrity failures surface as failed jobs; preserve the data and investigate rather than overwriting provenance.
- Training bounds are 20–200 epochs; benchmark bounds are 3–48 cases. API scenarios allow 120–600 steps, traffic .5–2, fault severity .2–3, onset at least 20 and duration at least 5, entirely inside the capture.
- No latency, throughput, high-availability, multi-user security or memory-capacity service-level objective has been established.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
.\.venv\Scripts\python.exe scripts/benchmark.py --epochs 60 --count 24 --output docs/benchmarks/default.json
```

The Python test suite isolates data in temporary directories. On this Windows coding sandbox, Python 3.11's asyncio socketpair required permission for local sockets; the tests succeeded when run outside that sandbox restriction. That is an agent execution environment constraint, not an extra application credential or product service dependency.

`pyproject.toml` treats warnings as errors except Starlette's specific deprecated `anyio.abc.BlockingPortal` alias warning. The narrow filter keeps that upstream compatibility warning from obscuring application regressions; it does not suppress general warnings.

## Before public hosting or real telemetry

Choose a provider only after deciding the use case. A private single-process deployment needs durable disk, a proper backup process and access control. Public multi-user use additionally needs authentication/authorization, request origin/CSRF policy, TLS, rate limits, tenancy and data isolation. Multiple workers need durable dispatch/leases and coordinated recovery, generally with a different queue/storage design.

A real telemetry phase needs an explicit schema, collector integration, missing-data/time alignment, measured topology, recalibration, dataset governance and real validation. Do not connect production systems and assume same-generator benchmark scores transfer. No provider selection or credentials are needed for the current local laboratory.
