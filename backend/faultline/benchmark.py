"""Held-out synthetic evaluation; truth is used for evaluation only."""
import numpy as np
from .analysis import analyze, first_sustained
from .schemas import Scenario, Fault
from .simulator import simulate, intrinsic
from .topology import SERVICE_IDS
from .ml.features import HISTORY


def evaluate(detector, seeds=None, progress=None) -> dict:
    seeds = list(seeds if seeds is not None else range(200,212))
    reserved = set(detector.metadata["train_seeds"] + detector.metadata["calibration_seeds"] + detector.metadata["validation_seeds"])
    if not seeds or set(seeds) & reserved:
        raise ValueError("Evaluation seeds must be nonempty and disjoint from fitting seeds")
    metrics = {name: {"detected": 0, "localized": 0, "delays": [], "fp": 0, "points": 0, "mae": []} for name in ("neural", "ewma")}
    cases = []
    for index, seed in enumerate(seeds):
        service = SERVICE_IDS[index % 8]
        kind = ["latency", "saturation", "errors"][index % 3]
        scenario = Scenario(seed=seed, traffic=.75 + .2*(index%6),
                            fault=Fault(service=service,kind=kind,severity=.5+.25*(index%6)))
        healthy = simulate(Scenario(seed=seed, traffic=scenario.traffic))
        faulty = simulate(scenario)
        case = {"seed": seed, "service": service, "kind": kind}
        for name, baseline in [("neural",False),("ewma",True)]:
            stat = metrics[name]
            score = detector.score(healthy, baseline=baseline)
            stat["fp"] += int((score["scores"][HISTORY:]>1).sum())
            stat["points"] += score["scores"][HISTORY:].size
            stat["mae"].append(float(np.abs(score["prediction"][:,:,0]-intrinsic(healthy)[HISTORY:,:,0]).mean()))
            result = analyze(faulty, detector, baseline=baseline)["diagnosis"]
            # Event recall asks about a sustained signal inside the fault window.
            # An earlier false alarm is counted separately, not allowed to mask this event.
            fault_scores = detector.score(faulty, baseline=baseline)["scores"]
            onset = first_sustained(fault_scores[scenario.fault.start:scenario.fault.start+scenario.fault.duration,
                                                 SERVICE_IDS.index(service)])
            hit = onset is not None
            stat["detected"] += int(hit)
            stat["localized"] += int(result["root_service"] == service)
            if hit:
                # Decision requires the third point; report decision delay, not retrospective onset.
                stat["delays"].append(onset + 2)
            case[name] = {"root": result["root_service"], "detected": bool(hit)}
        cases.append(case)
        if progress:
            progress(index+1,len(seeds))
    summary = {}
    for name, stat in metrics.items():
        summary[name] = {"detection_recall": stat["detected"]/len(seeds), "top1_accuracy": stat["localized"]/len(seeds),
            "false_positive_rate": stat["fp"]/stat["points"],
            "mean_detection_delay": float(np.mean(stat["delays"])) if stat["delays"] else None,
            "latency_mae_ms": float(np.mean(stat["mae"])), "detected_count": stat["detected"],
            "localized_count": stat["localized"], "healthy_points": stat["points"], "false_positive_points": stat["fp"]}
    return {"seeds": seeds, "case_count": len(seeds), "metrics": summary, "cases": cases,
        "metric_definition": "event-recall-v2: any 3 consecutive origin-score exceedances wholly inside the injected fault window; decision delay includes the third point",
        "limits": "Held-out synthetic seeds on the same fixed graph/generator. Point-level false alarms; event recall; no real-system generalization claim."}
