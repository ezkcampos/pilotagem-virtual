"""Isolated P0 experiment; never enables the SDL worker in the trainer."""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from pilotagem_virtual import __version__
from pilotagem_virtual.domain.acquisition import percentile, summarize_acquisition
from pilotagem_virtual.g29_axes import is_observed_g29_profile
from pilotagem_virtual.input.device import RawInputState
from pilotagem_virtual.input.pygame_device import PygameInputBackend


@dataclass(frozen=True)
class ProbeConfig:
    source: str = "fake"
    context: str = "main"
    duration_seconds: float = 10.0
    drawing: bool = True
    device_id: str | None = None

    def __post_init__(self):
        if self.source not in {"fake", "g29"} or self.context not in {"main", "worker"}:
            raise ValueError("Fonte ou contexto inválido")
        if not math.isfinite(self.duration_seconds) or not 0 < self.duration_seconds <= 60:
            raise ValueError("Duração deve estar entre 0 e 60 segundos")


class ProbeSampler(QObject):
    latest = Signal(object)
    finished = Signal(object)

    def __init__(self, config: ProbeConfig):
        super().__init__()
        self.config = config
        self.backend = None
        self.device = None
        self.timer = None
        self.origin_ns = 0
        self.readings: list[RawInputState] = []
        self.end_context = None
        self._done = False
        self._last_publication_ns = 0
        self.metadata = {}

    @Slot()
    def start(self):
        if self._done:
            return
        self.metadata = {
            "owner_thread": threading.get_ident(), "source": self.config.source,
            "requested_interval_ms": 8, "target_hz": 120,
        }
        try:
            if self.config.source == "g29":
                self.backend = PygameInputBackend()
                devices = [d for d in self.backend.list_devices() if is_observed_g29_profile(d.name, d.axis_count)]
                if self.config.device_id:
                    devices = [d for d in devices if d.device_id == self.config.device_id]
                if len(devices) != 1:
                    raise RuntimeError("É necessário um G29 compatível; para vários dispositivos, informe --device-id.")
                self.device = self.backend.open_device(devices[0].device_id)
                import pygame
                self.metadata.update(
                    device=asdict(devices[0]), pygame=pygame.version.ver,
                    sdl=list(pygame.get_sdl_version()), display_initialized=pygame.display.get_init(),
                    has_sdl_window=pygame.display.get_surface() is not None,
                )
            self.origin_ns = time.perf_counter_ns()
            self.timer = QTimer(self)
            self.timer.setTimerType(Qt.TimerType.PreciseTimer)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self._poll)
            self.timer.start(0)
        except Exception as error:
            self._finish("error", str(error))

    @Slot()
    def stop(self):
        self._finish("cancelled")

    @Slot()
    def _poll(self):
        if self._done:
            return
        try:
            if self.device is not None:
                raw = self.device.poll()
            else:
                now = time.perf_counter_ns()
                elapsed = (now - self.origin_ns) / 1e9
                # A labelled synthetic source; timestamps still measure real polls.
                brake = .5 + .4 * math.sin(elapsed * 2)
                raw = RawInputState(now, (0., 1., 1 - 2 * brake, 1.), (), ())
            if not raw.connected:
                self._finish("disconnected")
                return
            if len(raw.axes) < 4 or not all(math.isfinite(v) for v in raw.axes):
                self._finish("error", "Leitura contém eixos ausentes ou não finitos")
                return
            elapsed = raw.timestamp_ns - self.origin_ns
            if elapsed >= round(self.config.duration_seconds * 1e9):
                self.end_context = raw
                self._finish("completed")
                return
            self.readings.append(raw)
            if raw.timestamp_ns - self._last_publication_ns >= 16_000_000:
                self._last_publication_ns = raw.timestamp_ns
                self.latest.emit((elapsed, raw))
            # The proven spike cadence is the P0 baseline. A late callback waits
            # another 8 ms; it never emits a short burst to recover missed slots.
            self.timer.start(8)
        except Exception as error:
            self._finish("error", str(error))

    def _finish(self, reason: str, error: str | None = None):
        if self._done:
            return
        self._done = True
        finished_ns = time.perf_counter_ns()
        if self.timer:
            self.timer.stop()
        if self.backend:
            try:
                self.backend.close()
            except Exception as close_error:
                reason, error = "error", str(close_error)
        target_duration = round(self.config.duration_seconds * 1e9)
        duration = target_duration if reason == "completed" else max(1, min(target_duration, finished_ns - (self.origin_ns or finished_ns)))
        report = summarize_acquisition([r.timestamp_ns - self.origin_ns for r in self.readings], duration)
        payload = {
            "schema_version": "acquisition-probe-v1", "app_version": __version__,
            "kind": "development-P0", "config": asdict(self.config),
            "reason": reason, "error": error, "metadata": self.metadata,
            "origin_ns": self.origin_ns, "finished_ns": finished_ns,
            "duration_ns": duration, "acquisition": asdict(report),
            "samples": [asdict(r) for r in self.readings],
            "end_context": asdict(self.end_context) if self.end_context else None,
            "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        }
        self.finished.emit(payload)


class ProbeCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 320)
        self.points = []
        self.drawing = True
        self.recording = False
        self.duration = 10.0
        self.frames = []
        self.paint_durations = []

    def paintEvent(self, event):
        start = time.perf_counter_ns()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101716"))
        painter.setPen(QColor("#eee8dc"))
        painter.drawText(25, 30, "Entrada do freio (%) · carga visual experimental P0")
        if self.drawing:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for index in range(6):
                y = 60 + (self.height() - 100) * index / 5
                painter.setPen(QColor("#45504e"))
                painter.drawLine(QPointF(60, y), QPointF(self.width() - 30, y))
                painter.drawText(12, int(y), str(100 - index * 20))
            # Fixed-size synthetic reference supplies reproducible drawing load.
            reference = QPainterPath()
            for index in range(1200):
                x = 60 + (self.width() - 90) * index / 1199
                y = 60 + (self.height() - 100) * (.5 + .35 * math.sin(index / 150))
                reference.moveTo(x, y) if index == 0 else reference.lineTo(x, y)
            painter.setPen(QPen(QColor("#d3ab60"), 2, Qt.PenStyle.DashLine))
            painter.drawPath(reference)
            trace = QPainterPath()
            for index, (elapsed, value) in enumerate(self.points):
                x = 60 + (self.width() - 90) * min(1, elapsed / self.duration)
                y = 60 + (self.height() - 100) * (1 - value)
                trace.moveTo(x, y) if index == 0 else trace.lineTo(x, y)
            painter.setPen(QPen(QColor("#27c4df"), 3))
            painter.drawPath(trace)
            painter.drawText(65, self.height() - 15, "Tempo (s) · tracejado: carga sintética; contínuo: leitura visual")
        else:
            painter.drawText(25, 90, "Desenho desativado para comparação de aquisição.")
        painter.end()
        if self.recording:
            self.frames.append(start)
            self.paint_durations.append(time.perf_counter_ns() - start)


