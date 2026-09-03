import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import time
import threading

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pilotagem_virtual.acquisition_probe import ProbeConfig, ProbeSampler, ProbeWindow
from pilotagem_virtual.input.device import DeviceInfo, RawInputState


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def skip_preparation_in_lifecycle_tests(monkeypatch):
    # Dedicated countdown tests below use the real three-second preparation.
    monkeypatch.setattr("pilotagem_virtual.acquisition_probe.COUNTDOWN_SECONDS", 0)


def wait_finished(window):
    deadline = time.monotonic() + 5
    while window.worker is not None or window.thread is not None:
        assert time.monotonic() < deadline, "Aquisição não encerrou"
        QTest.qWait(5)


@pytest.mark.parametrize("context", ["main", "worker"])
def test_probe_closes_owner_and_keeps_original_timestamps(app, tmp_path, context):
    output = tmp_path / "probe.json"
    window = ProbeWindow(ProbeConfig(context=context, duration_seconds=.12), output)
    window.show()
    window.start_run()
    wait_finished(window)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["reason"] == "completed"
    assert len(report["samples"]) == report["acquisition"]["sample_count"] > 0
    times = [s["timestamp_ns"] for s in report["samples"]]
    assert all(b > a for a, b in zip(times, times[1:]))
    assert all(0 <= t - report["origin_ns"] < report["duration_ns"] for t in times)
    assert (report["metadata"]["owner_thread"] == threading.get_ident()) == (context == "main")
    assert report["ui"]["main_thread"] == threading.get_ident()
    assert window.worker is None and window.thread is None
    window.close()


@pytest.mark.parametrize("context", ["main", "worker"])
def test_probe_cancel_and_close_are_safe(app, context):
    window = ProbeWindow(ProbeConfig(context=context))
    window.show()
    window.start_run()
    QTest.qWait(25)
    window.close()
    wait_finished(window)
    assert window.report["reason"] == "application_closed"
    assert not window.render_timer.isActive()


def test_thirty_worker_runs_do_not_keep_workers_or_previous_data(app):
    window = ProbeWindow(ProbeConfig(context="worker", duration_seconds=.025, drawing=False))
    results = []
    window.run_finished.connect(results.append)
    for _ in range(30):
        window.start_run()
        wait_finished(window)
        assert window.start_button.isEnabled()
        assert window.worker is None and window.thread is None
    assert len(results) == 30
    assert all(r["reason"] == "completed" for r in results)
    assert len({r["origin_ns"] for r in results}) == 30
    assert all(len(r["samples"]) < 10 for r in results)
    window.close()


def test_g29_backend_lifecycle_stays_in_worker_with_stubbed_hardware(app, monkeypatch):
    calls = []
    class Backend:
        def __init__(self): calls.append(("init", threading.get_ident()))
        def list_devices(self):
            calls.append(("list", threading.get_ident()))
            return [DeviceInfo("g29:1", "G29", "guid", 4, 0, 0, 1)]
        def open_device(self, device_id):
            calls.append(("open", threading.get_ident()))
            return self
        def poll(self):
            calls.append(("poll", threading.get_ident()))
            return RawInputState(time.perf_counter_ns(), (0, 1, 0, 1), (), ())
        def close(self): calls.append(("close", threading.get_ident()))
    monkeypatch.setattr("pilotagem_virtual.acquisition_probe.PygameInputBackend", Backend)
    window = ProbeWindow(ProbeConfig(source="g29", context="worker", duration_seconds=.06))
    window.start_run()
    wait_finished(window)
    assert window.report["reason"] == "completed"
    assert calls[0][0] == "init" and calls[-1][0] == "close"
    assert {name for name, _ in calls} == {"init", "list", "open", "poll", "close"}
    assert len({owner for _, owner in calls}) == 1
    assert calls[0][1] != threading.get_ident()
    window.close()


def install_initializing_backend(monkeypatch, pending=3, disconnect_at=None):
    instances = []

    class Backend:
        def __init__(self):
            self.polls = 0
            self.owners = [threading.get_ident()]
            self.closed = False
            instances.append(self)

        def list_devices(self):
            self.owners.append(threading.get_ident())
            return [DeviceInfo(f"g29:{len(instances)}", "G29", "guid", 4, 0, 0, len(instances))]

        def open_device(self, device_id):
            self.owners.append(threading.get_ident())
            return self

        def poll(self):
            assert not self.closed
            self.owners.append(threading.get_ident())
            self.polls += 1
            if disconnect_at == self.polls and len(instances) == 1:
                return RawInputState(time.perf_counter_ns(), (), (), (), False)
            # Both the uninitialized state and a legitimate initialized state
            # contain zeros. Readiness must come from flags, never amplitudes.
            return RawInputState(time.perf_counter_ns(), (0.,) * 4, (), (),
                                 initialized_axes=(self.polls > pending,) * 4)

        def close(self):
            assert not self.closed
            self.owners.append(threading.get_ident())
            self.closed = True

    monkeypatch.setattr("pilotagem_virtual.acquisition_probe.PygameInputBackend", Backend)
    return instances


