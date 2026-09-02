from __future__ import annotations

import pytest

from pilotagem_virtual.domain.calibration import (
    PedalCalibration,
    SteeringCalibration,
    observed_g29_profile,
)


def test_observed_g29_profile_maps_all_axes() -> None:
    profile = observed_g29_profile("G29", "guid")
    released = profile.normalize([0.0, 0.99996948, 0.99996948, 0.99996948])
    pressed = profile.normalize([1.0, -1.0, -1.0, -1.0])

    assert released.steering == 0.0
    assert released.accelerator == pytest.approx(0.0)
    assert released.brake == pytest.approx(0.0)
    assert pressed.steering == 1.0
    assert pressed.accelerator == 1.0
    assert pressed.brake == 1.0
    assert pressed.clutch == 1.0


def test_steering_deadzone_is_removed_and_remaining_range_is_rescaled() -> None:
    calibration = SteeringCalibration(0, -1.0, 0.0, 1.0, deadzone=0.1)

    assert calibration.normalize(0.05) == 0.0
    assert calibration.normalize(-0.05) == 0.0
    assert calibration.normalize(0.55) == pytest.approx(0.5)
    assert calibration.normalize(-0.55) == pytest.approx(-0.5)


def test_comfortable_pedal_max_reaches_one_earlier() -> None:
    calibration = PedalCalibration(2, released=1.0, pressed=-1.0, comfortable_max=0.75)

    assert calibration.normalize(1.0) == 0.0
    assert calibration.normalize(-0.5) == 1.0
    assert calibration.normalize(-1.0) == 1.0
