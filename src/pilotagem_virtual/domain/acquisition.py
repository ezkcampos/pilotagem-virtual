"""Host polling diagnostics, independent of Qt and of scoring policy."""
from __future__ import annotations

from dataclasses import dataclass
from math import floor
from collections.abc import Sequence


def percentile(values: Sequence[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


@dataclass(frozen=True)
class AcquisitionReport:
    sample_count: int
    observed_hz: float
    per_second: tuple[int, ...]
    interval_p50_ms: float | None
    interval_p95_ms: float | None
    interval_p99_ms: float | None
    max_interval_ms: float | None
    leading_gap_ms: float
    trailing_gap_ms: float
    issues: tuple[str, ...]
    policy_version: str = "acquisition-candidate-v1"


def summarize_acquisition(
    timestamps_ns: Sequence[int], duration_ns: int, *, minimum_hz: int = 60,
    maximum_gap_ns: int = 50_000_000,
) -> AcquisitionReport:
    """Count only real readings in [0, duration); no end-context or resampling.

    The 60 Hz / 50 ms checks are experimental quality diagnostics, not approval
    of performance or a final policy for assigning exercise scores.
    """
    if duration_ns <= 0 or minimum_hz <= 0 or maximum_gap_ns <= 0:
        raise ValueError("Parâmetros de aquisição inválidos")
    times = tuple(timestamps_ns)
    issues: list[str] = []
    if any(b <= a for a, b in zip(times, times[1:])):
        issues.append("non_monotonic_timestamp")
    if any(t < 0 or t >= duration_ns for t in times):
        issues.append("outside_attempt")
    inside = tuple(t for t in times if 0 <= t < duration_ns)
    seconds = duration_ns // 1_000_000_000
    counts = [0] * seconds
    for timestamp in inside:
        bucket = timestamp // 1_000_000_000
        if bucket < seconds:
            counts[bucket] += 1
    if not inside:
        issues.append("no_samples")
    if any(count < minimum_hz for count in counts):
        issues.append("below_minimum_hz")
    gaps = [b - a for a, b in zip(inside, inside[1:]) if b > a]
    leading = min(inside) if inside else duration_ns
    trailing = duration_ns - max(inside) if inside else duration_ns
    if max([leading, trailing, *gaps]) > maximum_gap_ns:
        issues.append("acquisition_gap")

    def milliseconds(fraction: float) -> float | None:
        result = percentile(gaps, fraction)
        return None if result is None else result / 1_000_000

    return AcquisitionReport(
        len(inside), len(inside) / (duration_ns / 1_000_000_000), tuple(counts),
        milliseconds(0.5), milliseconds(0.95), milliseconds(0.99),
        max(gaps) / 1_000_000 if gaps else None,
        leading / 1_000_000, trailing / 1_000_000, tuple(issues),
    )
