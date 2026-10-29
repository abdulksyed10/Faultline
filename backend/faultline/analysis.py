"""Inference only reads telemetry arrays. Simulator truth is kept separate."""
import numpy as np
from .topology import SERVICE_IDS, ancestors
from .simulator import simulate, Telemetry
from .schemas import Scenario, Repair


def first_sustained(scores: np.ndarray) -> int | None:
    hits = scores > 1
    for t in range(2, len(hits)):
        if hits[t-2:t+1].all():
            return t - 2
    return None


def analyze(telemetry: Telemetry, detector, baseline=False) -> dict:
    scored = detector.score(telemetry, baseline=baseline)
    scores = scored["scores"]
    ranking = []
    for i, sid in enumerate(SERVICE_IDS):
        onset = first_sustained(scores[:, i])
        evidence = float(np.mean(np.sort(scores[:,i])[-6:]))
        ranking.append({"service": sid, "evidence": round(evidence, 3), "onset": onset,
            "peak_score": round(float(scores[:,i].max()), 3),
            "tail_probability": round(float(scored["tail"][:,i].min()), 5),
            "callers": ancestors(sid), "flagged": onset is not None})
    ranking.sort(key=lambda item: (item["flagged"], item["evidence"]), reverse=True)
    quality = detector.support(telemetry)
    root = ranking[0] if ranking[0]["flagged"] and quality["status"]=="within-support" else None
    services = {}
    for i, sid in enumerate(SERVICE_IDS):
        values = telemetry.values[:,i]
        services[sid] = {"latency": np.round(values[:,0], 3).tolist(), "cpu": np.round(values[:,1], 3).tolist(),
            "errors": np.round(values[:,2], 4).tolist(), "requests": np.round(telemetry.requests[:,i], 1).tolist(),
            "scores": np.round(scores[:,i], 3).tolist(),
            "peak_latency": round(float(values[:,0].max()), 2), "mean_latency": round(float(values[:,0].mean()), 2)}
    return {"timeline": list(range(len(telemetry.values))), "services": services, "quality": quality,
        "diagnosis": {"status": "detected" if root else "inconclusive", "root_service": root["service"] if root else None,
            "onset": root["onset"] if root else None, "ranking": ranking,
            "method": "Known-graph inversion + neural forecast residuals + sustained empirical threshold",
            "caveat": "Ranked evidence under simulator assumptions, not a causal probability."},
        "summary": {"peak_gateway_latency": services["gateway"]["peak_latency"],
            "mean_gateway_latency": services["gateway"]["mean_latency"],
            "flagged_services": sum(r["flagged"] for r in ranking), "steps": len(telemetry.values)},
        "model": {k:v for k,v in detector.metadata.items() if k != "curve"}}


def compare_repair(scenario: Scenario, repair: Repair, detector) -> dict:
    observed, replay = simulate(scenario), simulate(scenario, repair)
    before = observed.values[repair.at:,0,0]
    after = replay.values[repair.at:,0,0]
    baseline = float(before.mean())
    return {"repair": repair.model_dump(), "observed": np.round(observed.values[:,0,0],3).tolist(),
        "replayed": np.round(replay.values[:,0,0],3).tolist(),
        "latency_reduction_pct": round(100*(baseline-float(after.mean()))/max(baseline,1e-9),2),
        "observed_mean_ms": round(baseline,2), "replayed_mean_ms": round(float(after.mean()),2),
        "window": {"start": repair.at, "end": scenario.steps},
        "semantics": "Same-seed simulator intervention: remove the selected service's injected fault at the chosen time. Means use the post-repair window."}
