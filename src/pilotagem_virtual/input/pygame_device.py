from __future__ import annotations

import os
import time
import threading
from collections.abc import Callable

os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

import pygame

from pilotagem_virtual.input.device import DeviceInfo, RawInputState
from pilotagem_virtual.input.sdl_state import SdlJoystickState


class PygameInputDevice:
    def __init__(
        self, joystick: pygame.joystick.JoystickType, info: DeviceInfo,
        clock_ns: Callable[[], int] = time.perf_counter_ns,
        state_reader: SdlJoystickState | None = None,
    ) -> None:
        self._joystick = joystick
        self._info = info
        self._clock_ns = clock_ns
        self._owner = threading.get_ident()
        self._connected = True
        self._state_reader = state_reader or SdlJoystickState()

    @property
    def info(self) -> DeviceInfo:
        return self._info

    def poll(self) -> RawInputState:
        if threading.get_ident() != self._owner:
            raise RuntimeError("Leitura SDL fora da thread proprietária")
        if not self._connected:
            return RawInputState(self._clock_ns(), (), (), (), connected=False)
        try:
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEREMOVED and event.instance_id == self.info.instance_id:
                    self._connected = False
                    return RawInputState(self._clock_ns(), (), (), (), connected=False)
            axes = tuple(
                self._joystick.get_axis(index)
                for index in range(self._joystick.get_numaxes())
            )
            buttons = tuple(
                int(bool(self._joystick.get_button(index)))
                for index in range(self._joystick.get_numbuttons())
            )
            hats = tuple(
                tuple(self._joystick.get_hat(index))
                for index in range(self._joystick.get_numhats())
            )
            connected, initialized = self._state_reader.read(self.info.instance_id, len(axes))
            if not connected:
                self._connected = False
                return RawInputState(self._clock_ns(), (), (), (), connected=False)
        except pygame.error:
            self._connected = False
            return RawInputState(self._clock_ns(), (), (), (), connected=False)
        return RawInputState(self._clock_ns(), axes, buttons, hats, initialized_axes=initialized)


class PygameInputBackend:
    def __init__(self, clock_ns: Callable[[], int] = time.perf_counter_ns) -> None:
        self._owner = threading.get_ident()
        self._clock_ns = clock_ns
        self._closed = False
        pygame.init()
        pygame.joystick.init()
        try:
            self._state_reader = SdlJoystickState()
        except Exception:
            pygame.quit()
            raise
        self._devices: dict[str, tuple[pygame.joystick.JoystickType, DeviceInfo]] = {}

    def list_devices(self) -> list[DeviceInfo]:
        self._check_owner()
        if self._closed:
            raise RuntimeError("Backend SDL encerrado")
        for joystick, _ in self._devices.values():
            joystick.quit()
        self._devices.clear()
        pygame.event.get()
        for index in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(index)
            joystick.init()
            guid = self._safe_guid(joystick)
            instance_id = joystick.get_instance_id()
            device_id = f"{guid}:{instance_id}"
            info = DeviceInfo(
                device_id=device_id,
                name=joystick.get_name(),
                guid=guid,
                axis_count=joystick.get_numaxes(),
                button_count=joystick.get_numbuttons(),
                hat_count=joystick.get_numhats(),
                instance_id=instance_id,
            )
            self._devices[device_id] = (joystick, info)
        return [item[1] for item in self._devices.values()]

    def open_device(self, device_id: str) -> PygameInputDevice:
        self._check_owner()
        try:
            joystick, info = self._devices[device_id]
        except KeyError as error:
            raise LookupError(f"Dispositivo não encontrado: {device_id}") from error
        return PygameInputDevice(joystick, info, self._clock_ns, self._state_reader)

    def close(self) -> None:
        self._check_owner()
        if self._closed:
            return
        self._closed = True
        self._devices.clear()
        pygame.joystick.quit()
        pygame.quit()

    def _check_owner(self) -> None:
        if threading.get_ident() != self._owner:
            raise RuntimeError("Backend SDL fora da thread proprietária")

    @staticmethod
    def _safe_guid(joystick: pygame.joystick.JoystickType) -> str:
        try:
            return joystick.get_guid()
        except (AttributeError, pygame.error):
            return "unavailable"
