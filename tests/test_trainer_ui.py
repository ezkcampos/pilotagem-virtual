import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from pilotagem_virtual.domain.session import SessionState
from pilotagem_virtual.input.device import RawInputState
from pilotagem_virtual.trainer_app import TrainerWindow
from tests.test_trainer_controller import controller_for


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_rendering_cannot_create_samples_and_disconnect_restores_controls(app):
    states = [RawInputState(0, (0, 1, 1, 1), (), ()), RawInputState(3_000_000_000, (0, 1, 0, 1), (), ()), RawInputState(3_008_000_000, (), (), (), False)]
    controller = controller_for(states)
    window = TrainerWindow(controller)
    window.timer.stop()
    window.render_timer.stop()
    controller.poll()
    try:
        window._start_or_repeat()
        assert not window.refresh_button.isEnabled()
        assert not window.device_combo.isEnabled()
        controller.poll()
        for _ in range(100):
            window._tick()
        assert controller.session.sample_count == 1
        controller.poll()
        window._tick()
        assert window.phase_label.text() == "CANCELADO"
        assert window.refresh_button.isEnabled()
        assert not window.start_button.isEnabled()
    finally:
        window.close()
    assert controller.closed
    assert not window.timer.isActive() and not window.render_timer.isActive()


@pytest.mark.parametrize("size", [(1920, 1080), (2560, 1080)])
def test_legacy_completion_repeat_and_layout(app, size):
    states = [RawInputState(t, (0, 1, 0, 1), (), ()) for t in [0, 3_000_000_000, 11_000_000_000]]
    controller = controller_for(states)
    window = TrainerWindow(controller)
    window.timer.stop()
    window.render_timer.stop()
    controller.poll()
    try:
        window.resize(*size)
        window.show()
        app.processEvents()
        window._start_or_repeat()
        controller.poll()
        controller.poll()
        window._tick()
        assert controller.session.state == SessionState.COMPLETED
        assert "sem pontuação" in window.result_label.text()
        assert window.map_widget.progress == 1
        assert window.start_button.isEnabled()
        assert not window.grab().isNull()
        assert window.rect().contains(window.start_button.mapTo(window, window.start_button.rect().bottomRight()))
        previous = controller.session.snapshot()
        window._start_or_repeat()
        assert controller.session.state == SessionState.COUNTDOWN
        assert not controller.session.samples
        assert not window.result_label.text()
        assert previous.samples
    finally:
        window.close()


def test_initializing_device_hides_percentages_until_ready(app):
    controller = controller_for([
        RawInputState(0, (0,) * 4, (), (), initialized_axes=(False,) * 4),
        RawInputState(1, (0,) * 4, (), (), initialized_axes=(True,) * 4),
    ])
    window = TrainerWindow(controller)
    window.timer.stop()
    window.render_timer.stop()
    try:
        controller.poll()
        window._tick()
        assert not window.start_button.isEnabled()
        assert window.brake_meter.value_label.text() == "—"
        assert window.phase_label.text() == "AGUARDANDO"
        assert "Aguardando" in window.device_status.text()
        controller.poll()
        window._tick()
        assert window.start_button.isEnabled()
        assert window.brake_meter.value_label.text() == "50%"
        assert window.phase_label.text() == "PRONTO"
    finally:
        window.close()
