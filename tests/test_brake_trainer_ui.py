import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from pilotagem_virtual.persistence import TrainingStore
from pilotagem_virtual.trainer_app import BrakeTrainerWindow
from tests.test_trainer_controller import controller_for
from pilotagem_virtual.input.device import RawInputState
from pilotagem_virtual.input.device import DeviceInfo
from pilotagem_virtual.app.trainer import TrainerController
from pilotagem_virtual.domain.scenario import Scenario
from tests.test_scenario import scenario_payload


@pytest.fixture(scope='module')
def app(): return QApplication.instance() or QApplication([])


def make_window(tmp_path):
    states=[RawInputState(n*8_333_333,(0,1,1,1),(),()) for n in range(2500)]
    controller=controller_for(states)
    window=BrakeTrainerWindow(controller,TrainingStore(tmp_path/'ui.db'))
    window.timer.stop(); window.render_timer.stop(); controller.poll()
    return window


def test_modes_hide_and_restore_execution_without_changing_session(app,tmp_path):
    window=make_window(tmp_path)
    try:
        window.mode_combo.setCurrentText('Avaliação')
        window._start_or_repeat()
        window._tick()
        assert window.session.active and window.brake_meter.isHidden() and not window.chart.reveal
        attempt=window.session.attempt_id
        window.controller.cancel(); window._tick()
        assert not window.brake_meter.isHidden() and window.session.attempt_id==attempt
        window.mode_combo.setCurrentText('Guiado'); window._start_or_repeat()
        assert window.chart.reveal
    finally: window.close()


def test_guided_chart_requests_live_repaint_after_new_pedal_sample(app,tmp_path,monkeypatch):
    window=make_window(tmp_path)
    repaints=[]
    monkeypatch.setattr(window.chart,'update',lambda:repaints.append(len(window.chart.samples)))
    try:
        window._start_or_repeat()
        for _ in range(365): window.controller.poll()
        window._tick()
        assert window.session.samples
        assert repaints[-1]==len(window.session.samples)
        assert window.chart.reveal and window.chart.recording and not window.chart.result
    finally: window.close()


def test_catalog_navigation_curve_layout_and_legacy_remain_available(app,tmp_path):
    window=make_window(tmp_path)
    try:
        assert window.exercise_combo.count()==8
        window.exercise_combo.setCurrentIndex(6)
        assert window.visuals.currentIndex()==1 and window.map_widget.isVisibleTo(window.visuals)
        window.category_combo.setCurrentIndex(1)
        assert window.visuals.currentIndex()==2 and not window.exercise_combo.isEnabled()
        window.category_combo.setCurrentIndex(0)
        assert window.exercise_combo.isEnabled()
        window.resize(1920,1080); window.show(); app.processEvents()
        assert not window.grab().isNull()
    finally: window.close()


def test_completed_level_shows_score_graph_and_persists_snapshot(app,tmp_path):
    window=make_window(tmp_path)
    try:
        window._start_or_repeat()
        while window.session.active:
            window.controller.poll()
        window._tick()
        assert 'NOTA' in window.result_label.text()
        assert window.chart.result and window.chart.reveal and window.chart.samples
        assert window.start_button.text()=='Repetir tentativa'
        assert window.next_button.isEnabled()
        db=window.store.connect()
        try: assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]==1
        finally: db.close()
        first=window.session.snapshot()
        window._start_or_repeat()
        assert window.session.attempt_id != first.attempt_id and not window.session.samples
    finally: window.close()


def test_thirty_integrated_repetitions_do_not_reuse_samples_or_ids(app,tmp_path):
    class Device:
        now=0
        info=DeviceInfo('stream','Fake G29','fake-guid',4,0,0)
        def poll(self):
            self.now += 8_333_333
            return RawInputState(self.now,(0,1,1,1),(),())
    class Backend:
        def __init__(self): self.device=Device(); self.closed=False
        def list_devices(self): return [self.device.info]
        def open_device(self,device_id): return self.device
        def close(self): self.closed=True
    backend=Backend()
    controller=TrainerController(Scenario.from_dict(scenario_payload()),backend,lambda:backend.device.now)
    window=BrakeTrainerWindow(controller,TrainingStore(tmp_path/'repeat.db'))
    window.timer.stop(); window.render_timer.stop(); controller.poll()
    ids=[]
    try:
        for _ in range(30):
            window._start_or_repeat()
            while window.session.active: controller.poll()
            window._tick()
            assert window.session.sample_count < 800 and window.pending_save is None
            ids.append(window.session.attempt_id)
        assert len(set(ids))==30
        db=window.store.connect()
        try: assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]==30
        finally: db.close()
    finally: window.close()
