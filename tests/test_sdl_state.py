"""Exercise the real Windows ABI with SDL's virtual device, never physical input."""
import ctypes
import sys

import pytest

from pilotagem_virtual.input.pygame_device import PygameInputBackend
from pilotagem_virtual.input.sdl_state import SdlJoystickState


@pytest.mark.skipif(sys.platform != "win32", reason="Windows backend")
def test_native_readiness_uses_same_sdl_device_and_detects_removal():
    backend = PygameInputBackend()
    library = SdlJoystickState().library
    attach = library.SDL_JoystickAttachVirtual
    attach.argtypes = [ctypes.c_int] * 4
    attach.restype = ctypes.c_int
    detach = library.SDL_JoystickDetachVirtual
    detach.argtypes = [ctypes.c_int]
    detach.restype = ctypes.c_int
    instance = library.SDL_JoystickGetDeviceInstanceID
    instance.argtypes = [ctypes.c_int]
    instance.restype = ctypes.c_int32
    pointer = library.SDL_JoystickFromInstanceID
    pointer.argtypes = [ctypes.c_int32]
    pointer.restype = ctypes.c_void_p
    set_axis = library.SDL_JoystickSetVirtualAxis
    set_axis.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int16]
    set_axis.restype = ctypes.c_int
    index = attach(1, 4, 1, 0)
    assert index >= 0
    attached = True
    try:
        expected = instance(index)
        info = next(d for d in backend.list_devices() if d.instance_id == expected)
        device = backend.open_device(info.device_id)
        raw = device.poll()
        assert raw.initialized_axes == (True,) * 4
        assert raw.ready and raw.axes == (0.,) * 4
        assert set_axis(pointer(expected), 2, 12345) == 0
        raw = device.poll()
        assert raw.ready and raw.axes[2] == 12345 / 32768
        assert detach(index) == 0
        attached = False
        assert not device.poll().connected
    finally:
        if attached:
            detach(index)
        backend.close()
