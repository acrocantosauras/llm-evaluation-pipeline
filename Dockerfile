FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg and PostgreSQL client
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN useradd --create-home appuser

# Persist the HuggingFace/torch model cache under the user's home so a mounted
# volume (see docker-compose.prod.yml) survives container recreation and models
# are not re-downloaded on every restart.
ENV HF_HOME=/home/appuser/.cache/huggingface
RUN mkdir -p /home/appuser/.cache/huggingface && chown -R appuser:appuser /home/appuser/.cache

USER appuser

EXPOSE 8000

# Default command — override in docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