@pytest.mark.parametrize("context", ["main", "worker"])
def test_initialization_is_preserved_outside_capture_and_zero_can_be_ready(app, monkeypatch, tmp_path, context):
    instances = install_initializing_backend(monkeypatch)
    window = ProbeWindow(ProbeConfig(source="g29", context=context, duration_seconds=.06), output_dir=tmp_path)
    window.start_run()
    wait_finished(window)
    report = json.loads(next(tmp_path.glob('*.json')).read_text(encoding="utf-8"))
    assert report["reason"] == "completed"
    assert len(report["initialization"]["samples"]) == 3
    assert all(s["timestamp_ns"] < report["origin_ns"] for s in report["initialization"]["samples"])
    assert report["samples"][0]["timestamp_ns"] == report["origin_ns"]
    assert all(s["axes"] == [0.] * 4 and all(s["initialized_axes"]) for s in report["samples"])
    assert report["acquisition"]["sample_count"] == len(report["samples"])
    assert report["lifecycle"][-2]["event"] == "backend_closed"
    assert report["lifecycle"][-1]["event"] == "context_finished"
    assert len(set(instances[0].owners)) == 1 and instances[0].closed
    window.close()


@pytest.mark.parametrize("context", ["main", "worker"])
def test_initialization_timeout_saves_pending_data_without_fake_attempt(app, monkeypatch, tmp_path, context):
    install_initializing_backend(monkeypatch, pending=10000)
    window = ProbeWindow(ProbeConfig(source="g29", context=context, initialization_timeout_seconds=.03), output_dir=tmp_path)
    window.start_run()
    wait_finished(window)
    assert window.report["reason"] == "initialization_timeout"
    assert window.report["origin_ns"] is None and window.report["duration_ns"] == 0
    assert window.report["acquisition"] is None
    assert not window.report["samples"] and window.report["initialization"]["samples"]
    assert len(list(tmp_path.glob('*.json'))) == 1
    window.close()


@pytest.mark.parametrize("context", ["main", "worker"])
def test_cancel_then_close_during_initialization_save_distinct_reports(app, monkeypatch, tmp_path, context):
    instances = install_initializing_backend(monkeypatch, pending=10000)
    window = ProbeWindow(ProbeConfig(source="g29", context=context), output_dir=tmp_path)
    window.show()
    window.start_run()
    QTest.qWait(30)
    window.stop_button.click()
    wait_finished(window)
    first_id = window.report["run_id"]
    assert window.report["reason"] == "cancelled"
    window.start_run()
    QTest.qWait(30)
    window.close()
    wait_finished(window)
    assert window.report["run_id"] != first_id
    assert window.report["reason"] == "application_closed"
    assert not window.isVisible()
    assert len(list(tmp_path.glob('*.json'))) == 2
    assert all(i.closed and len(set(i.owners)) == 1 for i in instances)


@pytest.mark.parametrize("context", ["main", "worker"])
@pytest.mark.parametrize("disconnect_at", [2, 6])
def test_disconnect_during_initialization_or_capture_can_start_new_run(app, monkeypatch, tmp_path, context, disconnect_at):
    instances = install_initializing_backend(monkeypatch, disconnect_at=disconnect_at)
    window = ProbeWindow(ProbeConfig(source="g29", context=context, duration_seconds=.06), output_dir=tmp_path)
    window.start_run()
    wait_finished(window)
    first = window.report
    assert first["reason"] == "disconnected"
    assert first["terminal_reading"]["connected"] is False
    assert bool(first["samples"]) == (disconnect_at > 3)
    window.start_run()
    wait_finished(window)
    assert window.report["reason"] == "completed"
    assert first["run_id"] != window.report["run_id"]
    assert len(list(tmp_path.glob('*.json'))) == 2
    assert all(i.closed and len(set(i.owners)) == 1 for i in instances)
    window.close()


def test_failed_autosave_keeps_manual_window_open_on_close(app, monkeypatch, tmp_path):
    install_initializing_backend(monkeypatch, pending=10000)
    invalid_directory = tmp_path / "file-instead-of-directory"
    invalid_directory.write_text("existing file")
    window = ProbeWindow(ProbeConfig(source="g29", context="worker"), output_dir=invalid_directory)
    window.show()
    window.start_run()
    QTest.qWait(30)
    window.close()
    wait_finished(window)
    assert window.save_failed and window.isVisible()
    assert window.report and window.save_button.isEnabled()
    assert window._write(tmp_path / "manual-recovery.json")
    window.close()


