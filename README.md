# LLM Evaluation Pipeline

A production-grade, deployable LLM Evaluation & Quality-Gate Platform.

## Features

- **Relevance Scoring** — Sentence-transformer embeddings for semantic similarity
- **Hallucination Detection** — NLI-based factual consistency checking
- **Latency Measurement** — Execution time profiling
- **Token Cost Estimation** — Configurable token-based pricing
- **REST API** — FastAPI with automatic OpenAPI documentation
- **Async Evaluation** — Background job processing via Redis + arq
- **Batch Evaluation** — Process multiple evaluation cases in one job
- **Quality Gates** — Configurable per-metric thresholds
- **Baselines** — Mark runs as baselines for comparison
- **Regression Detection** — Compare runs against baselines with metric-aware direction
- **PostgreSQL Persistence** — Durable storage for all evaluation data
- **Docker Compose** — One-command local development stack

## Quick Start

### Docker Compose (recommended)

```bash
docker compose up --build
```

Starts: API (port 8000), Worker, PostgreSQL (port 5432), Redis (port 6379)

### Local Development

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
# In another terminal:
arq app.worker.WorkerSettings
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Application health check |
| `GET` | `/ready` | Database readiness check |
| `POST` | `/api/v1/evaluations` | Synchronous evaluation |
| `POST` | `/api/v1/evaluations/async` | Async batch evaluation (202) |
| `GET` | `/api/v1/runs` | List evaluation runs |
| `GET` | `/api/v1/runs/{id}` | Get evaluation run |
| `GET` | `/api/v1/runs/{id}/compare/{baseline_id}` | Compare run to baseline |
| `GET` | `/api/v1/jobs` | List evaluation jobs |
| `GET` | `/api/v1/jobs/{id}` | Get job status + progress |
| `POST` | `/api/v1/jobs/{id}/cancel` | Cancel a job |
| `GET` | `/api/v1/jobs/{id}/quality-gate` | Get quality gate result |
| `POST` | `/api/v1/baselines` | Create baseline from run |
| `GET` | `/api/v1/baselines` | List baselines |
| `GET` | `/api/v1/quality-gates` | List quality gates |
| `POST` | `/api/v1/quality-gates` | Create quality gate |

## Example: Batch Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/evaluations/async \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"conversation": {"model_response": "Drug X reduces fever.", "input_tokens": 20, "output_tokens": 10}, "context": [{"text": "Drug X treats fever."}]},
      {"conversation": {"model_response": "Drug Y causes drowsiness.", "input_tokens": 20, "output_tokens": 10}, "context": [{"text": "Drug Y may cause drowsiness."}]}
    ]
  }'
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/llm_eval` | PostgreSQL URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `WORKER_CONCURRENCY` | `2` | Max concurrent worker jobs |
| `WORKER_MAX_RETRIES` | `3` | Max retry attempts per job |
| `APP_ENV` | `development` | Application environment |
| `LOG_LEVEL` | `info` | Logging level |

## Running Tests

```bash
pytest -q           # All tests
ruff check .        # Linting
ruff format --check .  # Formatting
```

## Project Structure

```
app/
├── main.py              # FastAPI application
├── worker.py            # arq worker
├── core/
│   ├── config.py        # pydantic-settings
│   └── enums.py         # JobStatus, GateOutcome
├── api/
│   ├── routes/          # Health, evaluations, jobs, baselines
│   └── schemas/         # Pydantic request/response models
├── services/
│   ├── evaluation_service.py  # Sync evaluation
│   ├── job_service.py         # Job lifecycle
│   ├── quality_gate_service.py # Gate evaluation
│   ├── baseline_service.py    # Baselines & regression
│   └── redis_queue.py         # Redis queue operations
└── db/
    ├── base.py          # SQLAlchemy base
    ├── models.py        # ORM models
    └── session.py       # Session management
evaluator/               # Core evaluation engine (unchanged)
alembic/                 # Database migrations
tests/                   # 108 tests
```

## License

MIT
