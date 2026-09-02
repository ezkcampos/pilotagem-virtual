from __future__ import annotations

from dataclasses import FrozenInstanceError
import pytest

from pilotagem_virtual.domain.calibration import NormalizedControls
from pilotagem_virtual.domain.scenario import Scenario
from pilotagem_virtual.domain.session import AttemptSession, SessionState
from tests.test_scenario import scenario_payload


def test_attempt_transitions_from_countdown_to_completion() -> None:
    session = AttemptSession(Scenario.from_dict(scenario_payload()))
    controls = NormalizedControls(brake=0.8)
    start = 1_000_000_000

    session.start(start)
    assert session.state == SessionState.COUNTDOWN
    assert session.countdown_value(start) == 3

    assert session.tick(start + 2_000_000_000, controls) == 0.0
    assert session.state == SessionState.COUNTDOWN

    assert session.tick(start + 3_000_000_000, controls) == 0.0
    assert session.state == SessionState.RUNNING
    assert len(session.samples) == 1

    assert session.tick(start + 11_000_000_000, controls) == 1.0
    assert session.state == SessionState.COMPLETED
    assert session.samples[-1].controls.brake == 0.8


def test_attempt_can_be_cancelled() -> None:
    session = AttemptSession(Scenario.from_dict(scenario_payload()))
    session.start(0)
    session.cancel()
    assert session.state == SessionState.CANCELLED


def test_snapshot_preserves_real_boundary_and_survives_repetition():
    session = AttemptSession(Scenario.from_dict(scenario_payload()))
    first_id = session.start(0)
    session.tick(2_995_000_000, NormalizedControls(brake=0.1))
    session.tick(3_003_000_000, NormalizedControls(brake=0.2))
    session.tick(11_007_000_000, NormalizedControls(brake=0.3))
    result = session.snapshot()
    assert result.samples[0].elapsed_ns == 3_000_000
    assert result.boundary_before.elapsed_ns == -5_000_000
    assert result.boundary_after.elapsed_ns == 8_007_000_000
    assert len(result.samples) == 1
    with pytest.raises(FrozenInstanceError):
        result.samples[0].elapsed_ns = 0
    second_id = session.start(20_000_000_000)
    assert second_id != first_id
    session.tick(23_000_000_000, NormalizedControls(brake=1), attempt_id=first_id)
    assert not session.samples
    assert result.samples[0].controls.brake == 0.2


@pytest.mark.parametrize("last", [3_000_000_000, 2_999_999_999])
def test_repeated_or_backwards_timestamps_cancel_without_changing_data(last):
    session = AttemptSession(Scenario.from_dict(scenario_payload()))
    session.start(0)
    session.tick(3_000_000_000, NormalizedControls())
    session.tick(last, NormalizedControls(brake=0.5))
    assert session.snapshot().reason == "non_monotonic_timestamp"
    assert session.sample_count == 1


@pytest.mark.parametrize("brake", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_normalized_values_are_rejected(brake):
    session = AttemptSession(Scenario.from_dict(scenario_payload()))
    session.start(0)
    session.tick(3_000_000_000, NormalizedControls(brake=brake))
    assert session.snapshot().reason == "invalid_controls"
    assert not session.samples


def test_thirty_repetitions_have_fresh_ids_and_no_residual_samples():
    session = AttemptSession(Scenario.from_dict(scenario_payload()))
    results = []
    for repetition in range(30):
        origin = repetition * 20_000_000_000
        session.start(origin)
        for i in range(961):
            session.tick(origin + 3_000_000_000 + round(i * 1e9 / 120), NormalizedControls(brake=repetition / 30))
        results.append(session.snapshot())
    assert len({r.attempt_id for r in results}) == 30
    assert all(len(r.samples) == 960 for r in results)
    assert all(r.samples[0].controls.brake == i / 30 for i, r in enumerate(results))
