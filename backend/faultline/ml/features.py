import numpy as np
from ..simulator import Telemetry, intrinsic

HISTORY = 4


def features(telemetry: Telemetry) -> tuple[np.ndarray, np.ndarray]:
    """Rows in time-major/service-major order; no fault metadata is read."""
    local = intrinsic(telemetry)
    steps = len(local)
    if steps <= HISTORY:
        raise ValueError("At least five telemetry steps are required")
    history = np.concatenate([local[HISTORY - lag:steps - lag] for lag in range(1, HISTORY + 1)], axis=2)
    t = np.arange(HISTORY, steps)
    phase = np.broadcast_to(np.stack([np.sin(t / 23), np.cos(t / 23)], axis=1)[:, None, :], (steps - HISTORY, 8, 2))
    identity = np.broadcast_to(np.eye(8)[None], (steps - HISTORY, 8, 8))
    x = np.concatenate([history, telemetry.requests[HISTORY:, :, None], phase, identity], axis=2)
    return x.reshape(-1, x.shape[-1]), local[HISTORY:].reshape(-1, 3)


def ewma_prediction(telemetry: Telemetry) -> np.ndarray:
    local = intrinsic(telemetry)
    prediction = np.empty_like(local)
    state = local[0].copy()
    for i in range(len(local)):
        prediction[i] = state
        state = .35 * local[i] + .65 * state
    return prediction[HISTORY:]
