import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pilotagem_virtual.domain.brake_scoring import score
from pilotagem_virtual.domain.exercise import Exercise
from pilotagem_virtual.persistence import TrainingStore
from pilotagem_virtual.trainer_app import BrakeTrainerWindow
from pilotagem_virtual.ui.curve_editor import CurveEditorDialog, DEFAULT_VALUES
from tests.test_brake_exercises import series
from tests.test_trainer_controller import controller_for
from pilotagem_virtual.input.device import RawInputState


@pytest.fixture(scope='module')
def app(): return QApplication.instance() or QApplication([])


def custom_exercise(name='Minha curva'):
    duration=8.
    return Exercise.from_dict({
        'id':'custom-test','level':0,'name':name,
        'objective':'Acompanhe a curva personalizada criada por você.',
        'family':'custom','duration':duration,
        'target':[(duration*i/10,value/100) for i,value in enumerate(DEFAULT_VALUES)],
        'windows':[(0,duration)],'tolerance':.08,
        'steering':[(0,0),(duration,0)],'accelerator':[(0,0),(duration,0)],
        'custom':True,
    })


def test_custom_curve_requires_eleven_fixed_time_points_and_scores_target():
    exercise=custom_exercise()
    result=score(exercise,series(exercise))
    assert result['valid'] and result['score'] >= 99
    with pytest.raises(ValueError):
        Exercise.from_dict({**exercise.__dict__,'target':exercise.target[:-1]})
    moved=list(exercise.target); moved[5]=(4.1,moved[5][1])
    with pytest.raises(ValueError):
        Exercise.from_dict({**exercise.__dict__,'target':moved})


def test_editor_keyboard_duration_and_store_roundtrip(app,tmp_path):
    dialog=CurveEditorDialog()
    dialog.editor.setFocus()
    QTest.keyClick(dialog.editor,Qt.Key.Key_Right)
    before=dialog.editor.values[1]
    QTest.keyClick(dialog.editor,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier)
    assert dialog.editor.selected==1 and dialog.editor.values[1]==before-5
    dialog.name.setText('Curva de teste'); dialog.duration.setValue(7.5); dialog._save()
    exercise=dialog.result_exercise
    assert exercise.target[5][0]==3.75 and exercise.target[-1][0]==7.5

    store=TrainingStore(tmp_path/'custom.db')
    store.save_custom_exercise(exercise)
    assert store.load_custom_exercises()==(exercise,)
    updated=replace(exercise,name='Curva atualizada',version=2)
    store.save_custom_exercise(updated)
    assert store.load_custom_exercises()==(updated,)


def test_saved_custom_curve_appears_as_own_training_category(app,tmp_path):
    store=TrainingStore(tmp_path/'ui.db'); exercise=custom_exercise()
    store.save_custom_exercise(exercise)
    states=[RawInputState(n*8_333_333,(0,1,1,1),(),()) for n in range(2500)]
    controller=controller_for(states)
    window=BrakeTrainerWindow(controller,store)
    window.timer.stop(); window.render_timer.stop(); controller.poll()
    try:
        window.category_combo.setCurrentIndex(1)
        assert window.exercise_combo.count()==1
        assert window.exercise.id==exercise.id and window.chart.exercise==exercise
        assert window.new_curve_button.isVisibleTo(window) and window.edit_curve_button.isEnabled()
        window._start_or_repeat()
        for _ in range(365): controller.poll()
        window._tick()
        assert window.session.active and window.chart.recording and window.chart.reveal
        assert window.chart.samples
    finally: window.close()
