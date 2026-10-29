import numpy as np
import pytest
from faultline.benchmark import evaluate
from faultline.simulator import intrinsic


@pytest.mark.parametrize("fault_window_signal", [True, False])
def test_event_recall_counts_in_window_signal_despite_earlier_false_alarm(fault_window_signal):
    class ScriptedDetector:
        metadata = {"train_seeds": [], "validation_seeds": [], "calibration_seeds": []}

        def support(self, telemetry):
            return {"status": "within-support"}

        def score(self, telemetry, baseline=False):
            scores = np.zeros((240, 8))
            scores[20:23, 0] = 2  # Earlier alert must neither mask nor count as the event.
            if fault_window_signal:
                scores[85:88, 0] = 3
            return {"scores": scores, "tail": np.ones_like(scores),
                    "prediction": intrinsic(telemetry)[4:]}

    result = evaluate(ScriptedDetector(), [200])
    for method in ("neural", "ewma"):
        metrics = result["metrics"][method]
        assert metrics["detected_count"] == int(fault_window_signal)
        assert metrics["mean_detection_delay"] == (7 if fault_window_signal else None)
