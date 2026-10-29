# Release verification — October 29, 2026

This records observed local results, not promises about untested environments. Python 3.11.0, Node 22.13.1 and npm 10.9.2 were used on Windows. No remote CI run or cloud deployment was performed.

## Automated evidence

| Check | Observed result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **35 passed in 9.13 s** after evaluator and report regressions |
| `npm --prefix frontend test -- --run` | **5 passed**: numerical formatting/chart extents and delayed/cancelled terminal-job refresh |
| `npm --prefix frontend run build` | TypeScript strict compilation and Vite production build passed; final mobile CSS rebuild recorded below |
| `scripts/benchmark.py --epochs 60 --count 24 --output docs/benchmarks/default.json` | Completed; raw cases, counts, split seeds, curve, fingerprint and environment saved |

Tests cover deterministic simulation, propagation, unrelated repairs, finite inputs and bounds; finite-difference gradients and learnability; artifact round-trip, label-free inference, healthy and unsupported workloads; atomic idempotency/admission, restart recovery, terminal publication; actual asynchronous API training/run/benchmark, report/export, validation and installed-package frontend paths.

Final review issues were reproduced before fixes: default-model changes breaking idempotent retries, missing workload-support abstention, frontend polling releasing state before result refresh, and separate database result/terminal publication. Empty keys and installed-layout static serving received additional coverage. No material independent-review findings were deferred.

Two release-verification regressions were also observed RED then GREEN:

- A scripted detector with an early false alarm and a valid fault-window signal originally scored zero event detections. The corrected evaluator counts the in-window event and reports its third-point decision delay; an early-only signal still does not count.
- An unsupported-workload report originally omitted the abstention reason. The exported report now contains the same support message as the result/UI.

## Real browser evidence

The standalone Playwright tool was blocked by an already-in-use browser profile. Testing continued successfully using the connected in-app browser via CUA; no locked user browser was killed or profile removed.

Observed workflows:

- Loaded the real built frontend from the running FastAPI server.
- Trained a 60-epoch seed-7 model through **Model lab**; queued/running state completed and the model selector refreshed to `c3fb486a41384484b2f80eb7272aeb52`.
- Created a named database-saturation experiment through the dialog. The new run became selected after completion without manual refresh. Postgres was the likely origin at 80 seconds.
- Simulated Postgres repair at step 115: displayed **34.7%** reduction, **216.5 → 141.4 ms**. Changed the repair to Redis Cache: prior comparison cleared and the new result was **0.0%**, **216.5 → 216.5 ms**.
- Clicked the report download link; the completed file `faultline-c1359280.md` contained run/model IDs, the database diagnosis and workload-support explanation.
- Ran a real 24-case benchmark through the UI. Both methods displayed **24/24 event recall and localization**, **2.0 s** decision delay; neural **251/45,312** healthy point alarms and **0.511 ms** MAE, EWMA **246/45,312** and **0.557 ms**.
- Searched the archive by `Browser QA`, reopened the named run, and inspected completed job history.
- Created a seed-133 healthy control, which displayed **Inconclusive / No sustained local signal**.
- Created a traffic-2.0 healthy control via keyboard-operated range input, which displayed **Inconclusive / Origin diagnosis withheld** and the explicit outside-training-support warning. The first automation attempt to fill the range did not update React state; the actual keyboard interaction did. That first preserved run has a misleading QA name but traffic 1.0; no stored data was deleted or rewritten.
- Exercised mobile navigation, model lab, archive and experiment dialog at **390 × 844**; created the final demonstration from the mobile dialog.
- Identified archive page overflow caused by an absolutely positioned screen-reader label outside the table's containing block. Before the CSS correction, document scroll width was **745 px** at a **390 px** viewport. The table scroll container is now positioned so it contains the label. Final retest evidence is recorded below.

## Benchmark interpretation

Both methods tie on these large, abrupt same-generator faults. The neural forecaster has lower intrinsic healthy latency MAE; EWMA has slightly lower healthy point FPR. This supports a reproducible implementation comparison, not universal model superiority. The original 23/24 neural event count used an incorrect first-onset-only rule; the v2 definition corrects event accounting without changing model predictions. See [MODEL_CARD.md](MODEL_CARD.md#evaluation).

## Limits of verification

Docker build/run was not verified because the local Docker engine was stopped. CI definitions are supplied but not remotely run. There was no load test, production telemetry test, real browser/device matrix, exhaustive accessibility audit, internet-facing security audit or multiprocess recovery test. Failed/interrupted job handling is covered by storage/API tests; destructive interruption was not induced against the user's preserved browser demo data.

Browser screenshots from the earlier mobile check are saved under `docs/screenshots/`; the archive image predates the overflow fix. The final archive retest used a 390 × 844 viewport: document scroll width **375 px**, table container client width **348 px**, and table scroll width **778 px**, confirming that horizontal table scrolling is contained. No browser console errors were returned during that retest. The user-facing browser was restored to the investigation view. A process was already listening on port 8000; an attempted second start failed to bind and exited without replacing it. Network-request inspection and a final post-fix screenshot were not completed.
