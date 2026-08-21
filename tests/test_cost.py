from evaluator.cost import estimate_cost


def test_estimate_cost_basic():
    """Cost calculation should use the configured pricing."""
    convo = {"input_tokens": 1000, "output_tokens": 1000}
    cost = estimate_cost(convo)
    # (1000/1000)*0.00015 + (1000/1000)*0.0006 = 0.00075
    assert cost == 0.00075


def test_estimate_cost_zero_tokens():
    """Zero tokens should produce zero cost."""
    convo = {"input_tokens": 0, "output_tokens": 0}
    cost = estimate_cost(convo)
    assert cost == 0.0


def test_estimate_cost_input_only():
    """Only input tokens → cost from input pricing only."""
    convo = {"input_tokens": 2000, "output_tokens": 0}
    cost = estimate_cost(convo)
    # (2000/1000)*0.00015 = 0.0003
    assert cost == 0.0003


def test_estimate_cost_output_only():
    """Only output tokens → cost from output pricing only."""
    convo = {"input_tokens": 0, "output_tokens": 500}
    cost = estimate_cost(convo)
    # (500/1000)*0.0006 = 0.0003
    assert cost == 0.0003


def test_estimate_cost_missing_fields():
    """Missing token fields should default to 0."""
    convo = {}
    cost = estimate_cost(convo)
    assert cost == 0.0


def test_estimate_cost_partial_fields():
    """Partial token fields should work (missing one defaults to 0)."""
    convo = {"input_tokens": 100}
    cost = estimate_cost(convo)
    # (100/1000)*0.00015 = 0.000015
    assert cost == 0.000015


def test_estimate_cost_large_tokens():
    """Large token counts should calculate correctly."""
    convo = {"input_tokens": 100_000, "output_tokens": 50_000}
    cost = estimate_cost(convo)
    # (100000/1000)*0.00015 + (50000/1000)*0.0006 = 0.015 + 0.03 = 0.045
    assert cost == 0.045


def test_estimate_cost_is_rounded():
    """Result should be rounded to 8 decimal places."""
    convo = {"input_tokens": 3, "output_tokens": 7}
    cost = estimate_cost(convo)
    # Verify it's a float with limited precision
    assert isinstance(cost, float)
    # Check rounding: cost should have at most 8 decimal places
    cost_str = str(cost)
    if "." in cost_str:
        decimals = len(cost_str.split(".")[1])
        assert decimals <= 8
