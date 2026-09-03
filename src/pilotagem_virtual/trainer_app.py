from __future__ import annotations

import sys
import os
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QScrollArea,
)

from pilotagem_virtual.app.trainer import TrainerController
from pilotagem_virtual.domain.acquisition import summarize_acquisition
from pilotagem_virtual.domain.scenario import Scenario
from pilotagem_virtual.domain.session import SessionState
from pilotagem_virtual.input.pygame_device import PygameInputBackend
from pilotagem_virtual.ui.track_map import TrackMapWidget
from pilotagem_virtual.ui.brake_chart import BrakeChart
from pilotagem_virtual.ui.brake_calibration import BrakeCalibrationDialog
from pilotagem_virtual.domain.exercise import load_catalog
from pilotagem_virtual.domain.brake_scoring import score, SURFACES
from pilotagem_virtual.domain.session import AttemptSession
from pilotagem_virtual.persistence import TrainingStore, attempt_payload


POLL_INTERVAL_MS = 8


def resource_path(relative: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return bundle_root / relative


class ControlMeter(QWidget):
    def __init__(self, label: str, centered: bool = False) -> None:
        super().__init__()
        self.centered = centered
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title_row = QHBoxLayout()
        title = QLabel(label)
        title.setStyleSheet("font-weight: 600;")
        self.value_label = QLabel("0%")
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.value_label)
        layout.addLayout(title_row)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 2000 if centered else 1000)
        self.bar.setFixedHeight(16)
        layout.addWidget(self.bar)

    def set_value(self, value: float) -> None:
        if self.centered:
            value = max(-1.0, min(1.0, value))
            self.bar.setValue(round((value + 1.0) * 1000))
            self.value_label.setText(f"{value * 100:+.0f}%")
        else:
            value = max(0.0, min(1.0, value))
            self.bar.setValue(round(value * 1000))
            self.value_label.setText(f"{value * 100:.0f}%")

    def set_pending(self) -> None:
        self.bar.setValue(1000 if self.centered else 0)
        self.value_label.setText("—")


