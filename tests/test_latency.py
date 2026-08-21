import time

from evaluator.latency import measure_latency


def test_measure_latency_returns_number():
    """measure_latency should return a numeric value."""
    result = measure_latency(lambda: None)
    assert isinstance(result, (int, float))


def test_measure_latency_non_negative():
    """Measured latency should be non-negative."""
    result = measure_latency(lambda: None)
    assert result >= 0


def test_measure_latency_with_sleep():
    """measure_latency should accurately measure time for a sleeping function."""
    result = measure_latency(lambda: time.sleep(0.01), runs=1)
    # Should be at least ~10ms (0.01s * 1000)
    assert result >= 5  # generous lower bound in ms


def test_measure_latency_multiple_runs():
    """measure_latency averages over multiple runs."""
    result = measure_latency(lambda: None, runs=5)
    assert isinstance(result, float)
    assert result >= 0


def test_measure_latency_single_run():
    """measure_latency works with a single run."""
    result = measure_latency(lambda: None, runs=1)
    assert isinstance(result, float)
    assert result >= 0


def test_measure_latency_custom_function():
    """measure_latency works with a custom function that does work."""
    data = []

    def append_work():
        data.append(1)

    result = measure_latency(append_work, runs=3)
    assert result >= 0
    assert len(data) == 3  # function was called 3 times
