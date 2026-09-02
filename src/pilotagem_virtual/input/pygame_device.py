from __future__ import annotations

import os
import time

os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

import pygame

from pilotagem_virtual.input.device import DeviceInfo, RawInputState


class PygameInputDevice:
    def __init__(self, joystick: pygame.joystick.JoystickType, info: DeviceInfo) -> None:
        self._joystick = joystick
        self._info = info

    @property
    def info(self) -> DeviceInfo:
        return self._info

    def poll(self) -> RawInputState:
        pygame.event.pump()
        try:
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
        except pygame.error:
            return RawInputState(time.perf_counter_ns(), (), (), (), connected=False)
        return RawInputState(time.perf_counter_ns(), axes, buttons, hats)


class PygameInputBackend:
    def __init__(self) -> None:
        pygame.init()
        pygame.joystick.init()
        self._devices: dict[str, tuple[pygame.joystick.JoystickType, DeviceInfo]] = {}

    def list_devices(self) -> list[DeviceInfo]:
        self._devices.clear()
        pygame.event.pump()
        for index in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(index)
            joystick.init()
            guid = self._safe_guid(joystick)
            device_id = f"{guid}:{index}"
            info = DeviceInfo(
                device_id=device_id,
                name=joystick.get_name(),
                guid=guid,
                axis_count=joystick.get_numaxes(),
                button_count=joystick.get_numbuttons(),
                hat_count=joystick.get_numhats(),
            )
            self._devices[device_id] = (joystick, info)
        return [item[1] for item in self._devices.values()]

    def open_device(self, device_id: str) -> PygameInputDevice:
        try:
            joystick, info = self._devices[device_id]
        except KeyError as error:
            raise LookupError(f"Dispositivo não encontrado: {device_id}") from error
        return PygameInputDevice(joystick, info)

    def close(self) -> None:
        pygame.joystick.quit()
        pygame.quit()

    @staticmethod
    def _safe_guid(joystick: pygame.joystick.JoystickType) -> str:
        try:
            return joystick.get_guid()
        except (AttributeError, pygame.error):
            return "unavailable"
