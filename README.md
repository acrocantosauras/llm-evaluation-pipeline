# LLM Evaluation Platform

A production-oriented, deployment-ready LLM Evaluation & Quality-Gate Platform.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Technology Stack

**Backend:** FastAPI, Python, SQLAlchemy, PostgreSQL, Alembic  
**Async Processing:** Redis, arq  
**Evaluation:** Sentence Transformers, NLI, LLM-as-a-Judge  
**Dashboard:** Next.js, React, TypeScript  
**Observability:** Prometheus, Grafana, OpenTelemetry  
**Infrastructure:** Docker, Docker Compose, GitHub Actions

## What This Is

An end-to-end evaluation and quality-control platform for LLM and RAG applications. It measures answer quality, grounding, retrieval performance, latency, and cost, then uses quality gates and regression detection to prevent degraded AI systems from reaching production.

```text
                         User / CI
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        Next.js Dashboard            FastAPI API
                                          │
                         ┌────────────────┼────────────────┐
                         ▼                ▼                ▼
                  Sync Evaluation    Redis + arq       PostgreSQL
                         │                │
                         │              Worker
                         │                │
                         └────────────┬───┘
                                      ▼
                              Evaluation Engine
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              Quality Gates      Baselines         LLM Judge
                    │                 │
                    └────────────┬────┘
                                 ▼
                         Regression Detection
                                 │
                         Prometheus + Grafana
Why This Project?

LLM applications can regress when prompts, models, retrieval systems, or application code change. Traditional unit tests cannot reliably detect these quality regressions.

This platform treats AI evaluation as an engineering control loop:

Evaluate → Compare → Gate → Detect Regression → Decide whether to ship

Instead of relying on manual inspection after every model, prompt, retrieval, or application change, the platform makes AI quality measurable and enforceable as part of the software delivery lifecycle.

Features
Evaluation Engine
Relevance Scoring — Sentence-transformer embeddings
Hallucination Detection — NLI-based factual consistency
Faithfulness — Claim-level context support checking
Context Precision/Recall — Retrieval quality measurement
Answer Relevancy — Question-answer alignment scoring
Citation Correctness — Source attribution verification
LLM-as-a-Judge — Configurable provider, rubric-based semantic evaluation
Composite Scoring — Weighted multi-metric scoring
Platform
REST API — 20+ endpoints with OpenAPI docs
Async Evaluation — Background jobs via Redis + arq
Batch Evaluation — Process multiple cases in one job
Quality Gates — Configurable per-metric thresholds
Baselines — Mark runs for comparison
Regression Detection — Metric-aware direction (higher/lower is better)
API Authentication — SHA-256 hashed API keys with project isolation
Rate Limiting — Configurable per-project limits
Observability
Prometheus Metrics — API, evaluation, worker, judge metrics
OpenTelemetry Tracing — Request tracing across services
Structured Logging — JSON logs with correlation IDs
Grafana Dashboards — Pre-configured monitoring
CI/CD
Evaluation Quality Gates — Run evaluations on every PR
Baseline Comparison — Detect regressions automatically
GitHub Actions — Full CI/CD workflow included
Dashboard
Overview — Stats, recent runs, health status
Run Details — Metric scores, quality gate results
Jobs — Async job status and progress
Quality Gates — Threshold configuration
Baselines — Baseline management
Evaluation Profiles — Available evaluator sets
What Makes This Different?

This project is not an LLM chatbot or a prompt wrapper.

It is an engineering platform for evaluating and operating LLM and RAG systems across their development lifecycle.

It combines:

Multi-dimensional LLM/RAG evaluation
Async and batch evaluation
Configurable quality gates
Baseline comparison
Metric-aware regression detection
LLM-as-a-judge evaluation
CI/CD quality enforcement
Project-scoped API authentication
Rate limiting
Operational observability
Dashboard-based evaluation monitoring

The goal is to make AI quality measurable, comparable, and enforceable as part of the software delivery lifecycle.

Quick Start
Docker Compose (recommended)
cp .env.example .env
# Set POSTGRES_PASSWORD in .env for production
docker compose up --build

Services: API (8000), Worker, PostgreSQL (5432), Redis (6379)

Local Development
pip install -r requirements.txt
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload

Worker in another terminal:

arq app.worker.WorkerSettings
Dashboard
cd dashboard
npm install
npm run dev

Opens at:

http://localhost:3000
API Endpoints
Health
Method	Path	Description
GET	/health	Application health
GET	/ready	Database readiness
GET	/metrics	Prometheus metrics
Authentication
Method	Path	Description
POST	/api/v1/projects	Create project
GET	/api/v1/projects	List projects
POST	/api/v1/projects/{id}/api-keys	Create API key
DELETE	/api/v1/projects/{id}/api-keys/{key_id}	Revoke key
Evaluations
Method	Path	Description
POST	/api/v1/evaluations	Sync evaluation
POST	/api/v1/evaluations/async	Async batch (202)
Runs & Jobs
Method	Path	Description
GET	/api/v1/runs	List runs
GET	/api/v1/runs/{id}	Get run details
GET	/api/v1/jobs	List jobs
GET	/api/v1/jobs/{id}	Job status + progress
POST	/api/v1/jobs/{id}/cancel	Cancel job
Quality & Baselines
Method	Path	Description
POST	/api/v1/quality-gates	Create gate
GET	/api/v1/quality-gates	List gates
POST	/api/v1/baselines	Create baseline
GET	/api/v1/baselines	List baselines
GET	/api/v1/runs/{id}/compare/{baseline_id}	Compare
Configuration
Method	Path	Description
GET	/api/v1/profiles	List evaluation profiles

Interactive API documentation is available at:

http://localhost:8000/docs
Example: Submit Evaluation
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
Example: Batch Evaluation
curl -X POST http://localhost:8000/api/v1/evaluations/async \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"conversation": {"model_response": "Drug X reduces fever."}, "context": [{"text": "Drug X treats fever."}]},
      {"conversation": {"model_response": "Drug Y causes drowsiness."}, "context": [{"text": "Drug Y may cause drowsiness."}]}
    ]
  }'
Environment Variables
Variable	Default	Description
APP_ENV	development	Application environment
DATABASE_URL	postgresql+psycopg://...	PostgreSQL URL
REDIS_URL	redis://localhost:6379/0	Redis URL
WORKER_CONCURRENCY	2	Max concurrent worker jobs
WORKER_MAX_RETRIES	3	Max retry attempts
CORS_ORIGINS	["http://localhost:3000"]	Allowed origins
RATE_LIMIT_REQUESTS	100	Requests per window
RATE_LIMIT_WINDOW	60	Rate limit window (seconds)
RATE_LIMIT_FAIL_CLOSED	false	If true, return 503 when the Redis-backed limiter is unreachable; default fails open (documented tradeoff)
MAX_BATCH_ITEMS	100	Max items per async batch submission
EVAL_MAX_CONCURRENCY	4	Max concurrent blocking evaluations per API process
EVAL_SLOT_TIMEOUT	30	Seconds to wait for an evaluation slot before returning 503
ALLOW_DEV_AUTH_FALLBACK	false	Explicit opt-in for the dev-only unauthenticated fallback. Never honored when APP_ENV=production|ci
PROMETHEUS_ENABLED	true	Enable metrics endpoint
OPENTELEMETRY_ENABLED	false	Enable tracing
Running Tests
pytest -q
ruff check .
ruff format --check .
python main.py
Current Validation
215 tests passing
Ruff checks passing
Docker Compose configuration validated
Production Docker Compose configuration validated

The test suite covers:

API behavior
synchronous evaluation
asynchronous evaluation
Redis queue behavior
worker lifecycle
quality gates
baseline comparison
regression detection
authentication
API key lifecycle
project isolation
rate limiting
observability
OpenAPI schema
evaluator behavior
Project Structure
app/
├── main.py                  # FastAPI application
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
alembic/                     # Database migrations (5)
tests/                       # 215 tests
.github/workflows/           # CI evaluation quality gate
config/                      # Prometheus + Grafana config
├── prometheus.yml
└── grafana/                 # Auto-provisioned dashboards
scripts/
└── evaluate_ci.py           # CI quality gate script
examples/
└── ci_evaluation_dataset.json
Evaluation Profiles

The platform supports predefined evaluation profiles that bundle evaluators for different use cases.

Profile	Purpose
basic	Core answer-quality evaluation
rag	RAG-focused evaluation
rag_strict	Stricter RAG quality evaluation
judge	LLM-as-a-judge evaluation

Profiles allow users to select an appropriate evaluation depth without manually configuring individual evaluators.

CI/CD Quality Gate

The repository includes a GitHub Actions workflow that:

Runs all tests
Starts PostgreSQL + Redis
Runs evaluation on a synthetic dataset
Compares results against configured thresholds
Fails the build if quality gates fail
# .github/workflows/ci-evaluation.yml
# Runs evaluation quality checks in CI

The workflow turns AI-quality regressions into an automated CI signal rather than something discovered manually after deployment.

Production Deployment
Required secrets (never committed)
Secret	Used by	Notes
POSTGRES_PASSWORD	prod compose	Required — compose fails fast if missing
GRAFANA_PASSWORD	prod compose	Required — no known defaults (admin/admin) are accepted
OPENAI_API_KEY / ANTHROPIC_API_KEY	judge profile	Only needed for profile=judge
API keys	clients	Created via POST /api/v1/projects/{id}/api-keys; shown exactly once
Deployment sequence (migrations)

Migrations are decoupled from application startup in production to avoid a migration race when scaling API replicas:

docker compose -f docker-compose.prod.yml up -d postgres redis
docker compose -f docker-compose.prod.yml up migrate — one-shot, serialized alembic upgrade head; exits non-zero on failure
docker compose -f docker-compose.prod.yml up -d api worker — these wait on migrate: service_completed_successfully; safe to scale to N replicas

The local development compose file keeps the convenient alembic upgrade head && uvicorn startup because it runs a single instance.

Network isolation

In docker-compose.prod.yml, Postgres (5432) and Redis (6379) are not published to the host — only the internal Docker network. The only published ports are the intended entry points: API (8000), Grafana, Prometheus.

For ad-hoc DB access:

docker compose exec postgres psql ...

Put a TLS-terminating reverse proxy (Caddy/nginx/ALB) in front of the API port for public deployments.

Future Production Infrastructure

The following are deployment-scale concerns that depend on the target infrastructure and service-level requirements, and are outside the current application scope:

High-availability PostgreSQL with automated failover
Automated backups / point-in-time recovery (PITR)
TLS termination / reverse proxy
Horizontal scaling and autoscaling
Cloud-specific deployment configuration
Known Limitations
Cloud deployment: Not yet performed. The production Docker Compose configuration is prepared, but public deployment requires a cloud provider and deployment-specific infrastructure.
Grafana: Dashboard auto-provisioned in docker-compose.prod.yml. Manual import is available via config/grafana/dashboards/llm-eval.json.
Dashboard polish: The dashboard is functional and communicates with the API, but additional UX polish can be added over time.
High availability: Production-scale HA PostgreSQL/Redis, automated failover, backups, and PITR depend on the target deployment infrastructure.
Cloud Deployment Status
Deployed: NO
Platform: N/A
Public URL: N/A
Reason: Cloud deployment has not yet been performed

The repository is prepared for deployment, but no public cloud deployment is claimed until one has been actually provisioned and externally verified.

Engineering Focus

This project demonstrates practical engineering across:

LLM/RAG evaluation
Machine-learning model inference
Evaluation framework design
Async distributed processing
REST API development
PostgreSQL data modeling
Redis-based job processing
Authentication and authorization
Rate limiting
Regression detection
CI/CD quality enforcement
Observability
Containerization
Production configuration
Frontend/dashboard integration
Automated testing

The central design goal is to treat LLM quality as an engineering signal that can be measured, persisted, compared, and enforced.

License

MIT


### Important correction from my previous answer

The version above is **one complete README**, not a collection of replacement snippets. It starts at:

```text
# LLM Evaluation Platform

and ends at:

## License

MIT
