# Architecture Overview

## System Architecture

```
                         Users / CI
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
             Web Dashboard          REST API
            (Next.js)             (FastAPI)
                 │                       │
                 └───────────┬───────────┘
                             ▼
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          PostgreSQL       Redis        Workers
         (persistent     (queue +      (arq)
          data)           temp state)
                             │
                             ▼
                      Evaluation Engine
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          Traditional    RAG Metrics    LLM Judge
          Metrics        (5 evaluators) (provider-agnostic)
              │              │              │
              ▼              ▼              ▼
           MetricResult Objects (versioned, structured)
                             │
                    ┌────────┼────────┐
                    ▼        ▼        ▼
                Quality    Baseline  Composite
                Gates    Comparison  Scoring
                             │
                             ▼
                         PostgreSQL
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
           Prometheus    Grafana     Dashboard
           (metrics)    (dashboards) (visuals)
```

## Components

### 1. Evaluation Engine (`evaluator/`)

The core evaluation engine processes inputs and produces structured `MetricResult` objects.

**Available evaluators:**

| Evaluator | Version | Purpose | Direction |
|-----------|---------|---------|-----------|
| `relevance` | 1.0.0 | Semantic similarity (embeddings) | higher_is_better |
| `hallucination` | 1.0.0 | NLI-based factual checking | lower_is_better |
| `faithfulness` | 1.0.0 | Claim-level context support | higher_is_better |
| `context_precision` | 1.0.0 | Retrieval relevance scoring | higher_is_better |
| `context_recall` | 1.0.0 | Information completeness | higher_is_better |
| `answer_relevancy` | 1.0.0 | QA alignment scoring | higher_is_better |
| `citation_correctness` | 1.0.0 | Source attribution verification | higher_is_better |
| `latency` | 1.0.0 | Execution time measurement | lower_is_better |
| `cost` | 1.0.0 | Token cost estimation | lower_is_better |
| `judge` | 1.0.0 | LLM-as-a-judge evaluation | higher_is_better |

**Evaluation profiles** define which evaluators run:
- `basic` — relevance, hallucination, latency, cost
- `rag` — basic + faithfulness, context_precision, context_recall, answer_relevancy
- `rag_strict` — rag + citation_correctness
- `judge` — rag_strict + LLM judge

### 2. Application Layer (`app/`)

FastAPI application with:
- **20+ REST endpoints** with automatic OpenAPI docs
- **Service layer** between routes and evaluator
- **Authentication** via SHA-256 hashed API keys
- **Rate limiting** per-project
- **Request correlation** via X-Request-ID headers
- **Structured logging** (JSON format)

### 3. Persistence (`PostgreSQL`)

| Table | Purpose |
|-------|---------|
| `projects` | Multi-tenant project isolation |
| `api_keys` | Hashed API key storage |
| `evaluation_runs` | Evaluation results + input |
| `metric_results` | Individual metric scores |
| `evaluation_jobs` | Async job lifecycle |
| `quality_gates` | Threshold configurations |
| `evaluation_baselines` | Baseline run markers |

### 4. Async Processing (`Redis` + `arq`)

```
API → Redis Queue → arq Worker → Evaluation → PostgreSQL
```

- **Job queue** via Redis lists (`blpop`)
- **Job state** in Redis (24h TTL)
- **Worker concurrency** configurable via `WORKER_CONCURRENCY`
- **Bounded retries** via `WORKER_MAX_RETRIES`
- **Cooperative cancellation** checked before each item

### 5. Quality Gates

Threshold-based pass/fail determination:
```json
{
  "relevance": {"value": 0.80, "direction": "higher_is_better"},
  "latency_ms": {"value": 2000, "direction": "lower_is_better"}
}
```

Supports all metrics with correct directional comparison.

### 6. Baseline Comparison

Regression detection compares metric scores between baseline and current runs:
- Correctly handles higher-is-better (relevance, faithfulness) and lower-is-better (latency, cost) metrics
- Configurable tolerance thresholds
- Identifies specific metric regressions and improvements

### 7. Observability

- **Prometheus** — API request counts/latency, evaluation metrics, worker metrics, judge metrics
- **OpenTelemetry** — Distributed tracing with safe attributes
- **Structured Logging** — JSON logs with request_id, job_id, run_id, duration
- **Grafana** — Pre-configured dashboards via `docker-compose.prod.yml`

### 8. Dashboard (React/Next.js)

Production-quality dashboard with:
- Overview stats and recent runs
- Run detail with metric visualization
- Job monitoring
- Quality gate configuration view
- Baseline management
- Evaluation profile browser

## Security

- API keys stored as SHA-256 hashes (never plaintext)
- Project-level resource isolation
- Rate limiting on all API endpoints
- CORS restricted to configured origins
- Non-root Docker containers
- Parameterized database queries
- Request-size limits
- Structured error responses (no stack traces)

## Migration Strategy

All database changes go through Alembic:
```
001_initial → 002_phase2 → 003_phase3 → 004_phase4
```

Migrations are linear, reversible, and never modify historical migrations.

## Scaling Notes

- **Horizontal scaling**: Add API instances behind a load balancer
- **Worker scaling**: Increase `WORKER_CONCURRENCY` or add worker containers
- **Database**: Use managed PostgreSQL (AWS RDS, Supabase, etc.)
- **Redis**: Use managed Redis (Upstash, ElastiCache, etc.)
- **Dashboard**: Static export to Vercel/Netlify for zero-infrastructure frontend
