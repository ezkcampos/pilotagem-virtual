"""Read readiness from pygame's already-loaded SDL2 on Windows.

pygame exposes axis values but not SDL_JoystickGetAxisInitialState. Query the
same SDL module through its public C API; never load a second SDL runtime.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import pygame


class SdlJoystickState:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("A verificação de estado inicial do G29 requer Windows")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        kernel.GetModuleHandleW.restype = ctypes.c_void_p
        candidates = {Path(pygame.__file__).resolve().parent / "SDL2.dll"}
        if hasattr(sys, "_MEIPASS"):
            candidates.add(Path(sys._MEIPASS) / "SDL2.dll")
        handles = {
            handle for path in candidates
            if (handle := kernel.GetModuleHandleW(str(path)))
        }
        if len(handles) != 1:
            raise RuntimeError("Não foi possível identificar uma única SDL2 carregada pelo pygame")
        self.library = ctypes.CDLL("SDL2.dll", handle=handles.pop())
        self._from_instance = self.library.SDL_JoystickFromInstanceID
        self._from_instance.argtypes = [ctypes.c_int32]
        self._from_instance.restype = ctypes.c_void_p
        self._initial = self.library.SDL_JoystickGetAxisInitialState
        self._initial.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int16)]
        self._initial.restype = ctypes.c_int
        self._attached = self.library.SDL_JoystickGetAttached
        self._attached.argtypes = [ctypes.c_void_p]
        self._attached.restype = ctypes.c_int

    def read(self, instance_id: int, axis_count: int) -> tuple[bool, tuple[bool, ...]]:
        # Resolve on every poll; no native pointer survives a close/reconnect.
        joystick = self._from_instance(instance_id)
        if not joystick or not self._attached(joystick):
            return False, ()
        return True, tuple(bool(self._initial(joystick, axis, None)) for axis in range(axis_count))
