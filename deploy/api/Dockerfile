# ANAC Flight Intelligence v2 — read-only API (FastAPI).
# Build from the repository root, so the data built locally can be copied in:
#   docker build -f deploy/api/Dockerfile -t anac-fi-api .
# Its allowlist is deploy/api/Dockerfile.dockerignore: .env and raw data never enter the build.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANAC_API_HOST=0.0.0.0 \
    ANAC_API_PORT=8000 \
    ANAC_SERVING_DIR=/app/data/serving/v1 \
    ANAC_ANALYTICS_DIR=/app/data/analytics/v1

# LightGBM needs the OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-lock.txt pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements-lock.txt \
    && pip install --no-cache-dir --no-deps .

# Read-only data: payloads (~0.1 MB) and analytical tables (~29 MB), built locally.
COPY data/serving/v1 ./data/serving/v1
COPY data/analytics/v1 ./data/analytics/v1

RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"ANAC_API_PORT\"]}/health', timeout=4)" || exit 1

# The analyst is optional: set GROQ_API_KEY as a secret of the host, never in the image.
CMD ["anac-api"]
