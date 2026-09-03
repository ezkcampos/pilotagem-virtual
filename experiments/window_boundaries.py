"""P0 counterexample: outside samples affect clipped linear interpolation.

Run with Python's standard library. This is an experiment, not a scoring rule.
An all-60% window has a known result of 100% time in [55%, 65%].
"""
from fractions import Fraction
import json


def counterexample(previous_value: int) -> dict:
    window_start, window_end = Fraction(1), Fraction(7)
    before, first_inside = Fraction(997, 1000), Fraction(1005, 1000)
    previous, inside = Fraction(previous_value), Fraction(60)
    value_at_start = previous + (inside - previous) * (window_start - before) / (first_inside - before)
    crossing = window_start
    if value_at_start < 55:
        crossing = before + (55 - previous) / (inside - previous) * (first_inside - before)
    elif value_at_start > 65:
        crossing = before + (65 - previous) / (inside - previous) * (first_inside - before)
    outside_duration = max(Fraction(0), crossing - window_start)
    return {
        "previous_value_percent": previous_value,
        "all_in_window_samples_percent": 60,
        "interpolated_value_at_start": float(value_at_start),
        "outside_seconds_from_external_interpolation": float(outside_duration),
        "time_in_band_percent": float(100 * (1 - outside_duration / (window_end - window_start))),
        "expected_percent_by_CA2_002": 100,
    }


if __name__ == "__main__":
    print(json.dumps([counterexample(value) for value in (0, 60, 100)], indent=2))
