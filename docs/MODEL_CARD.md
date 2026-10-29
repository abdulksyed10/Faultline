# GRF-1 model card

**Intended use:** local experimentation and explanation of anomaly detection, graph residual diagnosis, and synthetic intervention. **Not validated for:** production incident response, automated remediation, causal discovery, or real telemetry.

GRF-1 is a shared 23-input, 32-hidden-unit tanh network with three outputs and 867 trainable scalars. It is trained locally in NumPy; no autograd framework, pretrained model, hosted LLM, or external inference API is involved.

## Structural data model

Services are ordered gateway, checkout, catalog, payments, inventory, orders, cache, database. `W[i,j]` is the fixed caller-to-dependency weight in `topology.py`. Dependencies have larger indices, so reverse service order produces observed metrics. For time t and service i:

```text
wave(t) = 1 + 0.18 sin(t/23) + 0.08 sin(t/7)
requests(t,i) = 350 × traffic × wave(t) × load_share(i) + Normal(0, 2)
load(t,i) = requests(t,i) / (350 × load_share(i))
local_latency = base_latency(i) × (1 + 0.3 load + 0.16 load²) + 0.5 noise_latency
local_cpu     = 12 + 23 load + 2.2 load² + 0.7 noise_cpu
local_errors  = 0.08 + 0.055 load² + 0.012 noise_errors
observed_latency(i) = local_latency(i) + Σ_j W[i,j] observed_latency(j)
observed_errors(i)  = local_errors(i) + 0.35 Σ_j W[i,j] observed_errors(j)
observed_cpu(i)     = local_cpu(i)
```

Metric noises are independent standard normals; request noise is generated first, then all metric noise, before fault application. Base latencies are `[8,18,12,22,15,17,3,25]` ms and load shares `[1,.62,.8,.5,.65,.4,.7,.85]`. Latency is floored at 0.1 ms, CPU clipped to [0,100], and the error signal floored at zero. The error signal is additive and is **not** a calibrated request-error probability.

During the fault window, a severity-scaled constant adds 110 ms for latency faults, 85 ms and 38 CPU points for saturation, or 9 error points and 20 ms for error bursts. These large, abrupt, single-service effects make many cases easy. There are no real connection pools, network queues, retries, distributed traces or microservice processes.

Structural inversion subtracts the same weighted observed dependency values, recovering local metrics. This assumes the exact graph and coefficients used by the generator. The neural network does not learn these dependencies or discover causality.

## Inputs, learning and gradients

Each service/time row contains four prior local vectors (12 values), current request rate (1), `sin(t/23)` and `cos(t/23)` (2), and one-hot service identity (8). The target is the current local latency, CPU and error vector. Rows are time-major then service-major. The first four points are warmup and carry no evidence.

Training-only means and standard deviations standardize X and Y, with standard deviation floored at 1e-6. For a batch of B rows:

```text
H = tanh(X W1 + b1)
Yhat = H W2 + b2
L = sum((Yhat - Y)²) / (3B)
D = 2 (Yhat - Y) / (3B)
dW2 = HᵀD                       db2 = sum_rows(D)
G = (D W2ᵀ) ⊙ (1 - H²)
dW1 = XᵀG                       db1 = sum_rows(G)
```

Weights use seeded normal initialization with standard deviations `sqrt(2/(23+32))` and `sqrt(2/(32+3))`; biases begin at zero. Batch size is 512; all epochs reshuffle using the model seed. Adam uses learning rate .003, β1=.9, β2=.999, ε=1e-8 with bias-corrected first/second moments. The default is 60 epochs; API accepts 20–200. No early stopping or hyperparameter search selects a favorable benchmark result.

Inference and calibration clip standardized input features to [-5,5]; fitting does not. Forecasts are transformed back to original units. This clipping limits extreme network inputs but is not an out-of-distribution guarantee.

## Splits and provenance

| Split | Seeds | Traffic multipliers | Samples |
|---|---|---|---:|
| Fit | 10–17 | .6,.8,1,1.2,1.4,1.6,1.8,.6 | 15,104 service-time rows |
| Validation curve | 40,41 | 1.1,1.1 | 3,776 rows |
| Residual calibration | 50–53 | .7,1.05,1.4,1.75 | 7,552 rows; 944 per service |
| Checked-in evaluation | 200–223 | .75,.95,1.15,1.35,1.55,1.75 repeated | 24 faults + 24 matched healthy runs |

Each sequence has 240 steps. Splits are by complete seed sequence, so overlapping windows never cross split boundaries. Evaluation rejects overlap with fitting/validation/calibration seeds. Repeated benchmark seeds remain the same held-out test set, not new independent evidence. Testing many model choices against them would turn them into a development set.

