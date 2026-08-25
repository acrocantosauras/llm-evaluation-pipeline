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

---

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
