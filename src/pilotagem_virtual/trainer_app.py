from __future__ import annotations

import sys
import time
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
)

from pilotagem_virtual.domain.calibration import (
    NormalizedControls,
    observed_g29_profile,
)
from pilotagem_virtual.domain.scenario import Scenario
from pilotagem_virtual.domain.session import AttemptSession, SessionState
from pilotagem_virtual.g29_axes import is_observed_g29_profile
from pilotagem_virtual.input.device import InputDevice
from pilotagem_virtual.input.pygame_device import PygameInputBackend
from pilotagem_virtual.ui.track_map import TrackMapWidget


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


class TrainerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pilotagem Virtual — Trail Braking")
        self.resize(1280, 760)

        self.scenario = Scenario.load(
            resource_path("resources/scenarios/medium_right_v1.json")
        )
        self.session = AttemptSession(self.scenario)
        self.backend = PygameInputBackend()
        self.device: InputDevice | None = None
        self.profile = None
        self.controls = NormalizedControls()
        self._completion_announced = False

        self._build_ui()
        self._refresh_devices()

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _build_ui(self) -> None:
        root_widget = QWidget()
        root = QVBoxLayout(root_widget)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)

        top = QHBoxLayout()
        branding = QVBoxLayout()
        title = QLabel("PILOTAGEM VIRTUAL")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #EEE8DC;")
        subtitle = QLabel("TREINO DE TRAIL BRAKING · BUILD 1")
        subtitle.setStyleSheet("color: #08A6C7; font-weight: 600;")
        branding.addWidget(title)
        branding.addWidget(subtitle)
        top.addLayout(branding)
        top.addStretch(1)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(360)
        self.device_combo.currentIndexChanged.connect(self._select_device)
        top.addWidget(self.device_combo)
        refresh = QPushButton("Detectar novamente")
        refresh.clicked.connect(self._refresh_devices)
        top.addWidget(refresh)
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
        self.brake_meter = ControlMeter("Freio")
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
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device = None
        self.profile = None
        devices = self.backend.list_devices()
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
            self.device = self.backend.open_device(str(device_id))
        except LookupError as error:
            self.device_status.setText(str(error))
            self.start_button.setEnabled(False)
            return

        info = self.device.info
        if is_observed_g29_profile(info.name, info.axis_count):
            self.profile = observed_g29_profile(info.name, info.guid)
            self.device_status.setText(
                "G29 conectado · perfil observado carregado · calibração personalizada virá no próximo build"
            )
            self.start_button.setEnabled(True)
        else:
            self.profile = None
            self.device_status.setText(
                "Dispositivo detectado, mas ainda sem perfil compatível. Use o diagnóstico do G29."
            )
            self.start_button.setEnabled(False)

    def _tick(self) -> None:
        now_ns = time.perf_counter_ns()
        if self.device is not None and self.profile is not None:
            raw = self.device.poll()
            if not raw.connected:
                self.session.cancel()
                self.device_status.setText("G29 desconectado. Detecte o dispositivo novamente.")
                self.start_button.setEnabled(False)
                self.cancel_button.setEnabled(False)
                return
            self.controls = self.profile.normalize(raw.axes)

        self.steering_meter.set_value(self.controls.steering)
        self.brake_meter.set_value(self.controls.brake)
        self.accelerator_meter.set_value(self.controls.accelerator)

        if self.session.state in {SessionState.COUNTDOWN, SessionState.RUNNING}:
            progress = self.session.tick(now_ns, self.controls)
            self.map_widget.set_progress(progress)
            if self.session.state == SessionState.COUNTDOWN:
                self.phase_label.setText(str(self.session.countdown_value(now_ns)))
            elif self.session.state == SessionState.RUNNING:
                self.phase_label.setText(self.scenario.active_marker(progress).label)
            elif self.session.state == SessionState.COMPLETED:
                self._show_completion()

    def _start_or_repeat(self) -> None:
        if self.device is None or self.profile is None:
            QMessageBox.information(self, "G29 necessário", "Conecte o G29 para iniciar a tentativa.")
            return
        self.session.start(time.perf_counter_ns())
        self._completion_announced = False
        self.result_label.setText("")
        self.phase_label.setText("3")
        self.map_widget.set_progress(0.0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def _cancel(self) -> None:
        self.session.cancel()
        self.phase_label.setText("CANCELADO")
        self.result_label.setText("Tentativa cancelada. Você pode iniciar novamente.")
        self.start_button.setText("Tentar novamente")
        self.start_button.setEnabled(self.device is not None and self.profile is not None)
        self.cancel_button.setEnabled(False)

    def _show_completion(self) -> None:
        if self._completion_announced:
            return
        self._completion_announced = True
        self.phase_label.setText("CONCLUÍDO")
        self.result_label.setText(
            f"Tentativa capturada com {len(self.session.samples)} amostras normalizadas. "
            "A pontuação será adicionada no próximo incremento."
        )
        self.start_button.setText("Repetir tentativa")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def closeEvent(self, event: Any) -> None:
        self.timer.stop()
        self.backend.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pilotagem Virtual")
    app.setOrganizationName("Pilotagem Virtual")
    window = TrainerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
