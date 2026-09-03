import pytest
from itertools import chain

from pilotagem_virtual.app.trainer import TrainerController
from pilotagem_virtual.domain.scenario import Scenario
from pilotagem_virtual.domain.session import SessionState
from pilotagem_virtual.input.device import RawInputState
from pilotagem_virtual.input.fake_device import FakeInputBackend, FakeInputDevice
from tests.test_scenario import scenario_payload


def controller_for(states, clock=lambda: 0):
    device = FakeInputDevice(chain([RawInputState(-1, (0, 1, 1, 1), (), ())], states))
    controller = TrainerController(Scenario.from_dict(scenario_payload()), FakeInputBackend(device), clock)
    controller.select_device(controller.refresh_devices()[0].device_id)
    controller.poll()
    return controller


def test_recording_uses_input_timestamp_instead_of_delivery_clock():
    times = iter([0, 99_000_000_000])
    controller = controller_for([RawInputState(3_123_000_000, (0, 1, -1, -1), (), ())], lambda: next(times))
    controller.start()
    controller.poll()
    assert controller.session.samples[0].elapsed_ns == 123_000_000
    assert controller.session.samples[0].controls.clutch == 1
    assert controller.clock_ns() == 99_000_000_000


@pytest.mark.parametrize("axes", [(0, 1), (0, 1, float("nan"), 1)])
def test_bad_axes_do_not_turn_into_half_pressed_pedals(axes):
    controller = controller_for([RawInputState(3_000_000_000, axes, (), ())])
    controller.start()
    controller.poll()
    assert controller.session.snapshot().reason == "invalid_axes"
    assert not controller.session.samples
    assert not controller.available


def test_fake_exhaustion_and_disconnect_cancel_and_freeze():
    controller = controller_for([RawInputState(3_000_000_000, (0, 1, 0, 1), (), ())])
    controller.start()
    controller.poll()
    controller.poll()
    assert controller.session.snapshot().reason == "input_exhausted"
    assert controller.session.sample_count == 1
    controller.close()
    controller.close()
    assert controller.backend.closed
    disconnected = controller_for([RawInputState(1, (), (), (), False)])
    disconnected.start()
    disconnected.poll()
    assert disconnected.session.snapshot().reason == "device_disconnected"


def test_cannot_change_device_or_restart_during_recording():
    controller = controller_for([])
    controller.start()
    for command in [controller.refresh_devices, controller.start, lambda: controller.select_device("fake-g29")]:
        with pytest.raises(RuntimeError):
            command()
    assert controller.session.state == SessionState.COUNTDOWN
    controller.close()
    assert controller.session.snapshot().reason == "application_closed"


def test_start_waits_for_confirmed_initial_state_and_accepts_legitimate_zero():
    controller = controller_for([
        RawInputState(0, (0,) * 4, (), (), initialized_axes=(False,) * 4),
        RawInputState(1, (0,) * 4, (), (), initialized_axes=(True,) * 4),
        RawInputState(3_100_000_000, (0,) * 4, (), (), initialized_axes=(True,) * 4),
        RawInputState(3_200_000_000, (0,) * 4, (), (), initialized_axes=(False,) * 4),
    ])
    controller.select_device("fake-g29")
    controller.poll()
    assert controller.waiting_for_input and not controller.available
    assert not controller.session.samples and controller.controls.brake == 0
    with pytest.raises(RuntimeError, match="primeira leitura"):
        controller.start()
    controller.poll()
    assert controller.available and not controller.waiting_for_input
    assert controller.controls.brake == pytest.approx(.5, abs=.0001)
    controller.start()
    controller.poll()
    assert controller.session.sample_count == 1
    controller.poll()
    assert controller.session.snapshot().reason == "input_not_ready"
    assert controller.session.sample_count == 1
