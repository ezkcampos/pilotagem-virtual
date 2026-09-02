from __future__ import annotations

import pytest

from pilotagem_virtual.g29_axes import (
    G29_AXIS_DESCRIPTORS,
    is_observed_g29_profile,
    normalize_g29_axis,
    normalize_inverted_pedal,
    normalize_steering,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(1.0, 0.0), (0.0, 0.5), (-1.0, 1.0), (2.0, 0.0), (-2.0, 1.0)],
)
def test_inverted_pedal_normalization(raw: float, expected: float) -> None:
    assert normalize_inverted_pedal(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(-1.0, -1.0), (0.0, 0.0), (1.0, 1.0), (-2.0, -1.0), (2.0, 1.0)],
)
def test_steering_normalization(raw: float, expected: float) -> None:
    assert normalize_steering(raw) == expected


def test_observed_g29_axis_mapping() -> None:
    assert G29_AXIS_DESCRIPTORS[0].name == "Volante"
    assert G29_AXIS_DESCRIPTORS[1].name == "Acelerador"
    assert G29_AXIS_DESCRIPTORS[2].name == "Freio"
    assert G29_AXIS_DESCRIPTORS[3].name == "Embreagem"
    assert normalize_g29_axis(2, 0.99996948) == pytest.approx(0.00001526)
    assert normalize_g29_axis(2, -1.0) == 1.0


def test_profile_only_applies_to_observed_four_axis_g29() -> None:
    name = "Logitech G HUB G29 Driving Force Racing Wheel USB"
    assert is_observed_g29_profile(name, 4)
    assert not is_observed_g29_profile(name, 3)
    assert not is_observed_g29_profile("Generic USB Wheel", 4)
