# Five-minute Faultline demo

Start with `python scripts/dev.py` and open http://127.0.0.1:8000. From the landing page, select **Open the lab**. Setup instructions are in the [README](../README.md). A fresh data directory automatically creates a trained model and a database saturation experiment.

## 1. Establish the experiment

“This is a synthetic commerce system with eight services. Requests follow the arrows; dependency delays propagate in the opposite direction. The graph and propagation coefficients are known assumptions.”

Open **New experiment → Connection pool exhaustion**, keep seed 42, traffic 1.0, onset 80, duration 100 and severity 1.2, then launch. The preset is a narrative label for the simulator's saturation fault; it does not emulate an actual connection pool. The newest model is selected by default.

Point out that job submission is asynchronous and the completed experiment appears without a manual refresh. The active experiment and model identity are persisted.

## 2. Review the diagnosis

Inspect **Postgres** and **API Gateway** on the topology. Both show high latency during the fault; only Postgres has strong sustained local residual evidence after graph inversion. Select **Anomaly**, scrub before and after 01:20, and use play/pause/reset.

“The diagnosis function sees telemetry and known topology, not the injected service label or healthy counterfactual. Structural inversion removes inherited effects, and a small learned model scores the remaining deviations. The evidence ratio is not a probability.”

The default run's likely origin is Postgres with onset 01:20. There are six reachable callers; that count is graph reachability, not proof that every service suffered a user-visible failure.

## 3. Test a falsifiable repair

Keep repair time at 01:55 and select **Postgres → Simulate repair**. In the verified seed-42 run, mean gateway latency over steps 115–239 fell from approximately **216.5 ms to 141.4 ms (34.7%)**.

Change the repair service to **Redis Cache**, then simulate again. The prior comparison clears and the new reduction is **0.0%**. This is an important negative control: an unrelated repair must not silently remove the database fault.

“The simulator uses exactly the same pre-generated random workload for both runs. The intervention only removes the selected service's injected fault after the chosen time. This is not a recommendation to perform an operational repair.”

## 4. Inspect and challenge the model

Open **Model lab**. Show the 23 → 32 → 3 architecture, 867 parameters, 15,104 training windows, validation curve, split seeds and hashes. Click **Train from scratch** with 60 epochs and seed 7. A new immutable model appears when the job completes; old experiments retain their original model.

Select **24 held-out incidents → Run benchmark**. Read both rows, including the baseline's advantages. The checked-in run ties on event recall/localization, improves neural latency MAE, and shows slightly lower EWMA healthy point FPR. See the [model card](MODEL_CARD.md) for exact denominators and limitations.

## 5. Show honest failure boundaries and persistence

Create **Healthy control** with seed 133 and traffic 1.0. The supported no-signal result says **Inconclusive**, not a promise of health. Create another healthy control at traffic 2.0: workload support is exceeded, so the UI explicitly withholds origin diagnosis while retaining residual plots.

Open **Experiments**, filter by name/service, and reopen a prior run. Download its Markdown report using the download icon. For full JSON, use `/api/runs/{run_id}/export` (the run ID is available from the archive and report).

Stop/restart the application and reopen the archive. Existing models/runs remain. Interrupted jobs are marked failed and need a new submission; the release intentionally does not pretend to resume arbitrary computation.

## Suggested interview questions

- Why use graph inversion before an MLP? What breaks when the graph is wrong?
- Why split by sequence instead of random overlapping windows?
- Why compare against EWMA, and when would you choose the baseline?
- How does the idempotency fingerprint remain stable when the default model changes?
- What state can a crash leave between file rename and SQLite commit?
- What would need to change for real telemetry or multiple workers?

## Reusable browser smoke outline

The complete browser check was performed with the connected in-app browser; it did not rely only on HTTP tests. Repeat with a fresh local app: train → create → wait for selected result → inspect evidence → repair origin → repair unrelated service → download report → benchmark → archive search/reopen → workload-support abstention → narrow viewport. Check console errors and overflow. The exact observed release evidence lives in [VERIFICATION.md](VERIFICATION.md).
