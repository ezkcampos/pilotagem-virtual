from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AxisKind = Literal["steering", "pedal"]


@dataclass(frozen=True)
class AxisDescriptor:
    name: str
    kind: AxisKind


G29_AXIS_DESCRIPTORS = {
    0: AxisDescriptor("Volante", "steering"),
    1: AxisDescriptor("Acelerador", "pedal"),
    2: AxisDescriptor("Freio", "pedal"),
    3: AxisDescriptor("Embreagem", "pedal"),
}


def is_observed_g29_profile(device_name: str, axis_count: int) -> bool:
    """Return whether the device matches the four-axis G29 profile we measured."""

    return axis_count == 4 and "G29" in device_name.upper()


def clamp_raw_axis(raw_value: float) -> float:
    return max(-1.0, min(1.0, float(raw_value)))


def normalize_steering(raw_value: float) -> float:
    """Normalize steering to -1 (left), 0 (center), and +1 (right)."""

    return clamp_raw_axis(raw_value)


def normalize_inverted_pedal(raw_value: float) -> float:
    """Normalize the G29's +1 released / -1 pressed signal to 0..1."""

    return (1.0 - clamp_raw_axis(raw_value)) / 2.0


def normalize_g29_axis(index: int, raw_value: float) -> float:
    descriptor = G29_AXIS_DESCRIPTORS[index]
    if descriptor.kind == "pedal":
        return normalize_inverted_pedal(raw_value)
    return normalize_steering(raw_value)
