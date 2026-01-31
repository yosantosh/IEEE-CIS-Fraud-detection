# Stage 1: Builder
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
# build-essential: for compiling python packages
# git: for installing git-based dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.13-slim as runtime

WORKDIR /app

# Install runtime dependencies
# git: required by DVC operations
# libgomp1: required by XGBoost/Sklearn
RUN apt-get update && apt-get install -y \
    git \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY dvc.yaml ./
COPY .dvc/ ./.dvc/

# Create directories
RUN mkdir -p artifacts logs models

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Entry point script
COPY docker/scripts/run_training.sh .
RUN chmod +x run_training.sh
CMD ["./run_training.sh"]


