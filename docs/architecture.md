# Architecture Overview

## Phase 2 Architecture

```
                     Client
                       │
                       ▼
                    FastAPI
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
   Synchronous API          Async Evaluation API
   POST /api/v1/evaluations  POST /api/v1/evaluations/async
          │                         │
          │                         ▼
          │                      Redis Queue
          │                         │
          │                         ▼
          │                    arq Worker
          │                         │
          │                         ▼
          │                EvaluationService
          │                         │
          │                  EvaluationEngine
          │                  ┌──────┴──────┐
          │             relevance  hallucination
          │             latency    cost
          │                         │
          │                    PostgreSQL
          │                         │
          │               ┌─────────┴─────────┐
          │               │                   │
          │          Quality Gate      Baseline Comparison
          │          (thresholds)      (regression detection)
          │
          ▼
    Direct Response
```

## Components

### Application Layer (`app/`)

- **FastAPI** with async evaluation, job management, quality gates, and baselines
- **arq worker** processes evaluation jobs asynchronously from Redis queue
- **SQLAlchemy** ORM with PostgreSQL for persistent storage
- **Redis** for job queue, job state, and temporary progress

### Core Evaluation Engine (`evaluator/`)

Unchanged from Phase 0 — the core evaluation engine remains the source of truth:
- Relevance scoring (sentence-transformer cosine similarity)
- Hallucination detection (NLI sentence classification)
- Latency measurement
- Cost estimation

### Job System

- Jobs represent batch evaluation requests
- Job statuses: queued → running → completed/failed/cancelled
- Progress tracking: total, completed, failed items
- Idempotency: re-executing a completed job is a no-op
- Cooperative cancellation: worker checks for cancellation before each item

### Quality Gates

Configurable per-metric thresholds:
- **Relevance**: minimum score (higher is better)
- **Hallucination**: maximum unsupported fraction (lower is better)
- **Latency**: maximum ms (lower is better)
- **Cost**: maximum estimated cost (lower is better)

Quality gates produce PASS/FAIL with individual check results.

### Baselines & Regression Detection

- Mark any evaluation run as a baseline
- Compare subsequent runs against baselines
- Metric-aware direction: understands higher-is-better vs lower-is-better
- Configurable tolerances per metric
- Produces regression and improvement reports

## Database Schema (Phase 2 additions)

### `evaluation_jobs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique job identifier |
| `created_at` | DateTime(tz) | UTC creation timestamp |
| `started_at` | DateTime(tz) | When worker began processing |
| `completed_at` | DateTime(tz) | When job finished |
| `status` | String(20) | queued/running/completed/failed/cancelled |
| `total_items` | Integer | Total evaluation cases |
| `completed_items` | Integer | Successfully processed |
| `failed_items` | Integer | Failed during processing |
| `error_message` | String(1000) | Error details if failed |
| `items` | JSONB | Input evaluation cases |
| `evaluation_run_id` | UUID (FK) | Associated run |
| `quality_gate_id` | UUID (FK) | Associated quality gate |
| `batch_results` | JSONB | Per-item results |

### `quality_gates`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique gate identifier |
| `created_at` | DateTime(tz) | Creation timestamp |
| `name` | String(100) | Unique gate name |
| `thresholds` | JSONB | Per-metric threshold config |
| `enabled` | Boolean | Whether gate is active |

### `evaluation_baselines`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique baseline identifier |
| `created_at` | DateTime(tz) | Creation timestamp |
| `name` | String(100) | Unique baseline name |
| `description` | String(500) | Description |
| `run_id` | UUID (FK) | The run marked as baseline |

### `evaluation_runs` (modified)

| New Column | Type | Description |
|-----------|------|-------------|
| `is_baseline` | Boolean | Whether this run is a baseline |

## Redis Usage

| Key Pattern | Purpose | TTL |
|------------|---------|-----|
| `llm_eval:jobs:queue` | Job ID queue (list) | Persistent |
| `llm_eval:jobs:state:{id}` | Job state JSON | 24h |
| `llm_eval:jobs:progress:{id}` | Progress JSON | 24h |

## Migration History

```
<base> → 001_initial (evaluation_runs)
  → 002_phase2 (evaluation_jobs, quality_gates, evaluation_baselines, is_baseline)
```

## Scaling Notes

- Worker concurrency via `WORKER_CONCURRENCY` env var
- Redis handles temporary job state (TTL 24h)
- PostgreSQL is source of truth for persistent data
- Batch evaluations process items sequentially within a job
- Future: batch NLI queries, ONNX runtime, async evaluation
