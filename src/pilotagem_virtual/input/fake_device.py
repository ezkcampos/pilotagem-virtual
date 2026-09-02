from __future__ import annotations

from collections.abc import Iterable

from pilotagem_virtual.input.device import DeviceInfo, RawInputState


class FakeInputDevice:
    def __init__(self, states: Iterable[RawInputState]) -> None:
        self._states = iter(states)
        self._last = RawInputState(0, (0.0, 1.0, 1.0, 1.0), (), ())
        self._info = DeviceInfo("fake-g29", "Fake G29", "fake", 4, 0, 0)

    @property
    def info(self) -> DeviceInfo:
        return self._info

    def poll(self) -> RawInputState:
        self._last = next(self._states, self._last)
        return self._last
