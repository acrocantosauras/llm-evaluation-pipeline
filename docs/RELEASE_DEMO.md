# Release Demo Workflow

Step-by-step guide to demonstrate the LLM Evaluation Platform.

## Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional, for containerized demo)
- PostgreSQL (or use Docker)
- Redis (or use Docker)

## Quick Start (Local)

```bash
# 1. Start services
docker compose up -d postgres redis

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Start API server
uvicorn app.main:app --reload

# 5. (In another terminal) Start worker
arq app.worker.WorkerSettings
```

## Demo Steps

### Step 1: Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

curl http://localhost:8000/ready
# Expected: {"status": "ready", "database": "connected"}
```

### Step 2: Create Project

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "demo-project", "description": "Release demo project"}'
# Expected: 201 with project ID
```

### Step 3: Create API Key

```bash
# Replace PROJECT_ID from step 2
curl -X POST http://localhost:8000/api/v1/projects/PROJECT_ID/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "demo-key"}'
# Expected: 201 with API key (save it!)
```

### Step 4: Authenticate

```bash
# Replace YOUR_API_KEY from step 3
API_KEY="YOUR_API_KEY"

# Verify authentication works
curl http://localhost:8000/api/v1/runs \
  -H "X-API-Key: $API_KEY"
# Expected: 200 with empty runs list

# Verify unauthenticated access is denied
curl http://localhost:8000/api/v1/runs
# Expected: 401
```

### Step 5: Submit Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "conversation": {
      "model_response": "Ibuprofen can cause stomach upset and drowsiness.",
      "input_tokens": 20,
      "output_tokens": 10
    },
    "context": [
      {"text": "Ibuprofen may cause stomach upset as a common side effect."}
    ],
    "profile": "basic"
  }'
# Expected: 201 with run ID and results
```

### Step 6: Retrieve Result

```bash
# Replace RUN_ID from step 5
curl http://localhost:8000/api/v1/runs/RUN_ID \
  -H "X-API-Key: $API_KEY"
# Expected: 200 with full evaluation results
```

### Step 7: Submit Async Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/evaluations/async \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "items": [
      {"conversation": {"model_response": "Drug X reduces fever."}, "context": [{"text": "Drug X treats fever."}]},
      {"conversation": {"model_response": "Drug Y causes drowsiness."}, "context": [{"text": "Drug Y may cause drowsiness."}]}
    ]
  }'
# Expected: 202 with job ID
```

### Step 8: Monitor Job

```bash
# Replace JOB_ID from step 7
curl http://localhost:8000/api/v1/jobs/JOB_ID \
  -H "X-API-Key: $API_KEY"
# Expected: 200 with job status (queued -> running -> completed)
```

### Step 9: Create Baseline

```bash
curl -X POST http://localhost:8000/api/v1/baselines \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"name": "baseline-v1", "description": "Initial baseline"}' \
  --data-urlencode "run_id=RUN_ID"
# Expected: 201 with baseline ID
```

### Step 10: View Metrics

```bash
curl http://localhost:8000/metrics
# Expected: Prometheus metrics output
```

### Step 11: Open Dashboard

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

## Docker Demo (Full Stack)

```bash
# Start everything
docker compose up --build

# Services: API (8000), Worker, PostgreSQL (5432), Redis (6379)
# Dashboard: cd dashboard && npm run dev

# Production stack with monitoring
docker compose -f docker-compose.prod.yml up --build
# Adds: Prometheus (9090), Grafana (3001)
```

## Verification Checklist

- [ ] Health endpoint returns healthy
- [ ] Database migrations applied
- [ ] Project creation works
- [ ] API key creation works
- [ ] Authentication enforced (401 without key)
- [ ] Sync evaluation returns results
- [ ] Async evaluation returns 202
- [ ] Worker processes jobs
- [ ] Baseline creation works
- [ ] Prometheus metrics endpoint works
- [ ] Dashboard displays data
