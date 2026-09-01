from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from pilotagem_virtual.spike_capture import (
    SCHEMA_VERSION,
    CaptureWriter,
    suggested_filename,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 1_000_000_000

    def __call__(self) -> int:
        return self.value

    def advance(self, nanoseconds: int) -> None:
        self.value += nanoseconds


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_suggested_filename_is_stable_and_uses_jsonl() -> None:
    instant = datetime(2026, 9, 1, 20, 30, 45, tzinfo=UTC)
    assert suggested_filename(instant) == "g29-capture-20260901-203045.jsonl"


def test_capture_writes_metadata_samples_and_summary(tmp_path) -> None:
    clock = FakeClock()
    path = tmp_path / "capture.jsonl"
    writer = CaptureWriter(
        path,
        {"device": {"name": "Fake G29", "axis_count": 3}},
        target_hz=120,
        flush_every=1,
        clock_ns=clock,
        now_iso=lambda: "2026-09-01T20:00:00+00:00",
    ).open()

    clock.advance(10_000_000)
    writer.sample([0.0, -1.0, 1.0], [0, 1], [(0, 0)])
    clock.advance(10_000_000)
    writer.sample([0.5, -0.5, 0.5], [1, 0], [(1, 0)])
    clock.advance(80_000_000)
    summary = writer.close(reason="test_complete")

    records = read_jsonl(path)
    assert [record["type"] for record in records] == [
        "metadata",
        "event",
        "sample",
        "sample",
        "summary",
    ]
    assert records[0]["schema_version"] == SCHEMA_VERSION
    assert records[2]["axes"] == [0.0, -1.0, 1.0]
    assert records[2]["buttons"] == [0, 1]
    assert records[2]["hats"] == [[0, 0]]
    assert records[3]["seq"] == 1
    assert summary["sample_count"] == 2
    assert summary["duration_ns"] == 100_000_000
    assert summary["observed_hz"] == 20.0
    assert summary["reason"] == "test_complete"


def test_close_is_idempotent(tmp_path) -> None:
    writer = CaptureWriter(tmp_path / "capture.jsonl", {}).open()
    first = writer.close()
    second = writer.close()

    assert first["type"] == "summary"
    assert second == {}


def test_flushed_samples_are_recoverable_before_close(tmp_path) -> None:
    path = tmp_path / "recoverable.jsonl"
    writer = CaptureWriter(path, {}, flush_every=1).open()
    writer.sample([0.25], [0], [])

    records = read_jsonl(path)

    assert [record["type"] for record in records] == ["metadata", "event", "sample"]
    assert records[-1]["axes"] == [0.25]
    writer.close()


def test_operations_fail_before_open(tmp_path) -> None:
    writer = CaptureWriter(tmp_path / "capture.jsonl", {})

    with pytest.raises(RuntimeError, match="não está aberta"):
        writer.sample([], [], [])
