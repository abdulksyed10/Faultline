# Faultline implementation checkpoint

Updated: 2026-10-29. The local release is implemented and verified. No API keys are needed locally.

## Read first

- Design: `docs/superpowers/specs/2026-10-29-faultline-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-29-faultline.md`
- Setup: `README.md`
- Verification evidence: `docs/VERIFICATION.md`
- Mathematics and limits: `docs/MODEL_CARD.md`
- Resume positioning and prior-project context: `docs/RESUME.md`

## Delivered

Python/FastAPI backend, deterministic eight-service simulator, NumPy neural forecaster with manually derived gradients and Adam, empirical calibration, workload-support abstention, EWMA baseline, SQLite job/model/run persistence, repair replay, export, React/TypeScript console, documentation, CI and container configuration are in the workspace. The actual supplied GitHub profile is abdulksyed10, as documented in docs/RESUME.md; the connected GitHub account belonged to a different profile.

- Backend: 35 tests passed, independently rerun in 7.54 seconds on 2026-10-29. HTTP tests required local socket access outside this Windows execution sandbox.
- Frontend: 5 tests passed; latest TypeScript and Vite production build succeeded after the mobile CSS fix.
- An independent code review was completed and material findings were fixed with regression coverage: stable default-model idempotency, workload-support abstention, job completion refresh, and atomic job/result publication. Empty idempotency keys and installed-package static serving also have tests.
- The 24-case synthetic evaluation is saved in docs/benchmarks/default.json, with 45,312 healthy service-time points. Neural and EWMA each detected and localized 24/24, with mean decision delay 2 seconds. Neural latency MAE was .511031 ms and FPR 251/45,312; EWMA MAE was .556819 ms and FPR 246/45,312. These results do not establish real-world performance.
- Browser QA covered training, experiment creation, diagnosis, correct and unrelated repair, benchmarking, archive, downloaded report, healthy and unsupported scenarios, and mobile navigation. Final 390px archive retest: document scroll width 375px and a separately scrollable 778px table in a 348px container. No browser console errors were observed during that check.
- Existing runtime records were preserved. The latest example is Connection pool exhaustion · reproducible demo, using a support-aware model. Historical runs are immutable and may predate support metadata.

## Limitations and follow-up

- This is a single-user, single-process research tool with a known synthetic graph. Real telemetry, topology discovery, authentication, distributed workers, public hosting and real-world model validation are future work.
- Docker and CI definitions are present; Docker build was not verified because Docker Desktop's engine was stopped. No remote CI, cloud deployment or public GitHub repository was created.
- Browser QA covered the in-app browser and one emulated mobile viewport, not a complete device or accessibility audit.
- The directory was originally empty and has no initialized Git repository or configured remote. Do not upload it or configure paid services without the user's choice and authorization.
- A server was already listening on 127.0.0.1:8000 during final verification. A second start failed to bind and exited. Start a fresh instance with `python scripts/dev.py`; `python scripts/setup.py` recreates dependencies/build if necessary.
- Preserve `data/` when continuing; tests use temporary directories. Do not overwrite historical runs.

## Restart procedure

Read this checkpoint and docs/VERIFICATION.md, inspect the filesystem and run relevant checks before making new claims. On Windows use .venv/Scripts/python.exe; on Unix use .venv/bin/python. Real-data evaluation and hosting can be pursued as separate follow-up phases.