class ProbeWindow(QMainWindow):
    stop_requested = Signal()
    run_finished = Signal(object)

    def __init__(self, config: ProbeConfig, output: Path | None = None, automatic=False):
        super().__init__()
        self.setWindowTitle("Pilotagem Virtual — Experimento de aquisição P0")
        self.config, self.output, self.automatic = config, output, automatic
        self.report = None
        self.save_failed = False
        self.worker = None
        self.thread = None
        self._closing = False
        self.deliveries = []
        self.resize_events = []
        root_widget = QWidget()
        root = QVBoxLayout(root_widget)
        title = QLabel("Experimento P0 · não é uma validação automática do G29")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        root.addWidget(title)
        instructions = QLabel("Compare as duas threads, com e sem desenho. Durante a captura, mova os pedais e redimensione a janela. Feche o treinador e o diagnóstico antes de medir o G29.")
        instructions.setWordWrap(True)
        root.addWidget(instructions)
        row = QHBoxLayout()
        self.source = QComboBox()
        self.source.addItem("Fonte sintética (sem hardware)", "fake")
        self.source.addItem("Logitech G29 real", "g29")
        self.source.setCurrentIndex(self.source.findData(config.source))
        self.context = QComboBox()
        self.context.addItem("Thread principal", "main")
        self.context.addItem("Worker experimental", "worker")
        self.context.setCurrentIndex(self.context.findData(config.context))
        self.drawing = QCheckBox("Desenhar gráfico")
        self.drawing.setChecked(config.drawing)
        self.start_button = QPushButton("Iniciar medição")
        self.stop_button = QPushButton("Cancelar")
        self.stop_button.setEnabled(False)
        self.save_button = QPushButton("Salvar relatório JSON")
        self.save_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_run)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.save_button.clicked.connect(self.save_report)
        for widget in (self.source, self.context, self.drawing, self.start_button, self.stop_button, self.save_button):
            row.addWidget(widget)
        root.addLayout(row)
        self.canvas = ProbeCanvas()
        root.addWidget(self.canvas, 1)
        self.status = QLabel("Pronto. Cada medição usa timestamps reais; a fonte sintética não mede o G29.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.setCentralWidget(root_widget)
        self.render_timer = QTimer(self)
        self.render_timer.setInterval(17)
        self.render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.render_timer.timeout.connect(self.canvas.update)
        self.resize(1280, 760)
        if automatic:
            QTimer.singleShot(0, self.start_run)

    @Slot()
    def start_run(self):
        if self.worker is not None or self.thread is not None:
            return
        self.report = None
        self.deliveries.clear()
        self.resize_events.clear()
        self.canvas.points.clear()
        self.canvas.frames.clear()
        self.canvas.paint_durations.clear()
        self.config = ProbeConfig(self.source.currentData(), self.context.currentData(), self.config.duration_seconds, self.drawing.isChecked(), self.config.device_id)
        self.canvas.drawing = self.config.drawing
        self.canvas.duration = self.config.duration_seconds
        self.canvas.recording = True
        self._set_running(True)
        self.status.setText("Medindo… fonte sintética" if self.config.source == "fake" else "Medindo G29 real…")
        self.worker = ProbeSampler(self.config)
        self.worker.latest.connect(self._latest)
        self.worker.finished.connect(self._finished)
        self.stop_requested.connect(self.worker.stop)
        if self.config.context == "worker":
            self.thread = QThread(self)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.start)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self._thread_finished)
            self.thread.start()
        else:
            QTimer.singleShot(0, self.worker.start)
        if self.config.drawing:
            self.render_timer.start()

    @Slot(object)
    def _latest(self, item):
        elapsed, raw = item
        self.deliveries.append(time.perf_counter_ns() - raw.timestamp_ns)
        self.canvas.points.append((elapsed / 1e9, max(0, min(1, (1 - raw.axes[2]) / 2))))

    @Slot(object)
    def _finished(self, report):
        self.canvas.recording = False
        self.render_timer.stop()
        duration = report["duration_ns"] / 1e9
        origin = report["origin_ns"]
        frames = [t for t in self.canvas.frames if origin <= t < origin + report["duration_ns"]]
        report["ui"] = {
            "width": self.width(), "height": self.height(), "device_pixel_ratio": self.devicePixelRatioF(),
            "qt_platform": QApplication.platformName(), "drawn_frames": len(frames),
            "drawn_fps": len(frames) / duration, "delivery_p95_ms": self._p95(self.deliveries),
            "paint_p95_ms": self._p95(self.canvas.paint_durations), "resize_events": self.resize_events.copy(),
            "main_thread": threading.get_ident(),
        }
        build_info = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "resources/build-info.json"
        report["build"] = json.loads(build_info.read_text(encoding="utf-8-sig")) if build_info.exists() else {"commit": None}
        self.report = report
        data = report["acquisition"]
        self.status.setText(f"{report['reason']} · {data['sample_count']} leituras · {data['observed_hz']:.1f} Hz · {report['ui']['drawn_fps']:.1f} FPS desenhados. " + (report["error"] or "Salve o relatório para analisar intervalos e lacunas."))
        self.canvas.update()
        if self.config.context == "main":
            self.stop_requested.disconnect(self.worker.stop)
            self.worker.deleteLater()
            self.worker = None
            self._ready()

    @Slot()
    def _thread_finished(self):
        self.thread.deleteLater()
        self.thread = None
        self.worker = None
        self._ready()

    def _ready(self):
        self._set_running(False)
        if self.output:
            self.save_failed = not self._write(self.output)
        self.run_finished.emit(self.report)
        if self.automatic or self._closing:
            self.close()

    def _set_running(self, running):
        for widget in (self.source, self.context, self.drawing, self.start_button):
            widget.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.save_button.setEnabled(not running and self.report is not None)

    @staticmethod
    def _p95(values):
        result = percentile(values, .95)
        return None if result is None else result / 1e6

    def _write(self, path):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as error:
            self.status.setText(f"Não foi possível salvar; relatório continua em memória: {error}")
            return False
        return True

    @Slot()
    def save_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar medição P0", "medicao-p0.json", "JSON (*.json)")
        if path:
            self._write(Path(path))

    def resizeEvent(self, event):
        if self.worker is not None:
            self.resize_events.append({"timestamp_ns": time.perf_counter_ns(), "width": event.size().width(), "height": event.size().height()})
        super().resizeEvent(event)

    def closeEvent(self, event):
        if self.worker is not None or self.thread is not None:
            self._closing = True
            event.ignore()
            self.stop_requested.emit()
            return
        self.render_timer.stop()
        super().closeEvent(event)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Experimento de aquisição P0")
    parser.add_argument("--source", choices=["fake", "g29"], default="fake")
    parser.add_argument("--context", choices=["main", "worker"], default="main")
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--no-drawing", action="store_true")
    parser.add_argument("--device-id")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--size", default="1920x1080")
    args = parser.parse_args(argv)
    app = QApplication.instance() or QApplication([sys.argv[0]])
    config = ProbeConfig(args.source, args.context, args.duration, not args.no_drawing, args.device_id)
    window = ProbeWindow(config, args.output, args.auto)
    width, height = (int(v) for v in args.size.split("x"))
    window.resize(width, height)
    window.show()
    code = app.exec()
    if args.auto and (window.report is None or window.report["reason"] != "completed" or window.save_failed):
        return 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
