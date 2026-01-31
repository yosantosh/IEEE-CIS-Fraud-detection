# Stage 1: Builder
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
# build-essential: for compiling python packages if wheels aren't valid
# git: for installing git dependencies if any
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies into venv
COPY requirements-inference.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime
FROM python:3.13-slim as runtime

WORKDIR /app

# Install minimal runtime dependencies
# libgomp1: often required by xgboost/scikit-learn
# curl: for healthcheck
RUN apt-get update && apt-get install -y \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY static/ ./static/

# Create model cache directory
RUN mkdir -p /tmp/models && chmod 777 /tmp/models

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MODEL_CACHE_DIR=/tmp/models

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI server
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]