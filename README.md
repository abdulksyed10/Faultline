# Faultline

**A local incident investigation lab for simulated service failures.**

Faultline is a local incident investigation laboratory combining a React console, durable Python jobs, and a neural forecaster implemented directly in NumPy. Inject a fault into an eight-service synthetic commerce graph, trace its effects, inspect likely origins, and test an intervention against the exact same generated workload.

No hosted model APIs, API keys, or external services are required. The services are simulated arrays, not deployed microservices. Root-cause evidence depends on a known graph and simplified propagation rules.

## Run locally

Prerequisites: Python 3.11+ and Node.js 22.12+ with npm. Verified locally on Windows with Python 3.11.0 and Node 22.13.1.

```sh
python scripts/setup.py
python scripts/dev.py
```

Open **http://127.0.0.1:8000** and select **Open the lab** on the landing page. First startup trains a 60-epoch model and creates a demonstration incident. Setup installs locked Python and npm dependencies in the project; the application then works offline. Stop with Ctrl+C. Your experiments and models remain in `data/`.

For hot frontend development: `python scripts/dev.py --hot`, then open http://127.0.0.1:5173. FastAPI's interactive API reference is at http://127.0.0.1:8000/docs.

## What you can do

- Configure latency, saturation, or error faults across eight services; compare against a fault-free control.
- Explore topology, scrub synchronized telemetry, inspect ranked local residuals, and see support-based abstention.
- Repair a chosen service at a chosen time; compare observed and replayed gateway latency under identical random inputs. Repairing an unrelated service has no effect.
- Train immutable 867-parameter models, inspect learning curves and SHA-256 provenance, and benchmark against EWMA on held-out seeds.
- Reopen archived experiments and download Markdown reports or complete JSON through `/api/runs/{id}/export`.

## What the ML actually does

The fixed dependency graph is inverted to recover local latency/error signals. Four history steps, current request rate, time phase, and service identity feed a shared **23 → 32 tanh → 3** network. Standardization, forward pass, analytic backpropagation, minibatches, and Adam are implemented in NumPy without autograd. Independent healthy sequences fit the model and calibrate positive residuals. Three consecutive threshold exceedances establish a sustained signal. Workloads outside recorded training support receive no origin diagnosis.

The model is inspectable and tested, but the benchmark does not establish production incident accuracy or learned causal discovery. See the exact mathematics and assumptions in the [model card](docs/MODEL_CARD.md).

## Reproduced results

The checked-in [24-case report](docs/benchmarks/default.json) uses model seed 7, 60 epochs, test seeds 200–223, and 45,312 healthy service-time points. All cases share the training simulator family and fixed topology.

| Metric | Neural forecaster | EWMA baseline |
|---|---:|---:|
| Fault-window event recall | 24/24 | 24/24 |
| Top-1 origin localization | 24/24 | 24/24 |
| Healthy point false-positive rate | 0.5539% (251/45,312) | 0.5429% (246/45,312) |
| Mean detection decision delay | 2.0 simulated seconds | 2.0 simulated seconds |
| Healthy intrinsic latency MAE | 0.5110 ms | 0.5568 ms |

The neural model improves this forecasting metric; EWMA has slightly fewer point alarms and ties detection/localization. This small synthetic benchmark is not evidence of general superiority. Metrics, denominator definitions, and a corrected event-recall accounting rule are documented in the [model card](docs/MODEL_CARD.md#evaluation).

Reproduce in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark.py --epochs 60 --count 24 --output docs/benchmarks/default.json
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`. Platform/BLAS differences can introduce small numerical differences; timestamps and elapsed time are expected to differ.

## Engineering

FastAPI validates requests and submits to a single bounded background worker. SQLite WAL stores jobs, runs, models, idempotency fingerprints, and terminal results. Artifact publication and model registration preserve immutable provenance; model/run database insertion and terminal job completion share a transaction. Restart recovery marks unfinished jobs failed, with an explicit retry message. Browser requests cancel stale work and refresh completed results before stopping job polling.

| Read next | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Data flow, transactions, API and failure semantics |
| [Model card](docs/MODEL_CARD.md) | Equations, split seeds, calibration, metrics and limits |
| [Demo](docs/DEMO.md) | Five-minute walkthrough and reproducible experiments |
| [Deployment](docs/DEPLOYMENT.md) | Local operation, container, backup and integration boundaries |
| [Resume and comparison](docs/RESUME.md) | Defensible claims, interview talking points, prior-project context |
| [Verification](docs/VERIFICATION.md) | Commands and observed release evidence |
| [Checkpoint](CHECKPOINT.md) | Recoverable implementation state |

Container and CI definitions are supplied. The local Docker daemon was stopped, so a container build was **not verified** in this delivery. No remote repository, deployment, external account, or public service has been created.

## Scope

This release supports one local user, one application process, one worker, and eight queued/running jobs. It intentionally has no authentication, real telemetry collector, topology discovery, distributed worker, or production monitoring guarantee. Error percentages are additive synthetic signals, not measured request-failure probabilities. Public multi-user hosting needs additional engineering; see [deployment boundaries](docs/DEPLOYMENT.md).

Original project code is available under the [MIT license](LICENSE). Dependencies retain their own licenses.
