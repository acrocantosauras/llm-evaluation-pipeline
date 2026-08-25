# LLM Evaluation Platform

A production-grade, deployable LLM Evaluation & Quality-Gate Platform.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## What This Is

An end-to-end evaluation platform for LLM and RAG applications that measures answer quality, grounding, retrieval quality, and cost — with quality gates and regression detection for CI/CD pipelines.

```
User/CI → FastAPI → Evaluation Engine → PostgreSQL
                    ↓
              Quality Gates
              Regression Detection
              Dashboard (React)
              Prometheus + Grafana
```

## Features

### Evaluation Engine
- **Relevance Scoring** — Sentence-transformer embeddings
- **Hallucination Detection** — NLI-based factual consistency
- **Faithfulness** — Claim-level context support checking
- **Context Precision/Recall** — Retrieval quality measurement
- **Answer Relevancy** — Question-answer alignment scoring
- **Citation Correctness** — Source attribution verification
- **LLM-as-a-Judge** — Configurable provider, rubric-based semantic evaluation
- **Composite Scoring** — Weighted multi-metric scoring

### Platform
- **REST API** — 20+ endpoints with OpenAPI docs
- **Async Evaluation** — Background jobs via Redis + arq
- **Batch Evaluation** — Process multiple cases in one job
- **Quality Gates** — Configurable per-metric thresholds
- **Baselines** — Mark runs for comparison
- **Regression Detection** — Metric-aware direction (higher/lower is better)
- **API Authentication** — SHA-256 hashed API keys with project isolation
- **Rate Limiting** — Configurable per-project limits

### Observability
- **Prometheus Metrics** — API, evaluation, worker, judge metrics
- **OpenTelemetry Tracing** — Request tracing across services
- **Structured Logging** — JSON logs with correlation IDs
- **Grafana Dashboards** — Pre-configured monitoring

### CI/CD
- **Evaluation Quality Gates** — Run evaluations on every PR
- **Baseline Comparison** — Detect regressions automatically
- **GitHub Actions** — Full CI/CD workflow included

### Dashboard
- **Overview** — Stats, recent runs, health status
- **Run Details** — Metric scores, quality gate results
- **Jobs** — Async job status and progress
- **Quality Gates** — Threshold configuration
- **Baselines** — Baseline management
- **Evaluation Profiles** — Available evaluator sets

## Quick Start

### Docker Compose (recommended)

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD in .env for production
docker compose up --build
```

Services: API (8000), Worker, PostgreSQL (5432), Redis (6379)

### Local Development

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload
# Worker in another terminal:
arq app.worker.WorkerSettings
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Opens at http://localhost:3000

## API Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Application health |
| `GET` | `/ready` | Database readiness |
| `GET` | `/metrics` | Prometheus metrics |

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects` | List projects |
| `POST` | `/api/v1/projects/{id}/api-keys` | Create API key |
| `DELETE` | `/api/v1/projects/{id}/api-keys/{key_id}` | Revoke key |

### Evaluations
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/evaluations` | Sync evaluation |
| `POST` | `/api/v1/evaluations/async` | Async batch (202) |

### Runs & Jobs
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/runs` | List runs |
| `GET` | `/api/v1/runs/{id}` | Get run details |
| `GET` | `/api/v1/jobs` | List jobs |
| `GET` | `/api/v1/jobs/{id}` | Job status + progress |
| `POST` | `/api/v1/jobs/{id}/cancel` | Cancel job |

### Quality & Baselines
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/quality-gates` | Create gate |
| `GET` | `/api/v1/quality-gates` | List gates |
| `POST` | `/api/v1/baselines` | Create baseline |
| `GET` | `/api/v1/baselines` | List baselines |
| `GET` | `/api/v1/runs/{id}/compare/{baseline_id}` | Compare |

### Configuration
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/profiles` | List evaluation profiles |

