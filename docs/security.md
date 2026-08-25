# Security

## Authentication

API key-based authentication using SHA-256 hashed keys.

### How It Works

1. **Create a project**: `POST /api/v1/projects`
2. **Generate API key**: `POST /api/v1/projects/{id}/api-keys`
   - Full key returned ONCE (e.g., `llm_eval_abc123...`)
   - Stored hash: `SHA-256(key)`
3. **Authenticate requests**: Include in header
   ```
   X-API-Key: llm_eval_abc123...
   # or
   Authorization: Bearer llm_eval_abc123...
   ```

### Development Mode
When `APP_ENV=development`, unauthenticated requests are allowed
and fall back to the first available project.

## Project Isolation

Every resource (runs, jobs, baselines, quality gates) is scoped to a project.
API keys from Project A cannot access Project B's data.

## Rate Limiting

Configurable per-project rate limiting:
- `RATE_LIMIT_REQUESTS`: Max requests per window (default: 100)
- `RATE_LIMIT_WINDOW`: Window in seconds (default: 60)

Health and readiness endpoints are NOT rate-limited.

## Secrets Management

- Never commit `.env` files
- Use environment variables for all credentials
- `.env.example` contains only safe defaults
- Database credentials come from environment
- LLM API keys (judge) come from environment
- No secrets in logs or error responses

## Input Validation

- All API inputs validated via Pydantic schemas
- Request body size limits enforced by Uvicorn
- SQL injection prevented by SQLAlchemy ORM
- No arbitrary code execution paths

## Docker Security

- Containers run as non-root user (`appuser`)
- Minimal base images (python:3.11-slim, alpine)
- No unnecessary packages installed
- Health checks for all services

## Error Handling

- Internal exceptions logged with full context
- API responses return generic error messages
- No stack traces exposed to clients
- Request IDs for correlation without information leakage
