from __future__ import annotations

from collections.abc import Iterable

from pilotagem_virtual.input.device import DeviceInfo, RawInputState


class FakeInputDevice:
    def __init__(self, states: Iterable[RawInputState]) -> None:
        self._states = iter(states)
        self._info = DeviceInfo("fake-g29", "Fake G29", "fake", 4, 0, 0)

    @property
    def info(self) -> DeviceInfo:
        return self._info

    def poll(self) -> RawInputState:
        # Exhaustion is explicit: replay must never manufacture fresh readings.
        return next(self._states)


class FakeInputBackend:
    def __init__(self, device: FakeInputDevice) -> None:
        self.device = device
        self.closed = False

    def list_devices(self) -> list[DeviceInfo]:
        return [] if self.closed else [self.device.info]

    def open_device(self, device_id: str) -> FakeInputDevice:
        if self.closed or device_id != self.device.info.device_id:
            raise LookupError("Dispositivo falso indisponível")
        return self.device

    def close(self) -> None:
        self.closed = True
