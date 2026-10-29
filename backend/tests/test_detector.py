import numpy as np
import pytest
from faultline.schemas import Scenario, Fault, Repair
from faultline.simulator import simulate, Telemetry
from faultline.ml.detector import Detector
from faultline.analysis import analyze, compare_repair


@pytest.fixture(scope="module")
def detector():
    return Detector.train(epochs=35)


def test_model_roundtrip_preserves_predictions_and_provenance(detector, tmp_path):
    path = tmp_path / "model.npz"
    detector.save(path)
    restored = Detector.load(path)
    telemetry = simulate(Scenario(seed=101))
    np.testing.assert_array_equal(detector.score(telemetry)["scores"], restored.score(telemetry)["scores"])
    assert set(detector.metadata["train_seeds"]).isdisjoint(detector.metadata["calibration_seeds"])
    assert len(detector.metadata["data_fingerprint"]) == 64
    assert detector.metadata["parameter_count"] > 500


@pytest.mark.parametrize("kind", ["latency", "saturation", "errors"])
def test_diagnosis_ranks_origin_above_affected_callers_without_fault_labels(detector, kind):
    source = simulate(Scenario(seed=121, fault=Fault(service="database", kind=kind)))
    # Deliberately replace scenario metadata: inference must rely on arrays only.
    unlabeled = Telemetry(source.values, source.requests, Scenario(seed=121))
    result = analyze(unlabeled, detector)
    assert result["diagnosis"]["status"] == "detected"
    assert result["diagnosis"]["ranking"][0]["service"] == "database"
    assert 80 <= result["diagnosis"]["ranking"][0]["onset"] <= 84


def test_healthy_run_is_inconclusive(detector):
    result = analyze(simulate(Scenario(seed=133)), detector)
    assert result["diagnosis"]["status"] == "inconclusive"
    assert result["diagnosis"]["root_service"] is None


def test_repair_comparison_measures_effect_and_rejects_out_of_range(detector):
    scenario = Scenario(fault=Fault(service="database"))
    correct = compare_repair(scenario, Repair(service="database", at=110), detector)
    wrong = compare_repair(scenario, Repair(service="cache", at=110), detector)
    assert correct["latency_reduction_pct"] > 20
    assert wrong["latency_reduction_pct"] == 0
    with pytest.raises(ValueError):
        compare_repair(scenario, Repair(service="database", at=240), detector)


def test_rejects_nonfinite_and_too_short_telemetry(detector):
    with pytest.raises(ValueError):
        Telemetry(np.full((240, 8, 3), np.nan), np.ones((240,8)), Scenario())
    with pytest.raises(ValueError):
        detector.score(Telemetry(np.ones((3,8,3)), np.ones((3,8)), Scenario()))


def test_unsupported_workload_abstains_instead_of_asserting_origin(detector):
    result = analyze(simulate(Scenario(seed=133, traffic=2)), detector)
    assert result["quality"]["status"] == "outside-support"
    assert result["diagnosis"]["status"] == "inconclusive"
    assert result["diagnosis"]["root_service"] is None


def test_legacy_artifact_without_support_declines_origin(detector):
    saved = detector.metadata.pop("workload_support", None)
    try:
        result = analyze(simulate(Scenario(fault=Fault())), detector)
        assert result["quality"]["status"] == "unknown"
        assert result["diagnosis"]["root_service"] is None
    finally:
        if saved is not None:
            detector.metadata["workload_support"] = saved