Artifacts persist weights, scalers, residual scales, sorted calibration scores, workload support, hyperparameters, training curve, split seeds and the SHA-256 of raw training X/Y bytes. Registry records also contain the SHA-256 of the exact NPZ file. The reproducible report includes model metadata, Python/platform and elapsed time. Artifact hashes can differ across retraining because creation timestamps differ; the data fingerprint is the training-data identity.

## Calibration, evidence and abstention

For each service i and metric k, residual `r = target - prediction`. Calibration RMS residual scales are floored at `[.35 ms, .5 CPU points, .01 error points]`. The scalar raw score is `a(t,i) = max_k(max(r(t,i,k)/scale(i,k), 0))`. This detects positive deviations only.

The threshold q(i) is NumPy's default interpolated 99.5th percentile of calibration raw scores, floored at .1. Displayed evidence is `a/q`. Three consecutive scores strictly greater than 1 mark a sustained signal; onset is the first point of that three-point window. Ranking sorts sustained services first, then the mean of their six largest score ratios. The first supported, sustained service is the likely origin. The historical onset may precede the injected fault if a false alert occurred earlier.

The descriptive tail value is `(1 + count(calibration_score >= observed_score))/(n+1)`. RMS scale and quantile use the same calibration data, temporal observations are dependent, and thresholds are not adaptively updated. **This is empirical calibration, not a conformal coverage guarantee, root-cause probability or posterior confidence.**

Workload support records each service's minimum and maximum training request rate, allowing 2% relative tolerance. If more than 1% of post-warmup service-time request values are outside these bounds, origin diagnosis is withheld; raw residuals remain visible. Legacy models without support metadata also abstain on new analyses. Being within these bounds does not detect all shifts (noise, topology, propagation, joint distribution, etc.). Existing stored analyses are immutable; older analyses show an archive warning rather than being silently recomputed.

## Evaluation

`python scripts/benchmark.py --epochs 60 --count 24 --output docs/benchmarks/default.json` regenerates the [full report](benchmarks/default.json). Cases cycle services and fault types, onset 80, duration 100, severity `.5 + .25*(index % 6)`, and the traffic values above. EWMA predicts the same local targets using α=.35, uses the same structural inversion, and gets its own RMS scales/thresholds on the same calibration seeds.

- **Event recall (v2):** fraction of injected cases with at least one three-point exceedance window for the injected service wholly inside the fault interval. An earlier false alert neither counts for nor masks the event. This is origin-conditioned signal recall, not precision or an operational incident alert rate; raw signals are counted even if support abstention would withhold the origin.
- **Top-1 localization:** fraction whose supported, sustained, whole-run top-ranked service matches the injected origin. Abstention counts as incorrect.
- **Healthy point FPR:** service-time score exceedances divided by all post-warmup healthy service-time observations. This is not a three-point alert rate or an event false-positive rate.
- **Decision delay:** mean time from fault start to the third point of the first wholly in-window qualifying run, only among detected cases. A two-second delay is the earliest possible with the three-point rule.
- **Latency MAE:** absolute forecast error on intrinsic healthy latency, averaged across times/services and then cases. It is not gateway response error or fault reconstruction accuracy.

The default report measures neural/EWMA recall **24/24 and 24/24**, top-1 **24/24 and 24/24**, point FPR **251/45,312 and 246/45,312**, decision delay **2.0 s and 2.0 s**, and latency MAE **0.511031 and 0.556819 ms**. These counts are a small same-generator sanity check. No confidence intervals or real-system validation are claimed.

During release verification, an older evaluator returned neural recall 23/24 because it only examined the first sustained onset over the entire trace. A pre-fault alert masked a valid fault-window signal. A hand-constructed early-alert-plus-event regression failed before the accounting fix and passed afterward; an early-only alert remains a miss. Detector weights, thresholds and telemetry were unchanged. `metric_definition` in the JSON identifies v2, so do not compare older recall numbers without accounting for that definition change.

## Repair interpretation

A repair removes the selected service's injected fault from the specified time onward, then recomputes telemetry with the same seed and pre-generated randomness. It does not change the ordinary background latency or repair other services. The displayed reduction is `(mean observed - mean replayed)/mean observed × 100`, over `[repair_time, run_end)`. It is a simulator intervention, not evidence a real operational action will produce that outcome.

## Boundaries and related work

The system is sensitive to fixed-graph correctness, noise assumptions and workload drift. It does not handle hidden confounding, changing topology, simultaneous faults, realistic retry feedback, missing telemetry, adaptive thresholds or live ingestion. Low residuals do not prove health. The eight-service identity encoding prevents direct generalization to unseen services.

[MicroRCA (NOMS 2020)](https://ieeexplore.ieee.org/document/9110353/) provides related graph-based diagnosis context; this project does not reproduce that system or benchmark against it. [Adaptive Conformal Predictions for Time Series (ICML 2022)](https://proceedings.mlr.press/v162/zaffran22a.html) is relevant to calibration under dependence and shift; those adaptive algorithms and guarantees are not implemented here.
