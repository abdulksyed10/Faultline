# Faultline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. The user delegated implementation; continue without repeated approval gates. Preserve this plan and CHECKPOINT.md across interruptions.

**Goal:** Ship a locally runnable incident investigation lab with a from-scratch neural detector and reproducible repair experiments.

**Architecture:** React/TypeScript console talks to FastAPI. SQLite owns experiment/job/model state; a bounded background worker owns heavy computations. A deterministic simulator and immutable NumPy model artifacts make results reproducible without external services.

**Tech Stack:** Python 3.11+, FastAPI, NumPy, SQLite, pytest, React, TypeScript, Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-29-faultline-design.md`

## Global Constraints

- No API keys or paid services for the local release; external integrations last.
- Single process and one worker; cap 8 nonterminal jobs.
- Eight fixed services; 120..600 one-second steps; seed 0..2^31-1; traffic 0.5..2; severity 0.2..3; onset >=20; duration >=5; fault end <= steps.
- Four history steps; three intrinsic metrics; tanh MLP and Adam implemented in NumPy.
- Disjoint train/calibration/test sequence seeds; scaler trained on training data only.
- Diagnosis never consumes fault metadata or healthy replay; simulator truth labeled separately.
- Empirical tail evidence is not a causal probability or coverage guarantee.
- One-process deployment serves built frontend and uses a persistent data directory.

## Review Focus

1. Concurrent duplicate submissions must create one job, and different inputs using the same key must return conflict.
2. Failed/interrupted training must not leave a partially registered model or a forever-running job.
3. Stale frontend requests must not overwrite a newer run selection or replay selection.
4. An unrelated repair must not change exogenous random inputs or magically fix an incident.
5. Healthy/out-of-distribution telemetry must not receive an unconditional confident diagnosis.

## File map

`backend/faultline/`: `schemas.py` validates input; `topology.py` defines graph; `simulator.py` generates telemetry; `ml/network.py` implements derivatives/Adam; `ml/features.py` isolates structural features; `ml/detector.py` trains/calibrates/serializes; `analysis.py` produces diagnosis and intervention results; `benchmark.py` evaluates; `store.py` owns SQLite; `engine.py` owns jobs/artifacts; `api.py` owns HTTP and static serving; `__main__.py` provides CLI.

`backend/tests/`: simulator, numerics, detector, storage, API and benchmark behavior.

`frontend/src/`: `types.ts` API contract; `api.ts` transport; `App.tsx` shell/data lifecycle; `components/` graph/chart/modal/controls; `views/` investigation/archive/model lab; `styles.css` visual system; `lib/` chart/format helpers and tests.

`scripts/`: setup, dev, benchmark and smoke verification. `docs/`: architecture, ML/model card, demo, deployment, resume, checkpoint. `.github/workflows/ci.yml`, `Dockerfile`, `compose.yaml`, root README and license complete delivery.

## Task 1: Reproducible simulation kernel

**Files:** pyproject.toml; backend/faultline/{__init__,schemas,topology,simulator}.py; backend/tests/test_simulator.py.

**Interfaces:** `Scenario` validates request; `simulate(scenario: Scenario, repair: Repair | None = None) -> Telemetry`; `Telemetry` has arrays `[steps, services, metrics]`, requests `[steps,services]`, service order and scenario; `intrinsic(telemetry)` removes known dependency contributions.

- [x] Write tests for deterministic samples, positive/finite metrics, dependency-only propagation, repair identity on unaffected service, repair removal on injected service, invalid bounds and healthy runs.
- [x] Run `python -m pytest backend/tests/test_simulator.py -q`; observe missing behavior.
- [x] Implement Pydantic contracts, known DAG, pre-generated random workload/noise and structural fault application.
- [x] Run simulator tests; expected all pass. Record result in CHECKPOINT.md.

## Task 2: From-scratch model and honest evaluation

**Files:** backend/faultline/ml/{__init__,network,features,detector}.py; analysis.py; benchmark.py; backend/tests/{test_network,test_detector}.py.

**Interfaces:** `MLP(input_size, hidden_size=32, seed=7)`, `predict(x)`, `loss_and_gradients(x,y)`, `fit(x,y,epochs,...)`; `Detector.train(epochs=60,seed=7,progress=None) -> Detector`; `Detector.score(telemetry) -> dict`; `save(path)` / `load(path)`; `analyze(telemetry,detector) -> dict`; `evaluate(detector,seeds) -> dict`.

- [x] Write finite-difference gradient, learnability, artifact round-trip, calibration, healthy inconclusive and root-origin-versus-downstream tests. Test against no fault labels at inference.
- [x] Run tests before implementation; expected fail for absent model.
- [x] Implement standardization, minibatch tanh MLP, analytic backprop, Adam, sequence seed splits, empirical calibration and safe NPZ serialization.
- [x] Implement local evidence ranking and paired intervention summary. Baseline gets its own calibration with the same feature targets.
- [x] Run numerical/detector suite; expected pass. Run held-out benchmark and save counts, seeds, measurements (no fabricated scores).

## Task 3: Durable API and background execution

**Files:** backend/faultline/{store,engine,api,__main__}.py; backend/tests/{test_store,test_api}.py.

**Interfaces:** `create_app(data_dir: Path | None = None, bootstrap=True) -> FastAPI`; `Store` stores jobs/models/runs; `Engine.submit(kind,payload,key=None)`; endpoints prefixed `/api` and OpenAPI at `/docs`.

- [x] Write durable reload, atomic idempotency, mismatch conflict, interrupted recovery and async end-to-end API tests with temp directories.
- [x] Run tests red; implement short SQLite transactions, immutable artifact registration, bounded executor and real train/run/benchmark/replay workflows.
- [x] Add health/topology/presets/models/jobs/runs/report/export routes; validate all mutation requests; serve built SPA with safe fallback.
- [x] Run full backend suite; expected all pass. Verify a real demo can be loaded without network.

## Task 4: Investigation console

**Files:** frontend/package.json + lock; Vite/TypeScript configs; src/types.ts; api.ts; App.tsx; components/{Icon,Chart,Topology,NewExperiment,Primitives}.tsx; views/{Investigation,Archive,ModelLab}.tsx; styles.css; lib/format.ts and tests.

**Interfaces:** types match actual API responses; run result includes timeline, service summaries, diagnosis and model provenance; repair route returns paired trajectories; new-run modal returns async job ID.

- [x] Add behavioral tests for chart extents, constant-series handling and time formatting; run red before helpers.
- [x] Implement cohesive responsive UI with actual graph/chart data, synchronized scrubber, playback, service selection and evidence.
- [x] Implement create experiment modal, archive selection, model training/benchmark, repair comparison, export, error/retry and job progress.
- [x] Run `npm --prefix frontend test -- --run` and `npm --prefix frontend run build`; expected pass.
- [x] Browser QA on actual local API: create fault -> completed result -> repair comparison; model train/benchmark; archive; export; 390px viewport; keyboard focus.

## Task 5: Delivery and independent review

**Files:** README.md; docs/{ARCHITECTURE,MODEL_CARD,DEMO,DEPLOYMENT,RESUME}.md; CHECKPOINT.md; scripts/{dev,setup,benchmark}.py; Dockerfile; compose.yaml; .github/workflows/ci.yml; .gitignore; LICENSE.

- [x] Write setup/dev/benchmark commands and executable entrypoints; document exact resource limits, seed split and synthetic-data limitations.
- [x] Add one-process container, persistent volume, health check, and CI for tests/build/evaluation.
- [x] Run full backend tests, frontend tests/build, real API smoke and benchmark; save final evidence in checkpoint and benchmark JSON.
- [x] Use requesting-code-review skill and one independent reviewer; fix material defects with regression tests, rerun affected checks.
- [x] Final handoff includes project purpose, start command, measured verification, plan/checkpoint links and any real remaining limitations. External deployment remains last, with provider choice deferred to user.

## Recovery procedure

Read CHECKPOINT.md first, then the spec and unchecked plan tasks. Inspect the current filesystem before rewriting. Use `.venv/Scripts/python.exe` on Windows (`.venv/bin/python` on Unix). Run tests to establish state. Never count a task complete based on a prior narrative without evidence. Do not delete models or runs to make tests pass; tests use temporary directories. Keep runtime data under ignored `data/`. Record changed commands and measurements as you go.