class TrainerWindow(QMainWindow):
    def __init__(self, controller: TrainerController | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Pilotagem Virtual — Trail Braking")
        self.resize(1280, 760)

        self.scenario = controller.session.scenario if controller else Scenario.load(
            resource_path("resources/scenarios/medium_right_v1.json")
        )
        self.controller = controller or TrainerController(self.scenario, PygameInputBackend())
        self.session = self.controller.session
        self._completion_announced = False

        self._build_ui()
        self._refresh_devices()

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self.controller.poll)
        self.timer.start()
        self.render_timer = QTimer(self)
        self.render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.render_timer.setInterval(17)
        self.render_timer.timeout.connect(self._tick)
        self.render_timer.start()

    def _build_ui(self) -> None:
        root_widget = QWidget()
        root = QVBoxLayout(root_widget)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)

        top = QHBoxLayout()
        branding = QVBoxLayout()
        title = QLabel("PILOTAGEM VIRTUAL")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #EEE8DC;")
        subtitle = QLabel("TRAIL BRAKING · DESENVOLVIMENTO P0")
        subtitle.setStyleSheet("color: #08A6C7; font-weight: 600;")
        branding.addWidget(title)
        branding.addWidget(subtitle)
        top.addLayout(branding)
        top.addStretch(1)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(360)
        self.device_combo.currentIndexChanged.connect(self._select_device)
        top.addWidget(self.device_combo)
        self.refresh_button = QPushButton("Detectar novamente")
        self.refresh_button.clicked.connect(self._refresh_devices)
        top.addWidget(self.refresh_button)
        root.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(18)
        self.map_widget = TrackMapWidget(self.scenario)
        body.addWidget(self.map_widget, 3)

        side = QFrame()
        side.setFrameShape(QFrame.Shape.StyledPanel)
        side.setMinimumWidth(330)
        side_layout = QVBoxLayout(side)
        scenario_title = QLabel(self.scenario.name)
        scenario_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        side_layout.addWidget(scenario_title)
        difficulty = QLabel(
            f"Nível: {self.scenario.difficulty} · {self.scenario.duration_seconds:.0f} segundos"
        )
        difficulty.setStyleSheet("color: #AAB3B0;")
        side_layout.addWidget(difficulty)
        description = QLabel(self.scenario.description)
        description.setWordWrap(True)
        side_layout.addWidget(description)

        self.phase_label = QLabel("PRONTO")
        self.phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phase_label.setStyleSheet(
            "font-size: 32px; font-weight: 800; color: #08A6C7; margin: 18px 0;"
        )
        side_layout.addWidget(self.phase_label)

        self.steering_meter = ControlMeter("Volante", centered=True)
        self.brake_meter = ControlMeter("Entrada do freio (%)")
        self.accelerator_meter = ControlMeter("Acelerador")
        side_layout.addWidget(self.steering_meter)
        side_layout.addWidget(self.brake_meter)
        side_layout.addWidget(self.accelerator_meter)
        side_layout.addStretch(1)

        self.device_status = QLabel("Procurando G29...")
        self.device_status.setWordWrap(True)
        side_layout.addWidget(self.device_status)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        side_layout.addWidget(self.result_label)

        actions = QHBoxLayout()
        self.start_button = QPushButton("Iniciar tentativa")
        self.start_button.setMinimumHeight(42)
        self.start_button.clicked.connect(self._start_or_repeat)
        actions.addWidget(self.start_button, 1)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.cancel_button)
        side_layout.addLayout(actions)
        body.addWidget(side, 1)
        root.addLayout(body, 1)

        self.setCentralWidget(root_widget)
        self.setStyleSheet(
            "QMainWindow, QWidget { background: #101716; color: #EEE8DC; }"
            "QFrame { background: #18201F; border: 1px solid #34403E; border-radius: 8px; }"
            "QPushButton { background: #08A6C7; color: #101716; border: 0; "
            "border-radius: 5px; padding: 9px 14px; font-weight: 700; }"
            "QPushButton:disabled { background: #394240; color: #717C78; }"
            "QComboBox { background: #18201F; border: 1px solid #717C78; "
            "border-radius: 4px; padding: 8px; }"
            "QProgressBar { background: #2A3331; border: 0; border-radius: 5px; }"
            "QProgressBar::chunk { background: #08A6C7; border-radius: 5px; }"
        )

    def _refresh_devices(self) -> None:
        if self.session.active:
            return
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        devices = self.controller.refresh_devices()
        for device in devices:
            self.device_combo.addItem(device.name, device.device_id)
        self.device_combo.blockSignals(False)
        if devices:
            self.device_combo.setCurrentIndex(0)
            self._select_device(0)
        else:
            self.device_status.setText("G29 não detectado. Conecte-o e clique em Detectar novamente.")
            self.start_button.setEnabled(False)

    def _select_device(self, index: int) -> None:
        device_id = self.device_combo.itemData(index)
        if not device_id:
            return
        try:
            self.controller.select_device(str(device_id))
        except (LookupError, RuntimeError) as error:
            self.device_status.setText(str(error))
            self.start_button.setEnabled(False)
            return

        if self.controller.waiting_for_input:
            self.device_status.setText("Aguardando primeira leitura do G29. Mova e solte os pedais.")
            self.start_button.setEnabled(False)
        elif self.controller.available:
            self.device_status.setText(
                "G29 conectado · perfil observado carregado · calibração personalizada virá no próximo build"
            )
            self.start_button.setEnabled(True)
        else:
            self.device_status.setText(
                "Dispositivo detectado, mas ainda sem perfil compatível. Use o diagnóstico do G29."
            )
            self.start_button.setEnabled(False)

    def _tick(self) -> None:
        controls = self.controller.controls
        self.steering_meter.set_value(controls.steering)
        self.brake_meter.set_value(controls.brake)
        self.accelerator_meter.set_value(controls.accelerator)
        self.start_button.setEnabled(not self.session.active and self.controller.available)
        if self.controller.error:
            self.device_status.setText("Leitura indisponível. Detecte o G29 novamente.")
        elif self.controller.waiting_for_input:
            self.device_status.setText("Aguardando primeira leitura do G29. Mova e solte os pedais.")
        elif self.controller.available:
            self.device_status.setText("G29 pronto · perfil observado carregado")
        if not self.controller.available:
            for meter in (self.steering_meter, self.brake_meter, self.accelerator_meter):
                meter.set_pending()
        self.map_widget.set_progress(self.session.progress)
        if self.session.state == SessionState.PREVIEW:
            self.phase_label.setText("PRONTO" if self.controller.available else "AGUARDANDO")
        elif self.session.state == SessionState.COUNTDOWN:
            self.phase_label.setText(str(self.session.countdown_value(self.controller.clock_ns())))
        elif self.session.state == SessionState.RUNNING:
            self.phase_label.setText(self.scenario.active_marker(self.session.progress).label)
        elif self.session.state == SessionState.COMPLETED:
            self._show_completion()
        elif self.session.state == SessionState.CANCELLED and not self._completion_announced:
            self._show_cancelled()

    def _start_or_repeat(self) -> None:
        try:
            self.controller.start()
        except RuntimeError as error:
            QMessageBox.information(self, "G29 necessário", str(error))
            return
        self._completion_announced = False
        self.result_label.setText("")
        self.phase_label.setText("3")
        self.map_widget.set_progress(0.0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.device_combo.setEnabled(False)
        self.refresh_button.setEnabled(False)

    def _cancel(self) -> None:
        self.controller.cancel()
        self._show_cancelled()

    def _show_cancelled(self) -> None:
        self._completion_announced = True
        self.phase_label.setText("CANCELADO")
        message = "Tentativa cancelada. Você pode iniciar novamente."
        if self.session.reason != "user_cancelled":
            message = "Captura interrompida por falha de leitura. Detecte o G29 novamente."
        self.result_label.setText(message)
        self.start_button.setText("Tentar novamente")
        self.start_button.setEnabled(self.controller.available)
        self.cancel_button.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.refresh_button.setEnabled(True)

    def _show_completion(self) -> None:
        if self._completion_announced:
            return
        self._completion_announced = True
        self.phase_label.setText("CONCLUÍDO")
        snapshot = self.session.snapshot()
        report = summarize_acquisition(
            [sample.elapsed_ns for sample in snapshot.samples], self.session.duration_ns,
        )
        quality = " Verifique a captura: houve lacunas ou baixa frequência." if report.issues else ""
        self.result_label.setText(
            f"{report.sample_count} amostras · leitura média {report.observed_hz:.1f} Hz. "
            f"Exercício legado sem pontuação.{quality}"
        )
        self.start_button.setText("Repetir tentativa")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.refresh_button.setEnabled(True)

    def closeEvent(self, event: Any) -> None:
        self.timer.stop()
        self.render_timer.stop()
        self.controller.close()
        super().closeEvent(event)


class BrakeTrainerWindow(TrainerWindow):
    """Integrated 0.2 trainer. The legacy window remains testable and accessible."""
    def __init__(self, controller=None, store=None):
        self.catalog=load_catalog(resource_path('resources/scenarios/brake_levels_v1.json'))
        self.exercise=self.catalog[0]
        self.mode='Guiado'
        self.surface='Seca'
        self.abs_enabled=False
        self.comparison_id=None
        self.abs_reports={}
        self.pending_save=None
        self.store=store or TrainingStore(Path(os.getenv('LOCALAPPDATA',Path.home()))/'PilotagemVirtual'/'pilotagem-virtual.db')
        self._legacy_scenario=(controller.session.scenario if controller else Scenario.load(resource_path('resources/scenarios/medium_right_v1.json')))
        super().__init__(controller)
        self.setWindowTitle('Pilotagem Virtual — Fundamentos do freio 0.2')

    def _scenario_for(self,exercise):
        return replace(self._legacy_scenario,name=exercise.name,description=exercise.objective,
                       difficulty=f'Nível {exercise.level}',duration_seconds=exercise.duration)

    def _build_ui(self):
        central=QWidget()
        root=QVBoxLayout(central)
        root.setContentsMargins(16,12,16,14)
        root.setSpacing(9)
        top=QHBoxLayout()
        brand=QLabel('PILOTAGEM VIRTUAL  ·  FUNDAMENTOS DO FREIO')
        brand.setStyleSheet('font-size: 20px; font-weight: 800; color:#eee8dc')
        top.addWidget(brand)
        top.addStretch()
        self.device_combo=QComboBox(); self.device_combo.setMinimumWidth(310)
        self.device_combo.currentIndexChanged.connect(self._select_device)
        self.refresh_button=QPushButton('Detectar novamente'); self.refresh_button.clicked.connect(self._refresh_devices)
        self.calibrate_button=QPushButton('Calibrar freio'); self.calibrate_button.clicked.connect(self._calibrate)
        self.restore_button=QPushButton('Restaurar perfil G29'); self.restore_button.clicked.connect(self._restore_profile)
        top.addWidget(self.device_combo); top.addWidget(self.refresh_button); top.addWidget(self.calibrate_button); top.addWidget(self.restore_button)
        root.addLayout(top)
        selection=QHBoxLayout()
        self.category_combo=QComboBox(); self.category_combo.addItems(['Fundamentos do freio','Trail braking em curva — legado'])
        self.category_combo.currentIndexChanged.connect(self._category_changed)
        self.exercise_combo=QComboBox()
        for e in self.catalog: self.exercise_combo.addItem(f'{e.level}. {e.name}',e.id)
        self.exercise_combo.currentIndexChanged.connect(self._exercise_changed)
        self.mode_combo=QComboBox(); self.mode_combo.addItems(['Guiado','Memória','Avaliação']); self.mode_combo.currentTextChanged.connect(self._mode_changed)
        self.surface_combo=QComboBox(); self.surface_combo.addItems(SURFACES); self.surface_combo.currentTextChanged.connect(self._surface_changed)
        for w in (self.category_combo,self.exercise_combo,self.mode_combo,self.surface_combo): selection.addWidget(w)
        root.addLayout(selection)
        body=QHBoxLayout(); body.setSpacing(12)
        self.visuals=QStackedWidget()
        self.chart=BrakeChart(); self.chart.exercise=self.exercise; self.chart.inspected.connect(self._inspection)
        self.map_widget=TrackMapWidget(self._legacy_scenario)
        combined=QWidget(); combined_layout=QVBoxLayout(combined); combined_layout.setContentsMargins(0,0,0,0)
        combined_layout.addWidget(self.map_widget,3); self.curve_chart=BrakeChart(); self.curve_chart.exercise=self.catalog[6]; combined_layout.addWidget(self.curve_chart,2)
        self.visuals.addWidget(self.chart); self.visuals.addWidget(combined); self.visuals.addWidget(TrackMapWidget(self._legacy_scenario))
        body.addWidget(self.visuals,3)
        side=QFrame(); side.setMinimumWidth(390); side.setMaximumWidth(510)
        side_layout=QVBoxLayout(side)
        self.scenario_title=QLabel(); self.scenario_title.setStyleSheet('font-size:20px;font-weight:700')
        self.difficulty=QLabel(); self.description=QLabel(); self.description.setWordWrap(True)
        self.phase_label=QLabel('PRONTO'); self.phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.phase_label.setStyleSheet('font-size:34px;font-weight:800;color:#08a6c7;margin:8px')
        for w in (self.scenario_title,self.difficulty,self.description,self.phase_label): side_layout.addWidget(w)
        self.steering_meter=ControlMeter('Volante',True); self.brake_meter=ControlMeter('Entrada do freio (%)'); self.accelerator_meter=ControlMeter('Acelerador')
        for w in (self.steering_meter,self.brake_meter,self.accelerator_meter): side_layout.addWidget(w)
        self.device_status=QLabel('Procurando G29...'); self.device_status.setWordWrap(True)
        self.result_label=QLabel(''); self.result_label.setWordWrap(True); self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        result_scroll=QScrollArea(); result_scroll.setWidgetResizable(True); result_scroll.setMinimumHeight(120); result_scroll.setWidget(self.result_label)
        side_layout.addWidget(self.device_status); side_layout.addWidget(result_scroll,1)
        actions=QHBoxLayout(); self.start_button=QPushButton('Iniciar tentativa'); self.start_button.setMinimumHeight(42); self.start_button.clicked.connect(self._start_or_repeat)
        self.next_button=QPushButton('Próximo nível'); self.next_button.clicked.connect(self._next); self.next_button.setEnabled(False)
        self.cancel_button=QPushButton('Cancelar'); self.cancel_button.clicked.connect(self._cancel); self.cancel_button.setEnabled(False)
        for w in (self.start_button,self.next_button,self.cancel_button): actions.addWidget(w)
        side_layout.addLayout(actions); body.addWidget(side,1); root.addLayout(body,1)
        self.setCentralWidget(central)
        self.setStyleSheet("QMainWindow,QWidget{background:#101716;color:#eee8dc} QFrame{background:#18201f;border:1px solid #34403e;border-radius:8px} QPushButton{background:#08a6c7;color:#101716;border:0;border-radius:5px;padding:8px;font-weight:700} QPushButton:disabled{background:#394240;color:#717c78} QComboBox{background:#18201f;border:1px solid #717c78;border-radius:4px;padding:7px} QProgressBar{background:#2a3331;border:0;border-radius:5px} QProgressBar::chunk{background:#08a6c7;border-radius:5px} QScrollArea{border:0}")
        self._apply_exercise()

    def _set_session(self,scenario):
        self.controller.session=AttemptSession(scenario)
        self.session=self.controller.session
        self.scenario=scenario

    def _category_changed(self,index):
        if self.session.active: return
        legacy=index==1
        self.exercise_combo.setEnabled(not legacy); self.mode_combo.setEnabled(not legacy); self.surface_combo.setEnabled(not legacy and self.exercise.level==8)
        if legacy:
            self._set_session(self._legacy_scenario); self.visuals.setCurrentIndex(2)
            self.scenario_title.setText(self._legacy_scenario.name); self.difficulty.setText('Exercício original · 8 segundos'); self.description.setText(self._legacy_scenario.description)
        else:
            self._apply_exercise()
        self.result_label.clear(); self.phase_label.setText('PRONTO'); self.next_button.setEnabled(False)

    def _exercise_changed(self,index):
        if index < 0 or self.session.active: return
        self.exercise=self.catalog[index]
        self._apply_exercise()

    def _apply_exercise(self):
        scenario=self._scenario_for(self.exercise)
        self._set_session(scenario)
        self.chart.exercise=self.exercise; self.curve_chart.exercise=self.exercise
        self.chart.override_target=SURFACES[self.surface] if self.exercise.level==8 else None
        self.visuals.setCurrentIndex(1 if self.exercise.level==7 else 0)
        self.scenario_title.setText(self.exercise.name)
        self.difficulty.setText(f'Nível {self.exercise.level} · {self.exercise.duration:.0f} segundos · tolerância ±{self.exercise.tolerance*100:.0f} pp')
        self.description.setText(self.exercise.objective)
        self.surface_combo.setVisible(self.exercise.level==8); self.surface_combo.setEnabled(self.exercise.level==8)
        self.abs_enabled=self.exercise.level==8
        self.abs_reports={}; self.comparison_id=None
        self._clear_charts(); self.result_label.clear(); self.next_button.setEnabled(False)

    def _clear_charts(self):
        for chart in (self.chart,self.curve_chart):
            chart.samples=(); chart.reveal=True; chart.result=False; chart.recording=False; chart.simulation=None; chart.progress=0; chart.frames.clear(); chart.update()

    def _mode_changed(self,text): self.mode=text
    def _surface_changed(self,text):
        self.surface=text
        if self.exercise.level==8:
            self.chart.override_target=SURFACES[text]
            self.chart.update()

    def _select_device(self,index):
        super()._select_device(index)
        if self.controller.device and self.controller.profile:
            try:
                saved=self.store.load_profile(self.controller.device.info)
                if saved: self.controller.profile=saved
            except (OSError,ValueError) as error:
                self.device_status.setText(f'Perfil salvo inválido: {error}. Restaure ou calibre novamente.')

    def _calibrate(self):
        if self.session.active or not self.controller.available or not self.controller.device:
            QMessageBox.information(self,'Calibração','Conecte o G29 e aguarde a leitura antes de calibrar.')
            return
        def save(profile):
            self.store.save_profile(self.controller.device.info,profile)
            self.controller.profile=profile
        dialog=BrakeCalibrationDialog(self.controller,save,self)
        if dialog.exec(): self.device_status.setText('G29 pronto · calibração personalizada salva')

    def _restore_profile(self):
        if self.controller.device:
            from pilotagem_virtual.domain.calibration import observed_g29_profile
            profile=observed_g29_profile(self.controller.device.info.name,self.controller.device.info.guid)
            self.store.save_profile(self.controller.device.info,profile); self.controller.profile=profile
            self.device_status.setText('G29 pronto · perfil observado restaurado')

    def _start_or_repeat(self):
        if self.pending_save:
            try: self.store.save_attempt(self.pending_save); self.pending_save=None
            except (OSError,ValueError) as error:
                self.result_label.setText(f'Falha ao salvar a tentativa anterior: {error}. Tente novamente antes de iniciar outra.')
                return
        if self.category_combo.currentIndex()==0:
            if self.exercise.level==8 and {'com_abs','sem_abs'} <= self.abs_reports.keys():
                self.abs_reports={}; self.comparison_id=None
            if self.exercise.level==8 and self.comparison_id is None: self.comparison_id=uuid.uuid4().hex
            self.abs_enabled=self.exercise.level==8 and 'com_abs' not in self.abs_reports
        super()._start_or_repeat()
        if not self.session.active: return
        self.next_button.setEnabled(False)
        for widget in (self.category_combo,self.exercise_combo,self.mode_combo,self.surface_combo,self.calibrate_button,self.restore_button):
            widget.setEnabled(False)
        guided=self.category_combo.currentIndex()==0 and self.mode=='Guiado'
        for chart in (self.chart,self.curve_chart):
            chart.samples=(); chart.reveal=guided; chart.result=False; chart.recording=True; chart.simulation=None; chart.update()
        self._apply_assistance()

    def _apply_assistance(self):
        active=self.session.active
        evaluation=active and self.category_combo.currentIndex()==0 and self.mode=='Avaliação'
        memory=active and self.category_combo.currentIndex()==0 and self.mode=='Memória'
        self.brake_meter.setVisible(not evaluation)
        self.steering_meter.setVisible(not evaluation and self.exercise.level==7)
        self.accelerator_meter.setVisible(not evaluation and self.exercise.level==7)
        if memory: self.description.setText('Execute o objetivo de memória. A comparação será revelada no resultado.')
        elif evaluation: self.description.setText('Avaliação em andamento. Entrada e curva serão reveladas no resultado.')
        elif self.category_combo.currentIndex()==0: self.description.setText(self.exercise.objective)

    def _tick(self):
        super()._tick()
        if self.category_combo.currentIndex()==1: return
        samples=self.session.samples
        for chart in (self.chart,self.curve_chart):
            chart.samples=samples; chart.progress=self.session.progress
        if self.session.active: self._apply_assistance()

    def _show_completion(self):
        if self._completion_announced: return
        if self.category_combo.currentIndex()==1:
            super()._show_completion()
            for widget in (self.category_combo,self.exercise_combo,self.mode_combo,self.calibrate_button,self.restore_button): widget.setEnabled(True)
            self.surface_combo.setEnabled(False)
            return
        self._completion_announced=True; self.phase_label.setText('CONCLUÍDO')
        snapshot=self.session.snapshot()
        report=score(self.exercise,snapshot.samples,surface=self.surface,abs_enabled=self.abs_enabled)
        key='com_abs' if self.abs_enabled else 'sem_abs'
        if self.exercise.level==8: self.abs_reports[key]=report
        for chart in (self.chart,self.curve_chart):
            chart.samples=snapshot.samples; chart.reveal=True; chart.result=True; chart.recording=False; chart.simulation=report.get('simulation'); chart.update()
        self._apply_assistance(); self.brake_meter.show()
        if self.exercise.level==7: self.steering_meter.show(); self.accelerator_meter.show()
        if report['valid']:
            components=' · '.join(f"{c['name']}: {c['score']:.0f}" for c in report['components'])
            message=f"NOTA {report['score']:.0f}/100\n{components}\n{report['feedback']}"
            if report.get('simulation'):
                sim=report['simulation']; message+=f"\nSimulação didática: {sim['locked_seconds']:.2f} s travada · {sim['useful_seconds']:.2f} s perto do limite."
        else: message=f"SEM NOTA\n{report['feedback']}"
        if self.exercise.level==8 and self.abs_enabled:
            message='ETAPA COM ABS — Simulação didática\n'+message+'\nAgora faça a etapa sem ABS nas mesmas condições.'
            self.start_button.setText('Iniciar etapa sem ABS')
        elif self.exercise.level==8:
            first=self.abs_reports.get('com_abs')
            if first and first.get('valid') and report.get('valid'):
                message+=f"\nComparação: com ABS {first['score']:.0f} · sem ABS {report['score']:.0f}."
            self.start_button.setText('Repetir comparação')
        else: self.start_button.setText('Repetir tentativa')
        self.result_label.setText(message)
        payload=attempt_payload(snapshot,self.exercise,report,self.mode,self.surface,self.abs_enabled,self.comparison_id)
        try: self.store.save_attempt(payload)
        except (OSError,ValueError) as error:
            self.pending_save=payload; self.result_label.setText(message+f'\nFalha ao salvar: {error}. A tentativa continua em memória; tente novamente.')
        self.start_button.setEnabled(self.controller.available); self.cancel_button.setEnabled(False)
        self.device_combo.setEnabled(True); self.refresh_button.setEnabled(True); self.next_button.setEnabled(self.exercise.level<8 and report['valid'])
        for widget in (self.category_combo,self.exercise_combo,self.mode_combo,self.calibrate_button,self.restore_button): widget.setEnabled(True)
        self.surface_combo.setEnabled(self.exercise.level==8)

    def _show_cancelled(self):
        super()._show_cancelled(); self._apply_assistance(); self.brake_meter.show()
        self._clear_charts()
        for widget in (self.category_combo,self.exercise_combo,self.mode_combo,self.calibrate_button,self.restore_button): widget.setEnabled(True)
        self.surface_combo.setEnabled(self.exercise.level==8)

    def _next(self):
        if self.exercise.level<8:
            self.exercise_combo.setCurrentIndex(self.exercise.level)

    def _inspection(self,text): self.result_label.setText(self.result_label.text()+'\n'+text)


def main() -> int:
    if "--acquisition-probe" in sys.argv:
        from pilotagem_virtual.acquisition_probe import main as probe_main
        return probe_main([arg for arg in sys.argv[1:] if arg != "--acquisition-probe"])
    app = QApplication(sys.argv)
    app.setApplicationName("Pilotagem Virtual")
    app.setOrganizationName("Pilotagem Virtual")
    window = BrakeTrainerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
