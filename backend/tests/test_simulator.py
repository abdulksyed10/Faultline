import numpy as np
import pytest
from pydantic import ValidationError

from faultline.schemas import Scenario, Fault, Repair
from faultline.simulator import simulate, intrinsic
from faultline.topology import SERVICE_IDS


def incident(**kwargs):
    return Scenario(fault=Fault(service="database", kind="latency", start=60, duration=60), **kwargs)


def test_seeded_simulation_is_finite_and_reproducible():
    a, b = simulate(incident()), simulate(incident())
    np.testing.assert_array_equal(a.values, b.values)
    assert a.values.shape == (240, 8, 3)
    assert np.isfinite(a.values).all()
    assert (a.values >= 0).all()
    assert (a.values[:, :, 1] <= 100).all()


def test_fault_propagates_to_callers_but_not_unrelated_services():
    healthy, faulty = simulate(Scenario()), simulate(incident())
    delta = faulty.values - healthy.values
    assert delta[80, SERVICE_IDS.index("gateway"), 0] > 20
    assert delta[80, SERVICE_IDS.index("database"), 0] > 50
    np.testing.assert_array_equal(delta[:, SERVICE_IDS.index("cache")], 0)
    local = intrinsic(faulty) - intrinsic(healthy)
    assert abs(local[80, SERVICE_IDS.index("gateway"), 0]) < 1e-8


def test_same_seed_repair_only_removes_selected_fault_after_repair_time():
    scenario = incident()
    original = simulate(scenario)
    unrelated = simulate(scenario, Repair(service="cache", at=90))
    repaired = simulate(scenario, Repair(service="database", at=90))
    healthy = simulate(Scenario())
    np.testing.assert_array_equal(original.values, unrelated.values)
    np.testing.assert_array_equal(original.values[:90], repaired.values[:90])
    np.testing.assert_allclose(healthy.values[90:], repaired.values[90:])


@pytest.mark.parametrize("kwargs", [{"steps": 5}, {"seed": -1}, {"traffic": float("nan")}, {"traffic": 5}])
def test_scenario_rejects_invalid_domains(kwargs):
    with pytest.raises(ValidationError):
        Scenario(**kwargs)


def test_fault_window_and_unknown_service_rejected():
    with pytest.raises(ValidationError):
        Scenario(steps=120, fault=Fault(service="database", start=100, duration=50))
    with pytest.raises(ValidationError):
        Fault(service="unknown")


def test_all_fault_types_and_healthy_repair_are_valid():
    for kind in ("latency", "saturation", "errors"):
        output = simulate(Scenario(fault=Fault(kind=kind)))
        assert np.isfinite(output.values).all()
    healthy = Scenario()
    np.testing.assert_array_equal(simulate(healthy).values, simulate(healthy, Repair(service="database", at=40)).values)
