from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO


SCHEMA_VERSION = "hardware-spike-v1"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def suggested_filename(now: datetime | None = None) -> str:
    instant = now or datetime.now(UTC)
    return f"g29-capture-{instant.strftime('%Y%m%d-%H%M%S')}.jsonl"


class CaptureWriter:
    """Stream a diagnostic capture as recoverable JSON Lines."""

    def __init__(
        self,
        path: str | Path,
        metadata: Mapping[str, Any],
        *,
        target_hz: int = 120,
        flush_every: int = 120,
        clock_ns: Callable[[], int] = time.perf_counter_ns,
        now_iso: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.path = Path(path)
        self.target_hz = target_hz
        self.flush_every = max(1, flush_every)
        self._clock_ns = clock_ns
        self._now_iso = now_iso
        self._file: TextIO | None = None
        self._start_ns = 0
        self._sample_count = 0
        self._closed = False
        self._metadata = dict(metadata)

    @property
    def sample_count(self) -> int:
        return self._sample_count

    @property
    def is_open(self) -> bool:
        return self._file is not None and not self._closed

    @property
    def elapsed_ns(self) -> int:
        if not self.is_open:
            return 0
        return max(0, self._clock_ns() - self._start_ns)

    def open(self) -> CaptureWriter:
        if self._file is not None:
            raise RuntimeError("CaptureWriter já foi aberto")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8", newline="\n")
        self._start_ns = self._clock_ns()
        self._write(
            {
                "type": "metadata",
                "schema_version": SCHEMA_VERSION,
                "created_at_utc": self._now_iso(),
                "target_hz": self.target_hz,
                **self._metadata,
            },
            flush=True,
        )
        self.event("recording_started")
        return self

    def event(self, name: str, **details: Any) -> None:
        self._ensure_open()
        self._write(
            {
                "type": "event",
                "name": name,
                "elapsed_ns": self.elapsed_ns,
                "details": details,
            },
            flush=True,
        )

    def sample(
        self,
        axes: Sequence[float],
        buttons: Sequence[int | bool],
        hats: Sequence[Sequence[int]],
    ) -> None:
        self._ensure_open()
        payload = {
            "type": "sample",
            "seq": self._sample_count,
            "elapsed_ns": self.elapsed_ns,
            "axes": [round(float(value), 8) for value in axes],
            "buttons": [int(bool(value)) for value in buttons],
            "hats": [[int(value) for value in hat] for hat in hats],
        }
        self._sample_count += 1
        self._write(payload, flush=self._sample_count % self.flush_every == 0)

    def close(self, reason: str = "user_stopped", **details: Any) -> dict[str, Any]:
        if self._file is None or self._closed:
            return {}

        duration_ns = max(0, self._clock_ns() - self._start_ns)
        observed_hz = (
            self._sample_count / (duration_ns / 1_000_000_000)
            if duration_ns > 0
            else 0.0
        )
        summary = {
            "type": "summary",
            "ended_at_utc": self._now_iso(),
            "reason": reason,
            "duration_ns": duration_ns,
            "sample_count": self._sample_count,
            "observed_hz": round(observed_hz, 3),
            "details": details,
        }
        self._write(summary, flush=True)
        self._file.close()
        self._closed = True
        return summary

    def _write(self, payload: Mapping[str, Any], *, flush: bool = False) -> None:
        self._ensure_open()
        assert self._file is not None
        self._file.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        self._file.write("\n")
        if flush:
            self._file.flush()

    def _ensure_open(self) -> None:
        if self._file is None or self._closed:
            raise RuntimeError("A captura não está aberta")

    def __enter__(self) -> CaptureWriter:
        return self.open()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        reason = "exception" if exc_type is not None else "context_closed"
        self.close(reason=reason)
