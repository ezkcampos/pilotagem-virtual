from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from pilotagem_virtual.domain.calibration import NormalizedControls
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


@dataclass
class AttemptSession:
    scenario: Scenario
    countdown_seconds: float = 3.0
    state: SessionState = SessionState.PREVIEW
    samples: list[AttemptSample] = field(default_factory=list)
    _started_ns: int | None = None

    def start(self, now_ns: int) -> None:
        self.samples.clear()
        self._started_ns = int(now_ns)
        self.state = SessionState.COUNTDOWN

    def cancel(self) -> None:
        if self.state in {SessionState.COUNTDOWN, SessionState.RUNNING}:
            self.state = SessionState.CANCELLED

    def reset(self) -> None:
        self.samples.clear()
        self._started_ns = None
        self.state = SessionState.PREVIEW

    def tick(self, now_ns: int, controls: NormalizedControls) -> float:
        if self._started_ns is None or self.state not in {
            SessionState.COUNTDOWN,
            SessionState.RUNNING,
        }:
            return 0.0

        total_elapsed = max(0.0, (int(now_ns) - self._started_ns) / 1_000_000_000)
        if total_elapsed < self.countdown_seconds:
            self.state = SessionState.COUNTDOWN
            return 0.0

        running_elapsed = total_elapsed - self.countdown_seconds
        progress = min(1.0, running_elapsed / self.scenario.duration_seconds)
        self.state = SessionState.RUNNING
        self.samples.append(
            AttemptSample(
                elapsed_ns=round(running_elapsed * 1_000_000_000),
                progress=progress,
                controls=controls,
            )
        )
        if progress >= 1.0:
            self.state = SessionState.COMPLETED
        return progress

    def countdown_value(self, now_ns: int) -> int:
        if self._started_ns is None or self.state != SessionState.COUNTDOWN:
            return 0
        elapsed = max(0.0, (int(now_ns) - self._started_ns) / 1_000_000_000)
        return max(1, math.ceil(self.countdown_seconds - elapsed))
