from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from pilotagem_virtual.domain.calibration import CalibrationProfile, NormalizedControls
from pilotagem_virtual.domain.scenario import Scenario


class SessionState(str, Enum):
    PREVIEW = "preview"
    COUNTDOWN = "countdown"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class AttemptSample:
    elapsed_ns: int
    progress: float
    controls: NormalizedControls


@dataclass(frozen=True)
class AttemptSnapshot:
    attempt_id: str
    scenario: Scenario
    profile: CalibrationProfile | None
    origin_ns: int
    state: SessionState
    reason: str | None
    samples: tuple[AttemptSample, ...]
    boundary_before: AttemptSample | None
    boundary_after: AttemptSample | None


@dataclass
class AttemptSession:
    scenario: Scenario
    countdown_seconds: float = 3.0
    state: SessionState = field(default=SessionState.PREVIEW, init=False)
    attempt_id: str = field(default="", init=False)
    reason: str | None = field(default=None, init=False)
    _samples: list[AttemptSample] = field(default_factory=list, init=False)
    _started_ns: int | None = field(default=None, init=False)
    _last_timestamp_ns: int | None = field(default=None, init=False)
    _profile: CalibrationProfile | None = field(default=None, init=False)
    _snapshot: AttemptSnapshot | None = field(default=None, init=False)
    _before: AttemptSample | None = field(default=None, init=False)
    _after: AttemptSample | None = field(default=None, init=False)
    _progress: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.countdown_seconds) or self.countdown_seconds < 0:
            raise ValueError("Contagem regressiva inválida")
        if not math.isfinite(self.scenario.duration_seconds) or self.scenario.duration_seconds <= 0:
            raise ValueError("Duração inválida")

    @property
    def samples(self) -> tuple[AttemptSample, ...]:
        return tuple(self._samples)

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    @property
    def active(self) -> bool:
        return self.state in {SessionState.COUNTDOWN, SessionState.RUNNING}

    @property
    def origin_ns(self) -> int | None:
        if self._started_ns is None:
            return None
        return self._started_ns + round(self.countdown_seconds * 1_000_000_000)

    @property
    def duration_ns(self) -> int:
        return round(self.scenario.duration_seconds * 1_000_000_000)

    @property
    def progress(self) -> float:
        return self._progress

    def start(self, now_ns: int, profile: CalibrationProfile | None = None) -> str:
        if self.active:
            raise RuntimeError("Tentativa já está em andamento")
        self.reset()
        self.attempt_id = uuid4().hex
        self._started_ns = int(now_ns)
        self._profile = profile
        self.state = SessionState.COUNTDOWN
        return self.attempt_id

    def cancel(self, reason: str = "user_cancelled") -> None:
        if self.active:
            self.reason = reason
            self.state = SessionState.CANCELLED
            self._freeze()

    def reset(self) -> None:
        if self.active:
            raise RuntimeError("Cancele a tentativa antes de limpar")
        self._samples.clear()
        self._started_ns = None
        self._last_timestamp_ns = None
        self._profile = None
        self._snapshot = None
        self._before = self._after = None
        self.reason = None
        self.attempt_id = ""
        self._progress = 0.0
        self.state = SessionState.PREVIEW

    def tick(
        self, now_ns: int, controls: NormalizedControls, *, attempt_id: str | None = None
    ) -> float:
        if not self.active or (attempt_id is not None and attempt_id != self.attempt_id):
            return self._progress
        assert self.origin_ns is not None and self._started_ns is not None
        now_ns = int(now_ns)
        if now_ns < self._started_ns:
            return self._progress
        if self._last_timestamp_ns is not None and now_ns <= self._last_timestamp_ns:
            self.cancel("non_monotonic_timestamp")
            return self._progress
        values = (controls.steering, controls.accelerator, controls.brake, controls.clutch)
        if not all(math.isfinite(v) for v in values) or not (
            -1 <= values[0] <= 1 and all(0 <= v <= 1 for v in values[1:])
        ):
            self.cancel("invalid_controls")
            return self._progress
        self._last_timestamp_ns = now_ns
        elapsed = now_ns - self.origin_ns
        sample = AttemptSample(elapsed, min(1.0, max(0.0, elapsed / self.duration_ns)), controls)
        if elapsed < 0:
            self._before = sample
            return 0.0
        self._progress = sample.progress
        if elapsed >= self.duration_ns:
            # The end reading is context, never a synthetic sample at duration.
            self._after = sample
            self.state = SessionState.COMPLETED
            self._freeze()
        else:
            self.state = SessionState.RUNNING
            self._samples.append(sample)
        return self._progress

    def snapshot(self) -> AttemptSnapshot:
        if self._snapshot is None:
            raise RuntimeError("A tentativa ainda não foi encerrada")
        return self._snapshot

    def _freeze(self) -> None:
        assert self.origin_ns is not None
        self._snapshot = AttemptSnapshot(
            self.attempt_id, self.scenario, self._profile, self.origin_ns,
            self.state, self.reason, tuple(self._samples), self._before, self._after,
        )

    def countdown_value(self, now_ns: int) -> int:
        if self.origin_ns is None or self.state != SessionState.COUNTDOWN:
            return 0
        return max(1, math.ceil((self.origin_ns - int(now_ns)) / 1_000_000_000))
