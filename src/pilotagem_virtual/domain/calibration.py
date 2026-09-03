from __future__ import annotations

import math
from dataclasses import dataclass, replace
from statistics import median


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
    deadzone: float = 0.0

    def __post_init__(self):
        if self.axis < 0 or not all(math.isfinite(v) for v in (self.released, self.pressed, self.comfortable_max, self.deadzone)):
            raise ValueError("Perfil do pedal inválido")
        if not (-1 <= self.released <= 1 and -1 <= self.pressed <= 1) or abs(self.pressed - self.released) < .1:
            raise ValueError("Curso do pedal insuficiente")
        if not 0 <= self.deadzone < self.comfortable_max <= 1:
            raise ValueError("Máximo de treino deve superar a deadzone")

    def normalize(self, raw: float) -> float:
        span = self.pressed - self.released
        if abs(span) < 1e-9:
            return 0.0
        physical = clamp((float(raw) - self.released) / span, 0.0, 1.0)
        return clamp((physical - self.deadzone) / (self.comfortable_max - self.deadzone), 0.0, 1.0)


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
            if not 0 <= index < len(axes) or not math.isfinite(axes[index]):
                raise ValueError("Eixo ausente ou inválido")
            return float(axes[index])

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


def calibrate_brake(profile, rest, applications, maximum=1.0):
    if len(rest) < 60 or len(applications) < 60:
        raise ValueError("Leituras insuficientes; repita a etapa")
    if not all(math.isfinite(v) and -1 <= v <= 1 for v in (*rest, *applications)):
        raise ValueError("Leitura inválida na calibração")
    released = median(rest)
    pressed = max(applications, key=lambda v: abs(v - released))
    span = abs(pressed - released)
    if span < .1:
        raise ValueError("Movimente o pedal para registrar seu curso")
    deadzone = max(abs(v - released) for v in rest) / span + .005
    if deadzone > .15:
        raise ValueError("Repouso instável; solte o pedal e repita")
    return replace(profile, brake=PedalCalibration(profile.brake.axis, released, pressed, maximum, deadzone), source="personalized-v1")


def profile_from_dict(data):
    return CalibrationProfile(
        data["device_name"], data["device_guid"], SteeringCalibration(**data["steering"]),
        PedalCalibration(**data["accelerator"]), PedalCalibration(**data["brake"]),
        PedalCalibration(**data["clutch"]) if data.get("clutch") else None, data["source"],
    )
