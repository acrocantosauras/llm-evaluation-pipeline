# Architecture Overview

## Components

### 1. Relevance Scoring
Uses sentence-transformer embeddings and cosine similarity to evaluate semantic closeness between LLM output and context.

### 2. Hallucination Detection
Uses a Natural Language Inference model (MNLI) to classify sentences as:
- Supported
- Contradicted
- Unsupported

### 3. Latency Measurement
Lightweight timer utility to measure inference time.

### 4. Token Cost Estimation
Estimates cost based on input/output token count and configurable pricing.

## Scaling Notes
- Cache embeddings
- Use ONNX runtime for faster NLI inference
- Batch NLI queries
