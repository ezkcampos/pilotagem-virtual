import pytest

from pilotagem_virtual.domain.acquisition import summarize_acquisition


def test_real_sample_count_excludes_terminal_context_and_detects_sparse_second():
    times = [i * 5_000_000 for i in range(200)] + [1_000_000_000 + i * 25_000_000 for i in range(40)]
    report = summarize_acquisition(times, 2_000_000_000)
    assert report.observed_hz == 120
    assert report.per_second == (200, 40)
    assert report.issues == ("below_minimum_hz",)


def test_irregular_timestamps_keep_the_gap_in_statistics():
    report = summarize_acquisition([0, 8_000_000, 18_000_000, 98_000_000], 100_000_000)
    assert report.interval_p50_ms == 10
    assert report.interval_p95_ms == pytest.approx(73)
    assert report.max_interval_ms == 80
    assert report.trailing_gap_ms == 2
    assert "acquisition_gap" in report.issues


def test_empty_duplicate_and_outside_samples_are_not_accepted_silently():
    empty = summarize_acquisition([], 1_000_000_000)
    assert empty.interval_p95_ms is None
    assert "no_samples" in empty.issues
    report = summarize_acquisition([-1, 0, 0, 1_000_000_000], 1_000_000_000)
    assert "non_monotonic_timestamp" in report.issues
    assert "outside_attempt" in report.issues
    assert report.per_second == (2,)


def test_regular_120_hz_series_passes_candidate_checks():
    report = summarize_acquisition([round(i * 1e9 / 120) for i in range(1200)], 10_000_000_000)
    assert report.per_second == (120,) * 10
    assert report.observed_hz == 120
    assert not report.issues
