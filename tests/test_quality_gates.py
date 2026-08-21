import uuid


def test_create_quality_gate(client):
    """POST /api/v1/quality-gates creates a gate."""
    gate = {"name": "strict", "thresholds": {"relevance": {"min": 0.9}}}
    response = client.post("/api/v1/quality-gates", json=gate)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "strict"
    assert data["thresholds"] == {"relevance": {"min": 0.9}}
    assert data["enabled"] is True
    uuid.UUID(data["gate_id"])


def test_create_quality_gate_defaults(client):
    """Quality gate with empty thresholds gets defaults."""
    gate = {"name": "default-gate"}
    response = client.post("/api/v1/quality-gates", json=gate)
    assert response.status_code == 201
    data = response.json()
    assert "relevance" in data["thresholds"]
    assert "latency_ms" in data["thresholds"]


def test_create_quality_gate_duplicate_name(client):
    """Duplicate gate names should fail."""
    gate = {"name": "my-gate"}
    client.post("/api/v1/quality-gates", json=gate)
    response = client.post("/api/v1/quality-gates", json=gate)
    # SQLite raises IntegrityError → 500; PostgreSQL would raise unique violation → 500/409
    assert response.status_code in (409, 500)


def test_list_quality_gates(client):
    """GET /api/v1/quality-gates lists all gates."""
    client.post("/api/v1/quality-gates", json={"name": "gate-a"})
    client.post("/api/v1/quality-gates", json={"name": "gate-b"})

    response = client.get("/api/v1/quality-gates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_quality_gate(client):
    """GET /api/v1/quality-gates/{id} returns specific gate."""
    resp = client.post("/api/v1/quality-gates", json={"name": "specific"})
    gate_id = resp.json()["gate_id"]

    response = client.get(f"/api/v1/quality-gates/{gate_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "specific"


def test_get_quality_gate_not_found(client):
    """GET /api/v1/quality-gates/{id} returns 404 for unknown."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/quality-gates/{fake_id}")
    assert response.status_code == 404


def test_evaluate_gate_pass():
    """Quality gate evaluation with passing results."""
    from app.services.quality_gate_service import evaluate_gate

    thresholds = {"relevance": {"min": 0.80}, "latency_ms": {"max": 2000}}
    results = {"relevance": 0.95, "latency_ms": 500, "hallucination": {"fraction_supported": 0.95}}

    gate_result = evaluate_gate(thresholds, results)
    assert gate_result["status"] == "pass"
    assert gate_result["checks"]["relevance"]["passed"] is True
    assert gate_result["checks"]["latency_ms"]["passed"] is True


def test_evaluate_gate_fail():
    """Quality gate evaluation with failing results."""
    from app.services.quality_gate_service import evaluate_gate

    thresholds = {"relevance": {"min": 0.90}, "latency_ms": {"max": 1000}}
    results = {"relevance": 0.70, "latency_ms": 1500, "hallucination": {"fraction_supported": 0.85}}

    gate_result = evaluate_gate(thresholds, results)
    assert gate_result["status"] == "fail"
    assert gate_result["checks"]["relevance"]["passed"] is False
    assert gate_result["checks"]["latency_ms"]["passed"] is False


def test_evaluate_gate_direction():
    """Quality gate correctly applies higher-is-better and lower-is-better."""
    from app.services.quality_gate_service import evaluate_gate

    thresholds = {"relevance": {"min": 0.80}, "estimated_cost": {"max": 0.005}}
    results = {"relevance": 0.75, "estimated_cost": 0.01, "hallucination": {"fraction_supported": 1.0}}

    gate_result = evaluate_gate(thresholds, results)
    assert gate_result["checks"]["relevance"]["direction"] == "higher_is_better"
    assert gate_result["checks"]["estimated_cost"]["direction"] == "lower_is_better"
    assert gate_result["status"] == "fail"


def test_evaluate_gate_hallucination_fraction():
    """Quality gate computes unsupported fraction correctly."""
    from app.services.quality_gate_service import evaluate_gate

    thresholds = {"hallucination_fraction_unsupported": {"max": 0.10}}
    results = {"hallucination": {"fraction_supported": 0.85}}  # 15% unsupported

    gate_result = evaluate_gate(thresholds, results)
    assert gate_result["checks"]["hallucination_fraction_unsupported"]["value"] == 0.15
    assert gate_result["checks"]["hallucination_fraction_unsupported"]["passed"] is False
