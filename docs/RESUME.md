# Positioning Faultline honestly

Faultline's strongest story is the integration of numerical ML, falsifiable experiments and reliable product behavior. Its value is not a claim to outperform production diagnosis research or a guarantee that it is “better” than every prior project.

## Resume bullets

Use only claims you can explain and reproduce. Candidate bullets:

- Built Faultline, a React/TypeScript and FastAPI incident investigation lab with an eight-service structural simulator, durable SQLite jobs, stable idempotent submissions, immutable model provenance and deterministic repair replay.
- Implemented a 23→32→3 neural forecaster directly in NumPy, including analytic backpropagation and Adam; added sequence-separated calibration, workload-support abstention and finite-difference gradient tests.
- Evaluated neural and EWMA methods on 24 held-out synthetic incidents: both localized 24/24 origins; neural healthy latency MAE was 0.511 ms versus 0.557 ms, with explicitly reported false alarms and simulator limitations.

Avoid “100% accurate root-cause AI,” “production distributed tracing,” “causal discovery,” “conformal guarantees,” or “automated production remediation.” The system simulates eight services in one process. It does not deploy eight microservices or ingest a real company's traffic.

## What this adds to the existing portfolio

The comparison below uses the supplied public profile **[abdulksyed10](https://github.com/abdulksyed10)**, not the differently named connected GitHub account. Evidence was inspected during this build on October 29, 2026. README/tree descriptions are evidence of advertised scope and visible structure, not a complete implementation/security audit or an attribution of every team contribution to one person.

| Prior project and observed evidence | What Faultline adds |
|---|---|
| [Collectibles](https://github.com/abdulksyed10/Collectibles): README describes Expo/React Native web/Android/iOS, Supabase identity/data, private R2 images, private-by-default entries, public sharing/Explore and moderation workflows. | Explicit numerical learning, gradient validation, calibrated residuals and paired interventions. Collectibles still demonstrates cross-platform product and privacy work that Faultline does not replace. |
| [PaintFlow](https://github.com/abdulksyed10/PaintFlow): README describes a Next/React/TypeScript paint storefront and admin product/inventory/invoice/customer/report surfaces, Dexie/IndexedDB local repositories and planned integrations. | A separately testable Python compute core, persisted async execution, reproducible model artifacts, seed-separated evaluation and quantitative baseline comparison. |
| [Los Pollos Hermanos Drive-Thru System](https://github.com/abdulksyed10/Los-Pollos-Hermanos-Drive-Thru-System): visible Python project with cashier/cook/manager roles, order/menu models, CSV data, diagrams and a report; repository identifies group-project history. | An integrated browser research tool with numerical training, telemetry reasoning, transactional publication and reproducible scenario experiments. Existing role/workflow and collaborative design experience remains relevant. |
| [P1 with Matt & Tommy predictions](https://github.com/abdulksyed10/P1withMattTommy-PredictionsPlayAlong): README describes Next.js/TypeScript, Supabase Postgres/Auth, per-race predictions, admin scoring and leaderboards. | A model trained from scratch, measured error/false-positive tradeoffs and evidence-driven diagnosis rather than user-entered predictions and scoring alone. |
| [CS273A final project](https://github.com/abdulksyed10/CS273A-FinalProject): visible ML notebooks and train/test-label CSV files; no README was available in the inspected tree. | A complete UI/API/storage workflow around ML, reusable model artifacts and operational failure semantics. No claim is made that the notebook's models or research quality were inferior. |
| [SWE225 Assignment 3](https://github.com/abdulksyed10/SWE225-Assignment3): visible Python analytics, indexer, search and test modules. | The combination of learning, graph reasoning, calibrated evaluation and intervention in a demonstrable product. The search project may already show independent algorithmic engineering. |

These comparisons guided scope selection, not a hiring ranking. A strong presentation depends on understanding the implementation and showing why each tradeoff was chosen. Faultline adds a coherent SWE-plus-ML story rather than just another CRUD interface or hosted-model wrapper.

## Interview evidence map

| Claim | Where to demonstrate it |
|---|---|
| “I understand backpropagation” | Derive `ml/network.py` gradients and explain the finite-difference test |
| “I prevent evaluation leakage” | Whole-sequence seeds, training-only scalers, evaluator overlap rejection |
| “I measure against simpler alternatives” | Checked-in benchmark and EWMA calibration; explain where the baseline ties/wins |
| “I distinguish correlation and assumptions” | Known graph inversion, conditional support, synthetic repair semantics |
| “I design reliable application state” | `Store.submit`, transactional `complete_model`/`complete_run`, crash recovery and stable default-model retry tests |
| “I validate user workflows” | Browser create/diagnose/repair, model training, benchmark, archive, download and narrow-layout evidence |

## Next research steps, not delivered claims

A useful extension would compare graph-aware and graph-free baselines under wrong topology, gradual drift, simultaneous faults and weaker injections. A separate real-data study could establish whether this model has value beyond its own generator. A deployment extension could add authenticated users and durable distributed workers. Each deserves its own validation rather than being implied by the current demo.
