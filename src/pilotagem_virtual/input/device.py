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
    instance_id: int | None = None


@dataclass(frozen=True)
class RawInputState:
    timestamp_ns: int
    axes: tuple[float, ...]
    buttons: tuple[int, ...]
    hats: tuple[tuple[int, int], ...]
    connected: bool = True
    # None is used by trusted replay/synthetic sources. SDL supplies one flag
    # per axis, independently of its numerical value (zero may be legitimate).
    initialized_axes: tuple[bool, ...] | None = None

    @property
    def ready(self) -> bool:
        return self.connected and (
            self.initialized_axes is None or (
                len(self.initialized_axes) == len(self.axes) and all(self.initialized_axes)
            )
        )


class InputDevice(Protocol):
    @property
    def info(self) -> DeviceInfo: ...

    def poll(self) -> RawInputState: ...


class InputBackend(Protocol):
    def list_devices(self) -> list[DeviceInfo]: ...

    def open_device(self, device_id: str) -> InputDevice: ...

    def close(self) -> None: ...
