# Deployment Guide

## Local Development

### Prerequisites
- Python 3.10+
- PostgreSQL 16+
- Redis 7+
- Node.js 18+ (for dashboard)

### Quick Start

```bash
# Clone and setup
git clone https://github.com/acrocantosauras/llm-evaluation-pipeline.git
cd llm-evaluation-pipeline
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Start infrastructure via Docker Compose
docker compose up -d postgres redis

# Initialize database
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start the worker
arq app.worker.WorkerSettings

# Start the dashboard
cd dashboard && npm install && npm run dev
```

### Access Points
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Dashboard: http://localhost:3000
- Prometheus: http://localhost:9090 (with docker-compose.prod.yml)
- Grafana: http://localhost:3001 (with docker-compose.prod.yml)

---

## Docker Compose (Development)

```bash
docker compose up --build
```

Services:
- `api` — FastAPI application on port 8000
- `worker` — Background evaluation worker
- `postgres` — PostgreSQL 16 on port 5432
- `redis` — Redis 7 on port 6379

---

## Docker Compose (Production)

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Additional services:
- `prometheus` — Metrics collection on port 9090
- `grafana` — Metrics visualization on port 3001

**Required environment variables:**
```bash
POSTGRES_PASSWORD=<strong-password>
GRAFANA_PASSWORD=<admin-password>
```

---

## Cloud Deployment

### Recommended Architecture

```
Internet
   │
   ▼
Load Balancer (nginx/Cloudflare)
   │
   ├── API Container(s)
   │     └── uvicorn + FastAPI
   │
   ├── Worker Container(s)
   │     └── arq background worker
   │
   ├── Dashboard Container
   │     └── Next.js (static export)
   │
   ├── PostgreSQL (managed)
   │     └── AWS RDS / GCP Cloud SQL / Supabase
   │
   ├── Redis (managed)
   │     └── AWS ElastiCache / Upstash / Redis Cloud
   │
   └── Observability
         ├── Prometheus (metrics)
         └── Grafana (dashboards)
```

### Environment Variables (Production)

```bash
APP_ENV=production
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
POSTGRES_PASSWORD=<from-secrets>
CORS_ORIGINS=["https://your-domain.com"]
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_WINDOW=60
PROMETHEUS_ENABLED=true
```

### Free/Cheap Deployment Options

| Service | Free Tier | Notes |
|---------|-----------|-------|
| Render | Yes | Docker deployment, managed PostgreSQL |
| Railway | $5 credit | Good for demos |
| Fly.io | Yes (limited) | Docker-based, Postgres available |
| Vercel (dashboard) | Yes | Static export of Next.js |

---

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Check current version
alembic current

# Generate a new migration
alembic revision --autogenerate -m "description"

# Rollback last migration
alembic downgrade -1
```

---

## Operations

### Backup & Restore

```bash
# Backup
pg_dump -h localhost -U postgres llm_eval > backup.sql

# Restore
psql -h localhost -U postgres llm_eval < backup.sql
```

### API Key Rotation
1. Create new key: `POST /api/v1/projects/{id}/api-keys`
2. Update clients with new key
3. Revoke old key: `DELETE /api/v1/projects/{id}/api-keys/{key_id}`

### Worker Restart
Workers automatically reconnect to Redis and resume from the queue.
No data loss occurs during restart.

### Redis Recovery
Redis stores only ephemeral job state (queue + progress). All persistent
data is in PostgreSQL. If Redis data is lost:
- Queued jobs need to be re-submitted
- Job progress will be unavailable for in-flight jobs
- No evaluation results are lost

---

## Security

- API keys are stored as SHA-256 hashes (never plaintext)
- Full key shown only once at creation time
- All credentials via environment variables
- CORS restricted to configured origins
- Rate limiting on API endpoints
- Request-size limits via FastAPI/Uvicorn
- Non-root Docker containers
- Parameterized database queries (SQLAlchemy ORM)
