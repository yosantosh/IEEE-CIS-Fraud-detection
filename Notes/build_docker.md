# 🐳 Complete Guide to Dockerization

This document serves as the master guide for how we containerized the IEEE-CIS Fraud Detection project. It covers the **Why**, the **How**, and provides detailed code explanations for every decision made.

---

## 🏗 The Architecture: Why Docker?

Before Docker, we ran code on our laptops. If it worked for me, it might break for you because you have a different Python version or missing libraries.

**Docker solves "It works on my machine"** by packaging the OS, Python, libraries, and code into a single immutable artifact called an **Image**.

### Our Strategy: Two Containers, One Purpose
We employ a **Microservices pattern**. Instead of one giant container that does everything, we split concerns:

1.  **Training Container**: A heavy worker.
    - **Job**: Pull data -> Train Model -> Push Model.
    - **Lifecycle**: Starts -> Works -> Dies (Ephemeral).
    - **Needs**: Git, DVC, Compilers, Heavy Configs.

2.  **Inference Container**: A lightweight server.
    - **Job**: Receive JSON -> Predict -> Return JSON.
    - **Lifecycle**: Runs forever (Long-running service).
    - **Needs**: Speed, Stability, minimal libraries.

---

## 🛠 1. The Training Dockerfile
**File Path**: `docker/training.Dockerfile`

This image essentially "automates the developer". It simulates a human setting up a brand new machine and running the training pipeline.

### The Code
```dockerfile
# -----------------------------------------------
# STAGE 1: THE BUILDER (Heavy Lifting)
# -----------------------------------------------
FROM python:3.13-slim as builder

WORKDIR /app

# 1. Install System Compilers
# We need 'build-essential' (gcc) to compile some python libraries (like numpy/pandas extensions)
# We need 'git' because some pip packages might install from git
RUN apt-get update && apt-get install -y build-essential git

# 2. Create Virtual Environment
# We isolate python packages in /opt/venv so we can copy them easily later
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Install Python Dependencies
# --no-cache-dir helps reduce image size by not storing the cached wheels
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# -----------------------------------------------
# STAGE 2: THE RUNTIME (Clean & Lean)
# -----------------------------------------------
FROM python:3.13-slim as runtime

WORKDIR /app

# 4. Install Runtime-Only System Libs
# 'git': Required by DVC to check file hashes
# 'libgomp1': Required explicitly by XGBoost (it's a C dependency)
RUN apt-get update && apt-get install -y git libgomp1

# 5. Copy the Environment
# We grab the pre-built environment from the 'builder' stage.
# We do NOT bring the compilers (gcc) with us.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 6. Copy Application Code
# We copy specific folders. Notice we DO NOT copy 'artifacts/' or 'models/'.
# Why? precise copying prevents accidental data leakage into the image.
COPY src/ ./src/
COPY config/ ./config/
COPY dvc.yaml ./
COPY .dvc/ ./.dvc/

# Configure Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 7. The Entrypoint
# When this container starts, it executes this shell script.
COPY docker/scripts/run_training.sh .
CMD ["./run_training.sh"]
```

### The `run_training.sh` Logic
How does the container train if it has no data? The entrypoint script handles the magic:
```bash
#!/bin/bash
# 1. Initialize empty git (DVC requires git to work)
git init

# 2. Pull Data from S3 (using keys provided at runtime)
dvc pull

# 3. Run Pipeline
dvc repro

# 4. Push new model to S3
dvc push
```

---

## 🚀 2. The Inference Dockerfile
**File Path**: `docker/inference.Dockerfile`

This image is optimized for serving requests. It skips DVC entirely because browsing S3 for raw csv files is slow and unnecessary for prediction.

### The Code
```dockerfile
# (Builder stage is similar to training, skipped for brevity...)

FROM python:3.13-slim as runtime
WORKDIR /app

# 1. System Dependencies
# 'curl': Useful for healthchecks (pinging localhost:8000/health)
# 'libgomp1': For XGBoost
RUN apt-get update && apt-get install -y curl libgomp1

# 2. Copy Environment & Code
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY src/ ./src/
COPY config/ ./config/
# Note: NO dvc.yaml, NO .dvc folder. This image is blind to DVC.

# 3. Model Caching Setup
# Local code looks in 'models/'. Docker needs a writable location.
# We use /tmp because it's guaranteed to be writable in all environments (AWS/Azure).
ENV MODEL_CACHE_DIR=/tmp/models
RUN mkdir -p /tmp/models && chmod 777 /tmp/models

# 4. Start the Server
# Host 0.0.0.0 is crucial! It means "listen on all network interfaces".
# if you use 127.0.0.1 in Docker, you can't access it from outside!
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧠 Deep Dive: Optimization Techniques

### technique 1: Multi-Stage Builds
**Problem**: Installing `pandas` requires `gcc` (Compiler). `gcc` is huge (100MB+).
**Solution**:
- Stage 1 (Builder): Install `gcc`, build `pandas`.
- Stage 2 (Runtime): Copy `pandas` files. Throw away `gcc`.
**Result**: Image size reduced by ~40%.

### Technique 2: Layer Caching
Docker builds in layers. If you change a line of code, Docker has to rebuild from that line down.
**Smart Ordering**:
1. Copy `requirements.txt`
2. Run `pip install`
3. Copy `src/` (Code)

By doing it in this order, if we change our python code (`src/`), Docker **skips** re-installing dependencies because `requirements.txt` didn't change. This makes builds take seconds instead of minutes.

### Technique 3: `.dockerignore`
We added a `.dockerignore` file (similar to `.gitignore`).
It prevents heavy folders like `artifacts/` (datasets) or `__pycache__` from being accidentally uploaded to the Docker daemon during build context sending. This speeds up the start of the build.

---

## 🎮 How to Control These Beasts

### Building
```bash
# Build Training
docker build -t fraud-training -f docker/training.Dockerfile .

# Build Inference
docker build -t fraud-inference -f docker/inference.Dockerfile .
```

### Running Inference Locally
To simulate production on your laptop:
```bash
# We pass .env so it can download the model from S3 on startup
docker run -p 8000:8000 --env-file .env fraud-inference
```
*Now open localhost:8000/docs to see your API.*

### Running Training Locally
To test the pipeline inside Docker:
```bash
docker run --env-file .env fraud-training
```
*Watch the logs as it pulls data, trains, and pushes the model.*
