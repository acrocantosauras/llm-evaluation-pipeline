# LLM Response Evaluation Framework

A compact, production-minded framework to evaluate LLM responses for:
- relevance to reference/context,
- hallucination / factual consistency (via NLI),
- simple latency measurement,
- token-cost estimation.

## Features
- Embedding-based relevance scoring (`sentence-transformers`).
- NLI-based hallucination checks (configurable model).
- Lightweight latency utility and token-cost estimator.
- Example data, unit tests, CI workflow and Dockerfile.

## Quickstart

1. Create & activate a virtual environment:
   ```bash
   python -m venv .venv
   # Git Bash / Linux:
   source .venv/bin/activate
   # PowerShell:
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the example entrypoint:
   ```bash
   python -m src.main
   ```
