"""Structural synthetic telemetry, not a packet/network emulator.

Noise is generated before interventions. Same seed => same exogenous world.
Metric axis: response latency (ms), CPU (%), additive error signal (%).
"""
from dataclasses import dataclass
import numpy as np
from .schemas import Scenario, Repair
from .topology import SERVICE_IDS, WEIGHTS

BASE_LATENCY = np.array([8., 18., 12., 22., 15., 17., 3., 25.])
LOAD_SHARES = np.array([1., .62, .8, .5, .65, .4, .7, .85])


@dataclass
class Telemetry:
    values: np.ndarray
    requests: np.ndarray
    scenario: Scenario

    def __post_init__(self):
        if self.values.ndim != 3 or self.values.shape[1:] != (8, 3):
            raise ValueError("Telemetry must have shape [steps,8,3]")
        if self.requests.shape != self.values.shape[:2] or not np.isfinite(self.values).all() or not np.isfinite(self.requests).all():
            raise ValueError("Telemetry must have finite aligned values and requests")


def simulate(scenario: Scenario, repair: Repair | None = None) -> Telemetry:
    if repair and repair.at >= scenario.steps:
        raise ValueError("Repair time must be inside the experiment")
    rng = np.random.default_rng(scenario.seed)
    t = np.arange(scenario.steps)
    wave = 1 + .18 * np.sin(t / 23) + .08 * np.sin(t / 7)
    global_load = scenario.traffic * wave
    requests = 350 * global_load[:, None] * LOAD_SHARES + rng.normal(0, 2, (scenario.steps, 8))
    noise = rng.normal(size=(scenario.steps, 8, 3))
    load = requests / (350 * LOAD_SHARES)
    local = np.empty_like(noise)
    local[:, :, 0] = BASE_LATENCY * (1 + .3 * load + .16 * load**2) + .5 * noise[:, :, 0]
    local[:, :, 1] = 12 + 23 * load + 2.2 * load**2 + .7 * noise[:, :, 1]
    local[:, :, 2] = .08 + .055 * load**2 + .012 * noise[:, :, 2]
    fault = scenario.fault
    if fault:
        idx = SERVICE_IDS.index(fault.service)
        active = (t >= fault.start) & (t < fault.start + fault.duration)
        if repair and repair.service == fault.service:
            active &= t < repair.at
        envelope = active.astype(float) * fault.severity
        if fault.kind == "latency":
            local[:, idx, 0] += 110 * envelope
        elif fault.kind == "saturation":
            local[:, idx, 0] += 85 * envelope
            local[:, idx, 1] += 38 * envelope
        else:
            local[:, idx, 2] += 9 * envelope
            local[:, idx, 0] += 20 * envelope
    local[:, :, 0] = np.maximum(local[:, :, 0], .1)
    local[:, :, 1] = np.clip(local[:, :, 1], 0, 100)
    local[:, :, 2] = np.maximum(local[:, :, 2], 0)
    observed = local.copy()
    for caller in reversed(range(8)):
        observed[:, caller, 0] += observed[:, :, 0] @ WEIGHTS[caller]
        observed[:, caller, 2] += .35 * (observed[:, :, 2] @ WEIGHTS[caller])
    return Telemetry(observed, requests, scenario)


def intrinsic(telemetry: Telemetry) -> np.ndarray:
    """Known structural inversion. No access to injection metadata."""
    values = telemetry.values
    result = values.copy()
    result[:, :, 0] -= values[:, :, 0] @ WEIGHTS.T
    result[:, :, 2] -= .35 * (values[:, :, 2] @ WEIGHTS.T)
    return result
