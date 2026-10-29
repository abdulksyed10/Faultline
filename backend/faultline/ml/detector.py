"""Healthy-sequence learning and split empirical residual calibration."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from .network import MLP
from .features import features, HISTORY, ewma_prediction
from ..schemas import Scenario
from ..simulator import simulate, Telemetry


class Detector:
    def __init__(self, network, x_mean, x_std, y_mean, y_std, scale, calibration, baseline_scale, baseline_calibration, metadata):
        self.network = network
        self.x_mean, self.x_std, self.y_mean, self.y_std = x_mean, x_std, y_mean, y_std
        self.scale, self.calibration = scale, calibration
        self.baseline_scale, self.baseline_calibration = baseline_scale, baseline_calibration
        self.metadata = metadata

    @classmethod
    def train(cls, epochs=60, seed=7, progress=None):
        train_seeds = list(range(10, 18))
        calibration_seeds = list(range(50, 54))
        validation_seeds = [40, 41]
        training = [features(simulate(Scenario(seed=s, traffic=.6 + .2 * (i % 7)))) for i, s in enumerate(train_seeds)]
        x, y = (np.concatenate([pair[j] for pair in training]) for j in (0, 1))
        x_mean, y_mean = x.mean(axis=0), y.mean(axis=0)
        x_std, y_std = np.maximum(x.std(axis=0), 1e-6), np.maximum(y.std(axis=0), 1e-6)
        validation = [features(simulate(Scenario(seed=s, traffic=1.1))) for s in validation_seeds]
        vx, vy = (np.concatenate([pair[j] for pair in validation]) for j in (0, 1))
        network = MLP(x.shape[1], seed=seed)
        curve = network.fit((x - x_mean) / x_std, (y - y_mean) / y_std, epochs=epochs, progress=progress,
                            validation=((vx - x_mean) / x_std, (vy - y_mean) / y_std))
        residuals, baselines = [], []
        for i, s in enumerate(calibration_seeds):
            telemetry = simulate(Scenario(seed=s, traffic=.7 + .35*i))
            cx, cy = features(telemetry)
            predicted = network.predict(np.clip((cx - x_mean) / x_std, -5, 5)) * y_std + y_mean
            residuals.append((cy - predicted).reshape(-1, 8, 3))
            baselines.append(cy.reshape(-1, 8, 3) - ewma_prediction(telemetry))
        residuals, baselines = np.concatenate(residuals), np.concatenate(baselines)
        floor = np.array([.35, .5, .01])
        scale = np.maximum(np.sqrt(np.mean(residuals**2, axis=0)), floor)
        baseline_scale = np.maximum(np.sqrt(np.mean(baselines**2, axis=0)), floor)
        calibration = np.sort(np.maximum(residuals / scale, 0).max(axis=2), axis=0)
        baseline_calibration = np.sort(np.maximum(baselines / baseline_scale, 0).max(axis=2), axis=0)
        metadata = {
            "name": "Graph residual forecaster", "version": "grf-1", "seed": seed, "epochs": epochs,
            "architecture": [x.shape[1], 32, 3], "parameter_count": sum(p.size for p in network.params.values()),
            "train_seeds": train_seeds, "validation_seeds": validation_seeds, "calibration_seeds": calibration_seeds,
            "training_samples": len(x), "calibration_samples": len(calibration)*8,
            "data_fingerprint": hashlib.sha256(x.tobytes() + y.tobytes()).hexdigest(),
            "curve": curve, "created_at": datetime.now(timezone.utc).isoformat(),
            "calibration": "Per-service 99.5th percentile of maximum positive standardized residual; 3 consecutive exceedances",
            "limits": "Synthetic data, known graph, fixed propagation. Tail evidence is not a causal probability or guaranteed coverage.",
            "workload_support": {"request_min": [float(x[x[:,-8+i]==1,12].min()) for i in range(8)],
                "request_max": [float(x[x[:,-8+i]==1,12].max()) for i in range(8)],
                "tolerance": .02, "max_outside_fraction": .01},
        }
        return cls(network, x_mean, x_std, y_mean, y_std, scale, calibration, baseline_scale, baseline_calibration, metadata)

    def support(self, telemetry: Telemetry) -> dict:
        support = self.metadata.get("workload_support")
        if support is None:
            return {"status":"unknown","outside_fraction":None,
                "message":"This model has no workload support metadata. Retrain before interpreting an origin diagnosis."}
        requests = telemetry.requests[HISTORY:]
        low = np.array(support["request_min"])*(1-support["tolerance"])
        high = np.array(support["request_max"])*(1+support["tolerance"])
        fraction = float(((requests<low)|(requests>high)).mean())
        outside = fraction > support["max_outside_fraction"]
        return {"status":"outside-support" if outside else "within-support","outside_fraction":fraction,
            "message":"Workload is outside this model's training support. Residuals are visible, but origin diagnosis is withheld." if outside
                else "Request rates fall within recorded training support; this does not establish real-system validity."}

    def score(self, telemetry: Telemetry, baseline=False) -> dict:
        x, y = features(telemetry)
        if baseline:
            predicted = ewma_prediction(telemetry)
            scale, calibration = self.baseline_scale, self.baseline_calibration
        else:
            predicted = (self.network.predict(np.clip((x-self.x_mean)/self.x_std, -5, 5))*self.y_std+self.y_mean).reshape(-1,8,3)
            scale, calibration = self.scale, self.calibration
        residuals = y.reshape(-1, 8, 3) - predicted
        raw = np.maximum(residuals / scale, 0).max(axis=2)
        thresholds = np.maximum(np.quantile(calibration, .995, axis=0), .1)
        score = raw / thresholds
        tail = np.empty_like(raw)
        for service in range(8):
            tail[:, service] = (1 + len(calibration) - np.searchsorted(calibration[:, service], raw[:, service], side="left")) / (len(calibration) + 1)
        # Warmup has no valid model evidence. It is displayed as zero, not scored.
        scores = np.pad(score, ((HISTORY,0),(0,0)))
        tails = np.pad(tail, ((HISTORY,0),(0,0)), constant_values=1)
        return {"scores": scores, "tail": tails, "residuals": residuals,
                "prediction": predicted, "thresholds": thresholds}

    def save(self, path: Path):
        with Path(path).open("wb") as handle:
            np.savez_compressed(handle, **self.network.params, x_mean=self.x_mean, x_std=self.x_std,
                y_mean=self.y_mean, y_std=self.y_std, scale=self.scale, calibration=self.calibration,
                baseline_scale=self.baseline_scale, baseline_calibration=self.baseline_calibration,
                metadata=np.array(json.dumps(self.metadata)))

    @classmethod
    def load(cls, path: Path):
        with np.load(path, allow_pickle=False) as stored:
            metadata = json.loads(str(stored["metadata"]))
            net = MLP(metadata["architecture"][0], metadata["architecture"][1], metadata["seed"])
            for key in net.params:
                values = stored[key].copy()
                if values.shape != net.params[key].shape or not np.isfinite(values).all():
                    raise ValueError("Invalid model parameters")
                net.params[key] = values
            arrays = [stored[key].copy() for key in ["x_mean", "x_std", "y_mean", "y_std", "scale", "calibration", "baseline_scale", "baseline_calibration"]]
            if any(not np.isfinite(a).all() for a in arrays):
                raise ValueError("Invalid model calibration")
            return cls(net, *arrays, metadata)
