from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DeviceInfo:
    device_id: str
    name: str
    guid: str
    axis_count: int
    button_count: int
    hat_count: int


@dataclass(frozen=True)
class RawInputState:
    timestamp_ns: int
    axes: tuple[float, ...]
    buttons: tuple[int, ...]
    hats: tuple[tuple[int, int], ...]
    connected: bool = True


class InputDevice(Protocol):
    @property
    def info(self) -> DeviceInfo: ...

    def poll(self) -> RawInputState: ...


class InputBackend(Protocol):
    def list_devices(self) -> list[DeviceInfo]: ...

    def open_device(self, device_id: str) -> InputDevice: ...
