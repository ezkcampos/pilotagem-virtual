from __future__ import annotations

import os
import platform
import sys
from collections import deque
from pathlib import Path
from typing import Any

os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

import pygame
from PySide6.QtCore import QStandardPaths, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pilotagem_virtual import __version__
from pilotagem_virtual.g29_axes import (
    G29_AXIS_DESCRIPTORS,
    AxisDescriptor,
    is_observed_g29_profile,
    normalize_g29_axis,
)
from pilotagem_virtual.spike_capture import CaptureWriter, suggested_filename


TARGET_HZ = 120
TIMER_INTERVAL_MS = round(1000 / TARGET_HZ)


class AxisRow:
    def __init__(self, index: int, descriptor: AxisDescriptor | None = None) -> None:
        self.index = index
        self.descriptor = descriptor
        name = descriptor.name if descriptor is not None else "Eixo"
        self.label = QLabel(f"{name} (eixo {index})" if descriptor else f"Eixo {index}")
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000 if descriptor and descriptor.kind == "pedal" else 2000)
        self.bar.setTextVisible(False)
        self.value = QLabel("0.000000")
        self.value.setMinimumWidth(190)

    def update(self, raw_value: float) -> None:
        bounded = max(-1.0, min(1.0, raw_value))
        if self.descriptor is None:
            self.bar.setValue(round((bounded + 1.0) * 1000))
            self.value.setText(f"bruto {raw_value:+.6f}")
            return

        normalized = normalize_g29_axis(self.index, raw_value)
        if self.descriptor.kind == "pedal":
            self.bar.setValue(round(normalized * 1000))
            self.value.setText(f"{normalized * 100:5.1f}% | bruto {raw_value:+.6f}")
        else:
            self.bar.setValue(round((normalized + 1.0) * 1000))
            self.value.setText(f"{normalized * 100:+5.1f}% | bruto {raw_value:+.6f}")


class HardwareSpikeWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pilotagem Virtual — Diagnóstico do G29")
        self.resize(920, 720)

        self._joysticks: list[pygame.joystick.JoystickType] = []
        self._joystick: pygame.joystick.JoystickType | None = None
        self._axis_rows: list[AxisRow] = []
        self._writer: CaptureWriter | None = None
        self._recent_ticks: deque[int] = deque()
        self._last_capture_path: Path | None = None

        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._poll_device)

        pygame.joystick.init()
        self.refresh_devices()
        self._timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        title = QLabel("Diagnóstico e calibração inicial do G29")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(title)

        instructions = QLabel(
            "Conecte o G29 e abra o Logitech G Hub. Durante a gravação, mova o volante "
            "até os dois limites, pressione cada pedal separadamente e depois em conjunto, "
            "e pressione todos os botões. A tela normaliza o G29 em porcentagem; "
            "o arquivo JSONL preserva os valores brutos."
        )
        instructions.setWordWrap(True)
        root.addWidget(instructions)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Dispositivo:"))
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._select_device)
        device_row.addWidget(self.device_combo, 1)
        self.refresh_button = QPushButton("Atualizar dispositivos")
        self.refresh_button.clicked.connect(lambda: self.refresh_devices())
        device_row.addWidget(self.refresh_button)
        root.addLayout(device_row)

        self.device_details = QLabel("Nenhum dispositivo selecionado")
        self.device_details.setWordWrap(True)
        root.addWidget(self.device_details)

        self.axes_group = QGroupBox("Eixos brutos")
        self.axes_layout = QGridLayout(self.axes_group)
        axes_scroll = QScrollArea()
        axes_scroll.setWidgetResizable(True)
        axes_scroll.setWidget(self.axes_group)
        root.addWidget(axes_scroll, 1)

        state_group = QGroupBox("Botões e hats")
        state_layout = QVBoxLayout(state_group)
        self.buttons_label = QLabel("Botões pressionados: —")
        self.buttons_label.setWordWrap(True)
        self.hats_label = QLabel("Hats: —")
        self.hats_label.setWordWrap(True)
        state_layout.addWidget(self.buttons_label)
        state_layout.addWidget(self.hats_label)
        root.addWidget(state_group)

        capture_row = QHBoxLayout()
        self.record_button = QPushButton("Escolher arquivo e gravar")
        self.record_button.clicked.connect(lambda: self.start_recording())
        capture_row.addWidget(self.record_button)
        self.stop_button = QPushButton("Parar gravação")
        self.stop_button.clicked.connect(lambda: self.stop_recording())
        self.stop_button.setEnabled(False)
        capture_row.addWidget(self.stop_button)
        capture_row.addStretch(1)
        self.rate_label = QLabel("Taxa observada: —")
        capture_row.addWidget(self.rate_label)
        root.addLayout(capture_row)

        self.path_label = QLabel("Arquivo: nenhum")
        self.path_label.setWordWrap(True)
        root.addWidget(self.path_label)

        self.status_label = QLabel("Pronto")
        root.addWidget(self.status_label)
        self.setCentralWidget(central)

    def refresh_devices(self) -> None:
        if self._writer is not None:
            QMessageBox.information(
                self,
                "Gravação em andamento",
                "Pare a gravação antes de atualizar os dispositivos.",
            )
            return

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self._joysticks.clear()
        self._joystick = None

        pygame.joystick.quit()
        pygame.init()
        pygame.joystick.init()
        for index in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(index)
            joystick.init()
            self._joysticks.append(joystick)
            self.device_combo.addItem(f"{index}: {joystick.get_name()}")

        self.device_combo.blockSignals(False)
        if self._joysticks:
            self.device_combo.setCurrentIndex(0)
            self._select_device(0)
            self.status_label.setText(f"{len(self._joysticks)} dispositivo(s) detectado(s)")
        else:
            self._rebuild_axis_rows(0)
            self.device_details.setText("Nenhum dispositivo detectado")
            self.status_label.setText("Conecte o G29 e clique em Atualizar dispositivos")
        self._update_actions()

    def _select_device(self, index: int) -> None:
        if not 0 <= index < len(self._joysticks):
            self._joystick = None
            self._rebuild_axis_rows(0)
            self._update_actions()
            return

        self._joystick = self._joysticks[index]
        self._rebuild_axis_rows(self._joystick.get_numaxes())
        self.device_details.setText(
            f"Nome: {self._joystick.get_name()} | GUID: {self._safe_guid()} | "
            f"Eixos: {self._joystick.get_numaxes()} | "
            f"Botões: {self._joystick.get_numbuttons()} | "
            f"Hats: {self._joystick.get_numhats()}"
        )
        self._update_actions()

    def _rebuild_axis_rows(self, count: int) -> None:
        while self.axes_layout.count():
            item = self.axes_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._axis_rows = []
        device_name = self._joystick.get_name() if self._joystick is not None else ""
        known_profile = is_observed_g29_profile(device_name, count)
        self.axes_group.setTitle(
            "Eixos normalizados e valores brutos" if known_profile else "Eixos brutos"
        )
        for index in range(count):
            descriptor = G29_AXIS_DESCRIPTORS.get(index) if known_profile else None
            row = AxisRow(index, descriptor)
            self._axis_rows.append(row)
            self.axes_layout.addWidget(row.label, index, 0)
            self.axes_layout.addWidget(row.bar, index, 1)
            self.axes_layout.addWidget(row.value, index, 2)

        if count == 0:
            self.axes_layout.addWidget(QLabel("Nenhum eixo disponível"), 0, 0, 1, 3)

    def _poll_device(self) -> None:
        if self._joystick is None:
            return

        try:
            events = pygame.event.get()
            current_instance_id = self._safe_instance_id()
            for event in events:
                if (
                    event.type == pygame.JOYDEVICEREMOVED
                    and getattr(event, "instance_id", None) == current_instance_id
                ):
                    self._handle_device_error("O dispositivo foi desconectado")
                    return
            axes = [
                self._joystick.get_axis(index)
                for index in range(self._joystick.get_numaxes())
            ]
            buttons = [
                self._joystick.get_button(index)
                for index in range(self._joystick.get_numbuttons())
            ]
            hats = [
                self._joystick.get_hat(index)
                for index in range(self._joystick.get_numhats())
            ]
        except pygame.error as error:
            self._handle_device_error(str(error))
            return

        for row, value in zip(self._axis_rows, axes, strict=False):
            row.update(value)

        pressed = [str(index) for index, value in enumerate(buttons) if value]
        self.buttons_label.setText(
            "Botões pressionados: " + (", ".join(pressed) if pressed else "—")
        )
        self.hats_label.setText(
            "Hats: " + (", ".join(f"{index}={hat}" for index, hat in enumerate(hats)) if hats else "—")
        )

        if self._writer is not None:
            self._writer.sample(axes, buttons, hats)
            now_ns = self._writer.elapsed_ns
            self._recent_ticks.append(now_ns)
            cutoff = max(0, now_ns - 1_000_000_000)
            while self._recent_ticks and self._recent_ticks[0] < cutoff:
                self._recent_ticks.popleft()
            self.rate_label.setText(
                f"Taxa observada: {len(self._recent_ticks)} Hz | "
                f"Amostras: {self._writer.sample_count}"
            )

    def start_recording(self) -> None:
        if self._joystick is None or self._writer is not None:
            return

        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        default_path = str(Path(documents) / suggested_filename())
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar captura do G29",
            default_path,
            "JSON Lines (*.jsonl)",
        )
        if not selected:
            return

        path = Path(selected)
        if path.suffix.lower() != ".jsonl":
            path = path.with_suffix(".jsonl")

        try:
            self._writer = CaptureWriter(
                path,
                self._capture_metadata(),
                target_hz=TARGET_HZ,
                flush_every=TARGET_HZ,
            ).open()
        except OSError as error:
            self._writer = None
            QMessageBox.critical(self, "Não foi possível salvar", str(error))
            return

        self._last_capture_path = path
        self._recent_ticks.clear()
        self.path_label.setText(f"Arquivo: {path}")
        self.status_label.setText("Gravando dados brutos...")
        self._update_actions()

    def stop_recording(self, reason: str = "user_stopped") -> None:
        if self._writer is None:
            return

        writer = self._writer
        self._writer = None
        try:
            summary = writer.close(reason=reason)
            self.status_label.setText(
                f"Gravação concluída: {summary.get('sample_count', 0)} amostras, "
                f"{summary.get('observed_hz', 0)} Hz"
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "Erro ao finalizar o arquivo",
                f"A captura pode estar incompleta: {error}",
            )
        self._recent_ticks.clear()
        self._update_actions()

    def _capture_metadata(self) -> dict[str, Any]:
        assert self._joystick is not None
        return {
            "app": {
                "name": "Pilotagem Virtual G29 Hardware Spike",
                "version": __version__,
            },
            "runtime": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "pygame": pygame.version.ver,
                "sdl": list(pygame.get_sdl_version()),
            },
            "device": {
                "name": self._joystick.get_name(),
                "guid": self._safe_guid(),
                "instance_id": self._safe_instance_id(),
                "axis_count": self._joystick.get_numaxes(),
                "button_count": self._joystick.get_numbuttons(),
                "hat_count": self._joystick.get_numhats(),
            },
            "capture_instructions": {
                "axes_are_raw": True,
                "expected_actions": [
                    "wheel_full_left_and_right",
                    "accelerator_individual",
                    "brake_individual",
                    "clutch_individual",
                    "accelerator_and_brake_together",
                    "all_buttons",
                ],
            },
        }

    def _safe_guid(self) -> str:
        try:
            return self._joystick.get_guid() if self._joystick is not None else ""
        except (AttributeError, pygame.error):
            return "unavailable"

    def _safe_instance_id(self) -> int | None:
        try:
            return self._joystick.get_instance_id() if self._joystick is not None else None
        except (AttributeError, pygame.error):
            return None

    def _handle_device_error(self, message: str) -> None:
        if self._writer is not None:
            self.stop_recording(reason="device_error")
        self.status_label.setText(f"Erro do dispositivo: {message}")
        self._joystick = None
        self._update_actions()

    def _update_actions(self) -> None:
        recording = self._writer is not None
        self.record_button.setEnabled(self._joystick is not None and not recording)
        self.stop_button.setEnabled(recording)
        self.refresh_button.setEnabled(not recording)
        self.device_combo.setEnabled(not recording)

    def closeEvent(self, event: Any) -> None:
        if self._writer is not None:
            self.stop_recording(reason="application_closed")
        self._timer.stop()
        pygame.joystick.quit()
        pygame.quit()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pilotagem Virtual G29 Spike")
    app.setOrganizationName("Pilotagem Virtual")
    window = HardwareSpikeWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
