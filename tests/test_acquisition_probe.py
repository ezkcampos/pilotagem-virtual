import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import time
import threading

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pilotagem_virtual.acquisition_probe import ProbeConfig, ProbeWindow
from pilotagem_virtual.input.device import DeviceInfo, RawInputState


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


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
    assert window.report["reason"] == "cancelled"
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
