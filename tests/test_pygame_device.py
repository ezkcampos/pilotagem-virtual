from types import SimpleNamespace

import pygame
import pytest

from pilotagem_virtual.input.device import DeviceInfo
from pilotagem_virtual.input.pygame_device import PygameInputDevice


class JoystickStub:
    def get_numaxes(self): return 4
    def get_axis(self, index): return float(index) / 4
    def get_numbuttons(self): return 1
    def get_button(self, index): return 1
    def get_numhats(self): return 1
    def get_hat(self, index): return (0, 1)


def device(state_reader=None):
    state_reader = state_reader or SimpleNamespace(read=lambda instance, axes: (True, (True,) * axes))
    return PygameInputDevice(JoystickStub(), DeviceInfo("guid:7", "G29", "guid", 4, 1, 1, 7), lambda: 42, state_reader)


def test_removal_uses_instance_id_and_stays_disconnected(monkeypatch):
    events = [SimpleNamespace(type=pygame.JOYDEVICEREMOVED, instance_id=8)]
    monkeypatch.setattr(pygame.event, "get", lambda: events)
    current = device()
    assert current.poll().connected
    events[0].instance_id = 7
    assert not current.poll().connected
    events.clear()
    assert not current.poll().connected


def test_event_pump_failure_becomes_disconnection(monkeypatch):
    def fail(): raise pygame.error("video unavailable")
    monkeypatch.setattr(pygame.event, "get", fail)
    assert not device().poll().connected


def test_read_is_timestamped_after_axes_and_buttons(monkeypatch):
    monkeypatch.setattr(pygame.event, "get", lambda: [])
    raw = device().poll()
    assert raw.timestamp_ns == 42
    assert raw.axes == (0, .25, .5, .75)
    assert raw.buttons == (1,)
    assert raw.hats == ((0, 1),)


def test_poll_cannot_move_to_another_thread(monkeypatch):
    current = device()
    monkeypatch.setattr("pilotagem_virtual.input.pygame_device.threading.get_ident", lambda: -1)
    with pytest.raises(RuntimeError, match="thread proprietária"):
        current.poll()


def test_readiness_is_not_guessed_from_axis_values(monkeypatch):
    monkeypatch.setattr(pygame.event, "get", lambda: [])
    statuses = iter([(True, (False,) * 4), (True, (True,) * 4), (False, ())])
    current = device(SimpleNamespace(read=lambda *args: next(statuses)))
    monkeypatch.setattr(current._joystick, "get_axis", lambda index: 0.)
    pending = current.poll()
    ready = current.poll()
    assert pending.axes == ready.axes == (0.,) * 4
    assert not pending.ready and ready.ready
    # Native attached status also catches removal without an event in the queue.
    assert not current.poll().connected
    assert not current.poll().connected
