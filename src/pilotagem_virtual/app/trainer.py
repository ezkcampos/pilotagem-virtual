from __future__ import annotations

import math
import time
from collections.abc import Callable

from pilotagem_virtual.domain.calibration import (
    CalibrationProfile, NormalizedControls, observed_g29_profile,
)
from pilotagem_virtual.domain.scenario import Scenario
from pilotagem_virtual.domain.session import AttemptSession
from pilotagem_virtual.g29_axes import is_observed_g29_profile
from pilotagem_virtual.input.device import DeviceInfo, InputBackend, InputDevice, RawInputState


class TrainerController:
    """Own input, profile and recorder; rendering never supplies samples.

    Called from the backend's owner thread. P0 keeps this on the main thread in
    production; only the isolated acquisition experiment may use a worker.
    """

    def __init__(
        self, scenario: Scenario, backend: InputBackend,
        clock_ns: Callable[[], int] = time.perf_counter_ns,
    ) -> None:
        self.backend = backend
        self.clock_ns = clock_ns
        self.session = AttemptSession(scenario)
        self.device: InputDevice | None = None
        self.profile: CalibrationProfile | None = None
        self.controls = NormalizedControls()
        self.available = False
        self.error: str | None = None
        self.closed = False
        self._last_timestamp_ns: int | None = None

    def refresh_devices(self) -> list[DeviceInfo]:
        self._require_idle()
        self.device = None
        self.profile = None
        self.available = False
        self.controls = NormalizedControls()
        return self.backend.list_devices()

    def select_device(self, device_id: str) -> None:
        self._require_idle()
        self.available = False
        self.profile = None
        self.controls = NormalizedControls()
        self.device = self.backend.open_device(device_id)
        self._last_timestamp_ns = None
        info = self.device.info
        if is_observed_g29_profile(info.name, info.axis_count):
            self.profile = observed_g29_profile(info.name, info.guid)
            self.available = True
            self.error = None
        else:
            self.error = "unsupported_device"

    def start(self) -> str:
        if self.closed or not self.available or self.profile is None:
            raise RuntimeError("Conecte um G29 compatível antes de iniciar")
        return self.session.start(self.clock_ns(), self.profile)

    def poll(self) -> RawInputState | None:
        if self.closed or not self.available or self.device is None or self.profile is None:
            return None
        try:
            raw = self.device.poll()
        except StopIteration:
            self._fail("input_exhausted")
            return None
        if not raw.connected:
            self._fail("device_disconnected")
            return raw
        if self._last_timestamp_ns is not None and raw.timestamp_ns <= self._last_timestamp_ns:
            self._fail("non_monotonic_timestamp")
            return raw
        self._last_timestamp_ns = raw.timestamp_ns
        axes = [self.profile.steering.axis, self.profile.accelerator.axis, self.profile.brake.axis]
        if self.profile.clutch is not None:
            axes.append(self.profile.clutch.axis)
        if any(index < 0 or index >= len(raw.axes) for index in axes) or not all(
            math.isfinite(value) for value in raw.axes
        ):
            self._fail("invalid_axes")
            return raw
        self.controls = self.profile.normalize(raw.axes)
        self.session.tick(raw.timestamp_ns, self.controls, attempt_id=self.session.attempt_id)
        return raw

    def cancel(self) -> None:
        self.session.cancel()

    def close(self) -> None:
        if self.closed:
            return
        self.session.cancel("application_closed")
        self.closed = True
        self.available = False
        self.backend.close()

    def _fail(self, reason: str) -> None:
        self.available = False
        self.error = reason
        self.controls = NormalizedControls()
        self.session.cancel(reason)

    def _require_idle(self) -> None:
        if self.closed or self.session.active:
            raise RuntimeError("Encerre a tentativa antes de trocar o dispositivo")