def test_resize_is_recorded_during_worker_capture(app, tmp_path):
    window = ProbeWindow(ProbeConfig(context="worker", duration_seconds=.15), output_dir=tmp_path)
    window.show()
    window.start_run()
    QTest.qWait(30)
    window.resize(1440, 900)
    actual_width = window.width()
    wait_finished(window)
    assert window.report["reason"] == "completed"
    assert any(e["width"] == actual_width and e["height"] == 900 for e in window.report["ui"]["resize_events"])
    window.close()


@pytest.mark.parametrize("context,drawing", [("main", True), ("worker", False)])
def test_visible_three_second_countdown_precedes_full_capture(app, monkeypatch, context, drawing):
    monkeypatch.setattr("pilotagem_virtual.acquisition_probe.COUNTDOWN_SECONDS", 3)
    window = ProbeWindow(ProbeConfig(context=context, duration_seconds=.08, drawing=drawing))
    window.show()
    observed = []
    window.start_run()
    window.worker.countdown_changed.connect(lambda value: observed.append((value, window.countdown_label.isVisible())))
    wait_finished(window)
    report = window.report
    assert report["reason"] == "completed"
    assert observed == [(3, True), (2, True), (1, True), (0, True)]
    displays = report["ui"]["countdown_displays"]
    assert [d["value"] for d in displays] == [3, 2, 1, 0]
    assert report["countdown"]["started_ns"] >= displays[0]["timestamp_ns"]
    assert report["origin_ns"] - report["countdown"]["started_ns"] >= 3_000_000_000
    assert report["duration_ns"] == 80_000_000
    assert report["samples"][0]["timestamp_ns"] == report["origin_ns"]
    assert all(s["timestamp_ns"] < report["origin_ns"] for s in report["countdown"]["samples"])
    assert report["acquisition"]["sample_count"] == len(report["samples"])
    assert window.countdown_label.text() == "CONCLUÍDO"
    window.close()


def test_countdown_waits_for_gui_ack_and_uses_real_poll_boundaries(app, monkeypatch):
    monkeypatch.setattr("pilotagem_virtual.acquisition_probe.COUNTDOWN_SECONDS", 3)
    now = 10_000_000_000
    sampler = ProbeSampler(ProbeConfig(), clock_ns=lambda: now)
    displayed = []
    reports = []
    sampler.countdown_changed.connect(displayed.append)
    sampler.finished.connect(reports.append)
    sampler.start()
    sampler._poll()
    # Even a GUI delayed for four seconds must get three full seconds after ack.
    now += 4_000_000_000
    sampler._poll()
    assert sampler.origin_ns is None and displayed == [3]
    sampler.begin_countdown()
    for elapsed, expected in [(999_999_999, 3), (1_000_000_000, 2), (2_000_000_000, 1), (2_999_999_999, 1)]:
        now = sampler.countdown_started_ns + elapsed
        sampler._poll()
        assert displayed[-1] == expected and sampler.origin_ns is None
    now += 1
    sampler._poll()
    assert displayed == [3, 2, 1, 0]
    assert sampler.origin_ns == now
    assert [s.timestamp_ns for s in sampler.readings] == [now]
    sampler.stop()
    assert reports[0]["initialization"]["wait_ms"] == 0
    sampler.deleteLater()


@pytest.mark.parametrize("context", ["main", "worker"])
def test_cancel_and_close_during_countdown_restart_without_attempt(app, monkeypatch, tmp_path, context):
    monkeypatch.setattr("pilotagem_virtual.acquisition_probe.COUNTDOWN_SECONDS", 3)
    window = ProbeWindow(ProbeConfig(context=context), output_dir=tmp_path)
    window.show()
    for reason in ("cancelled", "application_closed"):
        window.start_run()
        deadline = time.monotonic() + 2
        while window.countdown_label.text() != "3":
            assert time.monotonic() < deadline
            QTest.qWait(5)
        if reason == "cancelled":
            window.stop_button.click()
        else:
            window.close()
        wait_finished(window)
        assert window.report["reason"] == reason
        assert window.report["origin_ns"] is None and window.report["acquisition"] is None
        assert not window.report["samples"]
        assert window.report["countdown"]["samples"]
        assert [d["value"] for d in window.report["ui"]["countdown_displays"]] == [3]
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert not window.isVisible()


@pytest.mark.parametrize("context", ["main", "worker"])
def test_disconnect_during_countdown_preserves_preparation(app, monkeypatch, context):
    monkeypatch.setattr("pilotagem_virtual.acquisition_probe.COUNTDOWN_SECONDS", 3)
    instances = install_initializing_backend(monkeypatch, pending=1, disconnect_at=5)
    window = ProbeWindow(ProbeConfig(source="g29", context=context))
    window.show()
    window.start_run()
    wait_finished(window)
    assert window.report["reason"] == "disconnected"
    assert window.report["origin_ns"] is None and window.report["acquisition"] is None
    assert len(window.report["initialization"]["samples"]) == 1
    assert len(window.report["countdown"]["samples"]) == 3
    assert not window.report["samples"] and instances[0].closed
    assert window.countdown_label.text() == "DESCONECTADO"
    window.close()
