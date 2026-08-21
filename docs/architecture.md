# Architecture Overview

## Phase 1 Architecture

```
Client
  │
  ▼
FastAPI (app/)
  │
  ├── GET /health          → Application health
  ├── GET /ready           → Database readiness
  ├── POST /api/v1/evaluations  → Run evaluation
  ├── GET /api/v1/runs/{id}     → Retrieve run
  ├── GET /api/v1/runs          → List runs
  └── GET /api/v1/datasets      → (stub, Phase 2+)
  │
  ▼
EvaluationService (app/services/)
  │
  ▼
EvaluationEngine (evaluator/)
  │
  ├── relevance   → Sentence-transformer cosine similarity
  ├── hallucination → NLI-based sentence classification
  ├── latency     → Timing measurement
  └── cost        → Token-based cost estimation
  │
  ▼
PostgreSQL (via SQLAlchemy + Alembic)
  │
  └── evaluation_runs table
```

## Components

### API Layer (`app/`)

- **FastAPI application** with automatic OpenAPI documentation
- **Pydantic schemas** for request/response validation
- **Route handlers** organized by domain (health, evaluations, runs)
- **Configuration** via `pydantic-settings` from environment variables

### Service Layer (`app/services/`)

- **EvaluationService** bridges the API layer and the evaluation engine
- Translates API request format to evaluator engine format
- Manages persistence through SQLAlchemy sessions
- Keeps route handlers thin — all business logic lives here

### Evaluation Engine (`evaluator/`)

The core evaluation package remains unchanged from Phase 0:

- **Relevance Scoring** — Sentence-transformer embeddings (`all-MiniLM-L6-v2`) with cosine similarity
- **Hallucination Detection** — NLI model (`roberta-large-mnli`) classifying sentences as supported/contradicted/unsupported
- **Latency Measurement** — Timing utility for execution profiling
- **Cost Estimation** — Token-based cost calculation with configurable pricing

### Database Layer (`app/db/`)

- **SQLAlchemy 2.0** ORM with mapped_column style
- **Alembic** migrations as the source of truth for schema management
- **EvaluationRun** model stores input data and evaluation results as JSONB columns

## Database Schema

### `evaluation_runs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique run identifier |
| `created_at` | DateTime(tz) | UTC creation timestamp |
| `status` | String(20) | Run status (completed, failed, pending) |
| `conversation` | JSONB | Original conversation input |
| `context` | JSONB | Original context input |
| `relevance` | Float | Relevance score [0, 1] |
| `hallucination` | JSONB | Hallucination report with flags and details |
| `latency_ms` | Float | Latency in milliseconds |
| `estimated_cost` | Float | Estimated token cost |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/llm_eval` | PostgreSQL connection string |
| `APP_ENV` | `development` | Application environment |
| `LOG_LEVEL` | `info` | Logging level |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

## Scaling Notes

- Cache embeddings in Redis (Phase 2+)
- Use ONNX runtime for faster NLI inference
- Batch NLI queries for throughput
- Add async workers for background evaluation (Phase 2+)
