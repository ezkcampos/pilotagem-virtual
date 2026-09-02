from __future__ import annotations

from dataclasses import dataclass


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


@dataclass(frozen=True)
class SteeringCalibration:
    axis: int
    minimum: float
    center: float
    maximum: float
    deadzone: float = 0.02

    def normalize(self, raw: float) -> float:
        raw = clamp(raw, self.minimum, self.maximum)
        if raw < self.center:
            span = max(1e-9, self.center - self.minimum)
            value = (raw - self.center) / span
        else:
            span = max(1e-9, self.maximum - self.center)
            value = (raw - self.center) / span

        value = clamp(value, -1.0, 1.0)
        deadzone = clamp(self.deadzone, 0.0, 0.95)
        if abs(value) <= deadzone:
            return 0.0
        magnitude = (abs(value) - deadzone) / (1.0 - deadzone)
        return clamp((-1.0 if value < 0 else 1.0) * magnitude, -1.0, 1.0)


@dataclass(frozen=True)
class PedalCalibration:
    axis: int
    released: float
    pressed: float
    comfortable_max: float = 1.0

    def normalize(self, raw: float) -> float:
        span = self.pressed - self.released
        if abs(span) < 1e-9:
            return 0.0
        physical = clamp((float(raw) - self.released) / span, 0.0, 1.0)
        comfortable_max = clamp(self.comfortable_max, 0.05, 1.0)
        return clamp(physical / comfortable_max, 0.0, 1.0)


@dataclass(frozen=True)
class NormalizedControls:
    steering: float = 0.0
    accelerator: float = 0.0
    brake: float = 0.0
    clutch: float = 0.0


@dataclass(frozen=True)
class CalibrationProfile:
    device_name: str
    device_guid: str
    steering: SteeringCalibration
    accelerator: PedalCalibration
    brake: PedalCalibration
    clutch: PedalCalibration | None = None
    source: str = "manual"

    def normalize(self, axes: list[float] | tuple[float, ...]) -> NormalizedControls:
        def raw(index: int) -> float:
            return float(axes[index]) if 0 <= index < len(axes) else 0.0

        return NormalizedControls(
            steering=self.steering.normalize(raw(self.steering.axis)),
            accelerator=self.accelerator.normalize(raw(self.accelerator.axis)),
            brake=self.brake.normalize(raw(self.brake.axis)),
            clutch=(
                self.clutch.normalize(raw(self.clutch.axis))
                if self.clutch is not None
                else 0.0
            ),
        )


def observed_g29_profile(device_name: str, device_guid: str) -> CalibrationProfile:
    """Profile measured from the September 2026 G29 hardware capture."""

    released = 0.99996948
    return CalibrationProfile(
        device_name=device_name,
        device_guid=device_guid,
        steering=SteeringCalibration(
            axis=0,
            minimum=-1.0,
            center=0.0,
            maximum=0.99996948,
            deadzone=0.02,
        ),
        accelerator=PedalCalibration(axis=1, released=released, pressed=-1.0),
        brake=PedalCalibration(axis=2, released=released, pressed=-1.0),
        clutch=PedalCalibration(axis=3, released=released, pressed=-1.0),
        source="observed-g29-spike-2026-09-02",
    )
