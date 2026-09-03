"""Isolated P0 experiment; never enables the SDL worker in the trainer."""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import threading
import time
import uuid
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
    initialization_timeout_seconds: float = 10.0

    def __post_init__(self):
        if self.source not in {"fake", "g29"} or self.context not in {"main", "worker"}:
            raise ValueError("Fonte ou contexto inválido")
        if not math.isfinite(self.duration_seconds) or not 0 < self.duration_seconds <= 60:
            raise ValueError("Duração deve estar entre 0 e 60 segundos")
        if not math.isfinite(self.initialization_timeout_seconds) or not 0 < self.initialization_timeout_seconds <= 60:
            raise ValueError("Prazo de inicialização deve estar entre 0 e 60 segundos")


class ProbeSampler(QObject):
    latest = Signal(object)
    finished = Signal(object)
    phase_changed = Signal(str)

    def __init__(self, config: ProbeConfig):
        super().__init__()
        self.config = config
        self.backend = None
        self.device = None
        self.timer = None
        self.run_id = uuid.uuid4().hex
        self.origin_ns = None
        self.opened_ns = None
        self.initialization_readings: list[RawInputState] = []
        self.terminal_reading = None
        self.lifecycle = []
        self._last_timestamp_ns = None
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
        self._event("started")
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
                    readiness_api="SDL_JoystickGetAxisInitialState",
                )
            self.opened_ns = time.perf_counter_ns()
            self._event("source_opened")
            self.phase_changed.emit("Aguardando primeira leitura do G29. Mova e solte os pedais." if self.device else "Preparando fonte sintética…")
            self.timer = QTimer(self)
            self.timer.setTimerType(Qt.TimerType.PreciseTimer)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self._poll)
            self.timer.start(0)
        except Exception as error:
            self._finish("error", str(error))

    @Slot(str)
    def stop(self, reason="cancelled"):
        self._finish(reason)

    def _event(self, name):
        self.lifecycle.append({"event": name, "timestamp_ns": time.perf_counter_ns(), "owner_thread": threading.get_ident()})

    @Slot()
    def _poll(self):
        if self._done:
            return
        try:
            if self.device is not None:
                raw = self.device.poll()
            else:
                now = time.perf_counter_ns()
                elapsed = (now - self.opened_ns) / 1e9
                # A labelled synthetic source; timestamps still measure real polls.
                brake = .5 + .4 * math.sin(elapsed * 2)
                raw = RawInputState(now, (0., 1., 1 - 2 * brake, 1.), (), ())
            if not raw.connected:
                self.terminal_reading = raw
                self._finish("disconnected")
                return
            if len(raw.axes) < 4 or not all(math.isfinite(v) and -1 <= v <= 1 for v in raw.axes):
                self.terminal_reading = raw
                self._finish("error", "Leitura contém eixos ausentes, não finitos ou fora da faixa")
                return
            if self._last_timestamp_ns is not None and raw.timestamp_ns <= self._last_timestamp_ns:
                self.terminal_reading = raw
                self._finish("error", "Timestamp da leitura não é crescente")
                return
            self._last_timestamp_ns = raw.timestamp_ns
            if self.origin_ns is None:
                if raw.timestamp_ns - self.opened_ns >= round(self.config.initialization_timeout_seconds * 1e9):
                    self.initialization_readings.append(raw)
                    self._finish("initialization_timeout", "O G29 não confirmou o estado inicial no prazo. Detecte novamente e mova os pedais.")
                    return
                if not raw.ready:
                    self.initialization_readings.append(raw)
                    self.timer.start(8)
                    return
                self.origin_ns = raw.timestamp_ns
                self._event("input_ready")
                self.phase_changed.emit("Medindo G29 real…" if self.device else "Medindo fonte sintética…")
            elif not raw.ready:
                self.terminal_reading = raw
                self._finish("error", "Estado inicial do dispositivo deixou de estar disponível")
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
        self._event(reason)
        if self.timer:
            self.timer.stop()
        if self.backend:
            try:
                self.backend.close()
                self._event("backend_closed")
            except Exception as close_error:
                reason, error = "error", str(close_error)
                self._event("backend_close_failed")
        target_duration = round(self.config.duration_seconds * 1e9)
        duration = 0 if self.origin_ns is None else (
            target_duration if reason == "completed" else max(1, min(target_duration, finished_ns - self.origin_ns))
        )
        report = summarize_acquisition([r.timestamp_ns - self.origin_ns for r in self.readings], duration) if duration else None
        payload = {
            "schema_version": "acquisition-probe-v2", "app_version": __version__,
            "run_id": self.run_id,
            "kind": "development-P0", "config": asdict(self.config),
            "reason": reason, "error": error, "metadata": self.metadata,
            "origin_ns": self.origin_ns, "finished_ns": finished_ns,
            "duration_ns": duration, "acquisition": asdict(report) if report else None,
            "initialization": {
                "opened_ns": self.opened_ns, "ready_ns": self.origin_ns,
                "wait_ms": ((self.origin_ns or finished_ns) - self.opened_ns) / 1e6 if self.opened_ns else None,
                "samples": [asdict(r) for r in self.initialization_readings],
            },
            "lifecycle": self.lifecycle.copy(),
            "terminal_reading": asdict(self.terminal_reading) if self.terminal_reading else None,
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
    stop_requested = Signal(str)
    run_finished = Signal(object)

    def __init__(self, config: ProbeConfig, output: Path | None = None, automatic=False, output_dir: Path | None = None):
        super().__init__()
        self.setWindowTitle("Pilotagem Virtual — Experimento de aquisição P0")
        self.config, self.output, self.automatic = config, output, automatic
        self.output_dir = output_dir
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
        self.stop_button.clicked.connect(lambda: self.stop_requested.emit("cancelled"))
        self.save_button.clicked.connect(self.save_report)
        for widget in (self.source, self.context, self.drawing, self.start_button, self.stop_button, self.save_button):
            row.addWidget(widget)
        root.addLayout(row)
        self.canvas = ProbeCanvas()
        root.addWidget(self.canvas, 1)
        self.status = QLabel(f"Relatórios automáticos em: {output_dir}" if output_dir else "Pronto. Cada medição usa timestamps reais; a fonte sintética não mede o G29.")
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
        self.save_failed = False
        self.deliveries.clear()
        self.resize_events.clear()
        self.canvas.points.clear()
        self.canvas.frames.clear()
        self.canvas.paint_durations.clear()
        self.config = ProbeConfig(self.source.currentData(), self.context.currentData(), self.config.duration_seconds, self.drawing.isChecked(), self.config.device_id, self.config.initialization_timeout_seconds)
        self.canvas.drawing = self.config.drawing
        self.canvas.duration = self.config.duration_seconds
        self.canvas.recording = True
        self._set_running(True)
        self.status.setText("Medindo… fonte sintética" if self.config.source == "fake" else "Medindo G29 real…")
        self.worker = ProbeSampler(self.config)
        self.worker.latest.connect(self._latest)
        self.worker.finished.connect(self._finished)
        self.worker.phase_changed.connect(self.status.setText)
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
        frames = [t for t in self.canvas.frames if origin is not None and origin <= t < origin + report["duration_ns"]]
        report["ui"] = {
            "width": self.width(), "height": self.height(), "device_pixel_ratio": self.devicePixelRatioF(),
            "qt_platform": QApplication.platformName(), "drawn_frames": len(frames),
            "drawn_fps": len(frames) / duration if duration else 0, "delivery_p95_ms": self._p95(self.deliveries),
            "paint_p95_ms": self._p95([
                elapsed for stamp, elapsed in zip(self.canvas.frames, self.canvas.paint_durations)
                if origin is not None and origin <= stamp < origin + report["duration_ns"]
            ]), "resize_events": self.resize_events.copy(),
            "main_thread": threading.get_ident(),
        }
        build_info = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "resources/build-info.json"
        report["build"] = json.loads(build_info.read_text(encoding="utf-8-sig")) if build_info.exists() else {"commit": None}
        self.report = report
        data = report["acquisition"]
        detail = f"{data['sample_count']} leituras · {data['observed_hz']:.1f} Hz · {report['ui']['drawn_fps']:.1f} FPS desenhados" if data else "captura não iniciada"
        self.status.setText(f"{report['reason']} · {detail}. " + (report["error"] or "Relatório disponível."))
        self.canvas.update()
        if self.config.context == "main":
            self.stop_requested.disconnect(self.worker.stop)
            self.worker.deleteLater()
            self.worker = None
            self._ready()

    @Slot()
    def _thread_finished(self):
        if self.thread is None:
            return
        # finished can reach the GUI before native thread-local cleanup ends.
        # Keep Python/Qt wrappers alive until the OS thread has actually joined;
        # deleting them earlier can block the GUI while the worker needs the GIL.
        if not self.thread.wait(0):
            QTimer.singleShot(1, self._thread_finished)
            return
        self.thread.deleteLater()
        self.thread = None
        self.worker = None
        self._ready()

    def _ready(self):
        self.report["lifecycle"].append({"event": "context_finished", "timestamp_ns": time.perf_counter_ns(), "owner_thread": threading.get_ident()})
        self._set_running(False)
        output = self.output
        if self.output_dir:
            output = self.output_dir / f"p0-{self.config.context}-{'grafico' if self.config.drawing else 'sem-grafico'}-{self.report['run_id']}.json"
        if output:
            self.save_failed = not self._write(output)
            if not self.save_failed:
                self.status.setText(self.status.text() + f" Salvo em: {output}")
        self.run_finished.emit(self.report)
        if self.save_failed and self._closing and not self.automatic:
            self._closing = False
            self.status.setText(self.status.text() + " A janela ficou aberta para você salvar manualmente.")
        elif self.automatic or self._closing:
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
            self.stop_requested.emit("application_closed")
            # Main-thread cancellation can finish synchronously inside this
            # closeEvent. Qt ignores a recursive close(); accept the outer one.
            if self.worker is None and self.thread is None and self._closing:
                event.accept()
                super().closeEvent(event)
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
    parser.add_argument("--output-dir", type=Path, help="Salva cada execução, inclusive cancelamento/fechamento, em um arquivo próprio")
    parser.add_argument("--size", default="1920x1080")
    args = parser.parse_args(argv)
    app = QApplication.instance() or QApplication([sys.argv[0]])
    config = ProbeConfig(args.source, args.context, args.duration, not args.no_drawing, args.device_id)
    window = ProbeWindow(config, args.output, args.auto, args.output_dir)
    width, height = (int(v) for v in args.size.split("x"))
    window.resize(width, height)
    window.show()
    code = app.exec()
    if args.auto and (window.report is None or window.report["reason"] != "completed" or window.save_failed):
        return 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
