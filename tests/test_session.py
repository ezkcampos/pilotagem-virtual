from __future__ import annotations

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
