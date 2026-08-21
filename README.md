# LLM Evaluation Pipeline

A production-grade, deployable LLM Evaluation & Quality-Gate Platform.

This repository implements a modular evaluation pipeline for LLM responses, with a FastAPI-based REST API and PostgreSQL persistence.

## Features

- **Relevance Scoring** — Sentence-transformer embeddings for semantic similarity
- **Hallucination Detection** — NLI-based factual consistency checking
- **Latency Measurement** — Execution time profiling
- **Token Cost Estimation** — Configurable token-based pricing
- **REST API** — FastAPI with automatic OpenAPI documentation
- **PostgreSQL Persistence** — Durable storage for evaluation runs
- **Docker Compose** — One-command local development stack

## Quick Start

### Using Docker Compose (recommended)

```bash
docker compose up --build
```

This starts:
- **API** at `http://localhost:8000`
- **PostgreSQL** at `localhost:5432`
- **Swagger docs** at `http://localhost:8000/docs`

### Local Development

1. Start PostgreSQL (via Docker or local install)
2. Set environment variables:
   ```bash
   export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/llm_eval
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   alembic upgrade head
   ```
5. Start the API:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Application health check |
| `GET` | `/ready` | Database readiness check |
| `POST` | `/api/v1/evaluations` | Submit an evaluation request |
| `GET` | `/api/v1/runs` | List evaluation runs (paginated) |
| `GET` | `/api/v1/runs/{run_id}` | Retrieve a specific evaluation run |
| `GET` | `/api/v1/datasets` | Dataset management (stub, Phase 2+) |

### Example: Submit Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": {
      "model_response": "Ibuprofen may cause stomach pain and nausea.",
      "input_tokens": 40,
      "output_tokens": 15
    },
    "context": [
      {"id": "1", "text": "Ibuprofen can cause stomach upset, nausea, dizziness."}
    ]
  }'
```

### Example: Retrieve Run

```bash
curl http://localhost:8000/api/v1/runs/{run_id}
```

## Project Structure

```
llm-evaluation-pipeline/
├── app/                        # FastAPI application
│   ├── main.py                 # Application factory
│   ├── api/                    # API layer
│   │   ├── routes/             # Route handlers
│   │   │   ├── health.py       # Health & readiness endpoints
│   │   │   ├── evaluations.py  # Evaluation creation
│   │   │   ├── runs.py         # Run retrieval
│   │   │   └── datasets.py     # Dataset stubs
│   │   └── schemas/            # Pydantic request/response models
│   │       ├── evaluations.py
│   │       ├── runs.py
│   │       └── datasets.py
│   ├── services/               # Business logic
│   │   └── evaluation_service.py
│   ├── db/                     # Database layer
│   │   ├── base.py             # SQLAlchemy declarative base
│   │   ├── session.py          # Session management
│   │   └── models.py           # ORM models
│   └── core/                   # Configuration
│       └── config.py           # pydantic-settings config
├── evaluator/                  # Core evaluation engine
│   ├── relevance.py            # Relevance scoring
│   ├── hallucination.py        # Hallucination detection
│   ├── latency.py              # Latency measurement
│   ├── cost.py                 # Cost estimation
│   └── pipeline.py             # Evaluation pipeline
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
├── tests/                      # Test suite
│   ├── test_api_health.py      # Health endpoint tests
│   ├── test_api_evaluations.py # Evaluation API tests
│   ├── test_api_runs.py        # Run retrieval tests
│   └── ...
├── docker-compose.yml          # Local dev stack
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## Database Migrations

```bash
# Apply migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"
```

## Running Tests

```bash
# Unit and integration tests
pytest -q

# Linting
ruff check .

# Formatting check
ruff format --check .

# CLI evaluation (standalone, no API)
python main.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/llm_eval` | PostgreSQL connection string |
| `APP_ENV` | `development` | Application environment |
| `LOG_LEVEL` | `info` | Logging level |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

See `.env.example` for a template.

## License

MIT

## Author

Meet Jadhav
GitHub: https://github.com/acrocantosauras