## Example: Submit Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": {
      "model_response": "Ibuprofen can cause stomach upset and drowsiness.",
      "input_tokens": 20,
      "output_tokens": 10
    },
    "context": [
      {"text": "Ibuprofen may cause stomach upset as a common side effect."}
    ]
  }'
```

## Example: Batch Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/evaluations/async \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"conversation": {"model_response": "Drug X reduces fever."}, "context": [{"text": "Drug X treats fever."}]},
      {"conversation": {"model_response": "Drug Y causes drowsiness."}, "context": [{"text": "Drug Y may cause drowsiness."}]}
    ]
  }'
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Application environment |
| `DATABASE_URL` | `postgresql+psycopg://...` | PostgreSQL URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `WORKER_CONCURRENCY` | `2` | Max concurrent worker jobs |
| `WORKER_MAX_RETRIES` | `3` | Max retry attempts |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |
| `RATE_LIMIT_REQUESTS` | `100` | Requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window (seconds) |
| `PROMETHEUS_ENABLED` | `true` | Enable metrics endpoint |
| `OPENTELEMETRY_ENABLED` | `false` | Enable tracing |

## Running Tests

```bash
pytest -q              # 182 tests
ruff check .           # Linting
ruff format --check .  # Formatting
python main.py         # CLI smoke test
```

## Project Structure

```
app/                         # FastAPI application
├── main.py                  # Application factory
├── worker.py                # arq background worker
├── core/
│   ├── config.py            # Environment-based settings
│   ├── enums.py             # Status enums
│   └── security.py          # API key management
├── api/
│   ├── deps.py              # Auth, rate limiting, request ID
│   ├── routes/              # 20+ endpoint handlers
│   └── schemas/             # Pydantic models
├── services/                # Business logic layer
├── observability/           # Prometheus, OTel, structured logging
└── db/                      # SQLAlchemy models + session
evaluator/                   # Core evaluation engine
├── base.py                  # MetricResult, BaseEvaluator
├── registry.py              # Evaluator registry + profiles
├── composite.py             # Weighted composite scoring
├── judge.py                 # LLM-as-a-judge
├── profiles.py              # Evaluation profiles
├── faithfulness.py          # Claim-level support checking
├── context_precision.py     # Retrieval precision
├── context_recall.py        # Retrieval recall
├── answer_relevancy.py      # QA alignment
├── citation_correctness.py  # Source attribution
├── relevance.py             # Embedding similarity
├── hallucination.py         # NLI detection
├── latency.py               # Execution timing
└── cost.py                  # Token cost estimation
dashboard/                   # React/Next.js dashboard
alembic/                     # Database migrations (4)
tests/                       # 182 tests
.github/workflows/           # CI evaluation quality gate
config/                      # Prometheus + Grafana config
├── prometheus.yml
└── grafana/                  # Auto-provisioned dashboards
scripts/
│   └── evaluate_ci.py        # CI quality gate script
examples/
│   └── ci_evaluation_dataset.json
```

## CI/CD Quality Gate

The repository includes a GitHub Actions workflow that:

1. Runs all tests
2. Starts PostgreSQL + Redis
3. Runs evaluation on a synthetic dataset
4. Compares results against configured thresholds
5. Fails the build if quality gates fail

```yaml
# .github/workflows/ci-evaluation.yml
# Runs on every PR to main
```

## Known Limitations

- **Cloud deployment**: Not yet performed. Docker Compose config is production-ready but requires a cloud provider.
- **Dashboard authentication**: The dashboard does not currently pass API keys to the backend. It works in development mode (unauthenticated fallback).
- **Worker metrics**: The worker does not yet expose a `/metrics` endpoint. Prometheus config is ready for when it is added.
- **Grafana**: Dashboard auto-provisioned in `docker-compose.prod.yml`. Manual import available via `config/grafana/dashboards/llm-eval.json`.

## Cloud Deployment Status

```
Deployed: NO
Platform: N/A
Public URL: N/A
Reason: Cloud credentials/account access unavailable
```

## License

MIT
