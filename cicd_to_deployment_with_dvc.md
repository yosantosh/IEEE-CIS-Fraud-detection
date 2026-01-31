# Complete Deployment Guide: Development to Production

> **IEEE-CIS Fraud Detection System**  
> **Version**: 3.0 | **Updated**: 2026-01-30

---

## Table of Contents

### Part 1: Foundation
1. [Overview & Architecture](#1-overview--architecture)
2. [DVC with Docker Explained](#2-dvc-with-docker-explained)
3. [Dockerization](#3-dockerization)

### Part 2: CI/CD Pipeline
4. [CI Pipeline Basics](#4-ci-pipeline-basics)

### Part 3: Deployment Options (Choose One)
5. [Option A: Simple EC2 Deployment](#5-option-a-simple-ec2-deployment) - ~$30/month
6. [Option B: AWS EKS (Production)](#6-option-b-aws-eks-production) - ~$180/month
7. [Option C: Azure AKS (Cost-Effective)](#7-option-c-azure-aks-cost-effective) - ~$78/month 💰

### Part 4: Reference
8. [Comparison & Decision Guide](#8-comparison--decision-guide)

---

# PART 1: FOUNDATION

---

# 1. Overview & Architecture

## 1.1 What Are We Building?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FRAUD DETECTION SYSTEM                                │
│                                                                              │
│   CURRENT STATE (Development):                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │   Your Laptop                                                       │   │
│   │   ┌───────────────────────────────────────────────────────────────┐ │   │
│   │   │  python src/api/main.py  ← Runs locally                      │ │   │
│   │   │  dvc repro               ← Trains locally                    │ │   │
│   │   └───────────────────────────────────────────────────────────────┘ │   │
│   │   PROBLEMS:                                                         │   │
│   │   ❌ Only you can access it                                        │   │
│   │   ❌ Dies when laptop shuts down                                   │   │
│   │   ❌ Can't handle many users                                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   TARGET STATE (Production):                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │   Cloud (AWS or Azure)                                              │   │
│   │   ┌───────────────────────────────────────────────────────────────┐ │   │
│   │   │  Docker containers running 24/7                              │ │   │
│   │   │  Auto-scaling based on traffic                               │ │   │
│   │   │  Accessible from anywhere via URL                            │ │   │
│   │   └───────────────────────────────────────────────────────────────┘ │   │
│   │   BENEFITS:                                                         │   │
│   │   ✅ Always available                                              │   │
│   │   ✅ Scales automatically                                          │   │
│   │   ✅ Professional deployment                                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```


**Detailed Breakdown:**
1.  **Development (Your Laptop)**: You write code and run `dvc repro`. This is manual and relies on your machine being on.
2.  **Transition**: We package your environment into **Docker Containers**. This freezes your Python version, dependencies, and code into a portable unit.
3.  **Production (Cloud)**: We run these containers on servers (EC2 or Kubernetes).
    *   **CI/CD** acts as the bridge: It automatically builds the container whenever you push code to GitHub.
    *   **The Cloud** acts as the host: It pulls the new container and runs it.

## 1.2 Two Services We Deploy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TWO MICROSERVICES                                  │
│                                                                              │
│   SERVICE 1: INFERENCE                    SERVICE 2: TRAINING               │
│   ┌───────────────────────────┐          ┌───────────────────────────┐     │
│   │                           │          │                           │     │
│   │  FastAPI Server           │          │  DVC Pipeline             │     │
│   │  • Runs 24/7              │          │  • Runs periodically      │     │
│   │  • Accepts predictions    │          │  • Retrains model         │     │
│   │  • Returns fraud score    │          │  • Updates S3             │     │
│   │                           │          │                           │     │
│   │  Port: 8000               │          │  Schedule: Weekly         │     │
│   │  Endpoint: /predict       │          │  Output: model.pkl        │     │
│   │                           │          │                           │     │
│   └───────────────────────────┘          └───────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```


**How They Connect (The "Loop"):**
1.  **Training Service** runs on a schedule (e.g., weekly).
    *   It pulls new data, retrains, and **pushes the new model artifact** to S3.
2.  **S3 Bucket** acts as the shared storage (The "Handover" point).
3.  **Inference Service** starts up (or restarts).
    *   It **downloads the latest model** from S3 during startup.
    *   It uses this model to answer user requests.

> **Why decouple them?**
> By separating them, your API stays fast and lightweight. It doesn't need to know *how* to train, it just needs the result. The heavy lifting happens in the background Training Service.

## 1.3 Deployment Options at a Glance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        THREE DEPLOYMENT OPTIONS                              │
│                                                                              │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │  OPTION A: EC2      │ │  OPTION B: AWS EKS  │ │  OPTION C: Azure AKS│   │
│  │  (Simple)           │ │  (AWS Production)   │ │  (Cost-Effective)   │   │
│  ├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤   │
│  │                     │ │                     │ │                     │   │
│  │  Single server      │ │  Kubernetes cluster │ │  Kubernetes cluster │   │
│  │  Docker Compose     │ │  Auto-scaling       │ │  Auto-scaling       │   │
│  │  Manual scaling     │ │  Load balancing     │ │  Load balancing     │   │
│  │                     │ │                     │ │                     │   │
│  │  ~$30/month         │ │  ~$180/month        │ │  ~$78/month 💰      │   │
│  │                     │ │                     │ │                     │   │
│  │  Best for:          │ │  Best for:          │ │  Best for:          │   │
│  │  • Learning         │ │  • AWS-heavy teams  │ │  • Budget-conscious │   │
│  │  • Small projects   │ │  • Enterprise       │ │  • Production       │   │
│  │  • Development      │ │  • High traffic     │ │  • Startups         │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 2. DVC with Docker Explained

## 2.1 The Key Question: How Does DVC Work in Docker?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   SIMPLE ANSWER: DVC runs INSIDE the Docker container!                      │
│                                                                              │
│   Docker Container = A mini computer (like a VM)                            │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │   Inside the container:                                                │ │
│   │   • Python is installed                                                │ │
│   │   • Your code is copied                                                │ │
│   │   • DVC is installed                                                   │ │
│   │   • All dependencies are installed                                     │ │
│   │                                                                        │ │
│   │   When container starts, it runs:                                      │ │
│   │   $ dvc repro    ← Works exactly like on your laptop!                 │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```


**The Credential Chain (How DVC gets permission):**
One common confusion is: *How does the container inside the cloud know my AWS passwords?*
1.  **GitHub Secrets**: You store `AWS_ACCESS_KEY_ID` in your GitHub repository settings.
2.  **Injection**: When the CI pipeline runs, it passes these secrets as **Environment Variables** (`-e AWS_ACCESS_KEY_ID=...`) to the container.
3.  **Usage**: Inside the container, DVC reads these environment variables automatically to authenticate with S3. You don't hardcode passwords!

## 2.2 Which Service Uses DVC?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   SERVICE 1: TRAINING                    SERVICE 2: INFERENCE               │
│   ┌───────────────────────────┐         ┌───────────────────────────┐      │
│   │                           │         │                           │      │
│   │  ✅ Uses DVC              │         │  ❌ Does NOT use DVC      │      │
│   │                           │         │                           │      │
│   │  WHY?                     │         │  WHY?                     │      │
│   │  • Needs to run pipeline  │         │  • Just loads model       │      │
│   │  • Data ingestion         │         │  • Makes predictions      │      │
│   │  • Feature engineering    │         │  • No training happens    │      │
│   │  • Model training         │         │                           │      │
│   │                           │         │  LOADS MODEL DIRECTLY:    │      │
│   │  RUNS:                    │         │  s3.download('model.pkl') │      │
│   │  $ dvc pull               │         │  model = joblib.load()    │      │
│   │  $ dvc repro              │         │                           │      │
│   │  $ dvc push               │         │                           │      │
│   │                           │         │                           │      │
│   └───────────────────────────┘         └───────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 3. Dockerization

## 3.1 What is a Dockerfile?

A Dockerfile is a **recipe** that tells Docker how to build your container.

```dockerfile
# ANALOGY: Building a Dockerfile is like setting up a new computer

# Step 1: Choose the operating system
FROM python:3.10-slim     # "Install Ubuntu with Python 3.10"

# Step 2: Set where to work
WORKDIR /app              # "Create and go to /app folder"

# Step 3: Install system tools
RUN apt-get update && apt-get install -y git  # "Install git"

# Step 4: Copy and install Python packages
COPY requirements.txt .   # "Copy requirements file"
RUN pip install -r requirements.txt  # "Install packages"

# Step 5: Copy your code
COPY src/ ./src/          # "Copy your source code"

# Step 6: What to run when container starts
CMD ["python", "main.py"] # "Run this command"
```

## 3.2 Training Dockerfile

```dockerfile
# docker/training.Dockerfile
# ══════════════════════════════════════════════════════════════════════════════
# PURPOSE: Build a container that can run DVC pipeline for model training
# ══════════════════════════════════════════════════════════════════════════════

# Base image with Python
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install DVC with S3 support
RUN pip install dvc dvc-s3

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY dvc.yaml dvc.lock ./
COPY .dvc/ ./.dvc/

# Create directories
RUN mkdir -p artifacts logs

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Entry point script
COPY docker/scripts/run_training.sh .
RUN chmod +x run_training.sh
CMD ["./run_training.sh"]
```


**Key Steps Explained:**
*   `FROM python:3.10-slim`: We use a "slim" image to keep the download size small (fast deployment).
*   `RUN pip install dvc dvc-s3`: We explicitly install `dvc` and its S3 plugin so it can talk to your bucket.
*   `COPY .dvc/ ./.dvc/`: **CRITICAL STEP**. This copies the `.dvc` hidden folder which contains your configuration (where the remote S3 bucket is defined). Without this, DVC won't know where to look.
*   `COPY docker/scripts/run_training.sh`: Instead of running a python script directly, we use a shell script. This allows us to run multiple setup commands (like configuring DVC remotes) before starting the python code.

## 3.3 Training Entry Script

```bash
#!/bin/bash
# docker/scripts/run_training.sh

set -e  # Exit on error

echo "🚀 Starting Training Pipeline..."

# Configure DVC with AWS credentials
dvc remote modify myremote access_key_id $AWS_ACCESS_KEY_ID
dvc remote modify myremote secret_access_key $AWS_SECRET_ACCESS_KEY

# Pull cached data
echo "📥 Pulling cached data..."
dvc pull --allow-missing || true

# Run training pipeline
echo "⚙️ Running DVC pipeline..."
dvc repro

# Push new artifacts
echo "📤 Pushing artifacts to S3..."
dvc push

echo "✅ Training complete!"
```


**Script Logic Breakdown:**
1.  `dvc remote modify ...`: **Dynamic Authentication**. We set the credentials at runtime using the environment variables we injected. This keeps secrets out of the image itself.
2.  `dvc pull --allow-missing`: This downloads the *input data* needed for training from S3. We use `--allow-missing` so it doesn't crash if some optional files are gone, but strictly you might want to remove it for production consistency.
3.  `dvc repro`: The specific command that reads `dvc.yaml` and executes the pipeline (Preprocess -> Transform -> Train).
4.  `dvc push`: After training, a new model file (`model.pkl`) is created. We immediately push this **back to S3** so the Inference Service can find it.

## 3.4 Inference Dockerfile

```dockerfile
# docker/inference.Dockerfile
# ══════════════════════════════════════════════════════════════════════════════
# PURPOSE: Build a container that serves predictions via FastAPI
# NOTE: Does NOT use DVC - loads model directly from S3
# ══════════════════════════════════════════════════════════════════════════════

FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (NO DVC!)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY static/ ./static/       # Frontend assets (HTML, CSS, JS)

# Create model cache directory
RUN mkdir -p /tmp/models

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
```

## 3.5 Docker Compose for Local Testing

```yaml
# docker-compose.yml
# docker-compose.yml
# ===========================================
# Local development and testing for both services
# Usage:
#   docker-compose up inference    → Test API only
#   docker-compose up training     → Run training pipeline
#   docker-compose up              → Run both
# ===========================================

version: '3.10  '

services:
  # =========================================
  # INFERENCE SERVICE (FastAPI)
  # =========================================
  inference:
    build:
      context: .
      dockerfile: docker/inference.Dockerfile
    container_name: fraud-inference
    ports:
      - "8000:8000" # Access at http://localhost:8000
    environment:
      # AWS credentials for fetching model from S3
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
      # Model settings
      - MODEL_CACHE_DIR=/tmp/models
      - S3_BUCKET=${S3_BUCKET:-mlops-capstone-project-final}
    volumes:
      # Optional: mount model cache to persist between restarts (faster dev)
      - model-cache:/tmp/models
    restart: unless-stopped
    healthcheck:
      test: [ "CMD", "curl", "-f", "http://localhost:8000/health" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # =========================================
  # TRAINING SERVICE (DVC Pipeline)
  # =========================================
  training:
    build:
      context: .
      dockerfile: docker/training.Dockerfile
    container_name: fraud-training
    environment:
      # AWS credentials for DVC
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
      # DagsHub/MLflow (if using)
      - DAGSHUB_TOKEN=${DAGSHUB_TOKEN:-}
      - MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI:-}
    volumes:
      # Mount artifacts for inspection after training
      - ./artifacts:/app/artifacts
      - ./models:/app/models
      - ./logs:/app/logs
    # Training runs once and exits (not a long-running service)
    restart: "no"

# Named volumes for persistence
volumes:
  model-cache:
    name: fraud-model-cache

```

## 3.6 .dockerignore

```
# .dockerignore
.git
.dvc/cache
.dvc/tmp
__pycache__
*.pyc
.env
.venv
venv
artifacts/
logs/
*.egg-info
.pytest_cache
.coverage
notebooks/
```

---

# PART 2: CI/CD PIPELINE

---

# 4. CI Pipeline Basics

## 4.1 What is CI/CD?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   CI = Continuous Integration                                                │
│      = Automatically test & build when you push code                        │
│                                                                              │
│   CD = Continuous Deployment                                                 │
│      = Automatically deploy to production                                   │
│                                                                              │
│   FLOW:                                                                      │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│   │  Code   │───▶│  Test   │───▶│  Build  │───▶│  Push   │───▶│ Deploy  │  │
│   │ (push)  │    │ (lint,  │    │ Docker  │    │ to      │    │ to      │  │
│   │         │    │ pytest) │    │ images  │    │ Registry│    │ Cloud   │  │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│                                                                              │
│   WHERE DOES THIS RUN?                                                       │
│   GitHub provides FREE servers (called "runners") to run your CI/CD!        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```


**The "Safety Net" Logic:**
The pipeline is designed to be a **gatekeeper**.
*   **Stage 1: Test**: Before we build anything, we run your tests (`pytest`). If *any* test fails, the pipeline **stops immediately**. Bad code never reaches the build stage.
*   **Stage 2: Build**: Only if tests pass, we build the Docker image.
*   **Stage 3: Push**: We upload the valid image to a registry (like a digital library for your apps).
*   **Stage 4: Deploy**: Finally, we tell the production server "Hey, there's a new verified image, please update."

## 4.2 Basic CI Workflow (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # Job 1: Test the code
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest flake8
      - run: flake8 src/ --max-line-length=120
      - run: pytest tests/ -v || true

  # Job 2: Build Docker images
  build:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      # Registry login and push steps depend on deployment option
      # See specific deployment sections below
```

---

# PART 3: DEPLOYMENT OPTIONS

---

# 5. Option A: Simple EC2 Deployment

> **Cost**: ~$30/month | **Complexity**: ⭐ Easy | **Best for**: Learning, Small Projects

## 5.1 What is EC2?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   EC2 = Elastic Compute Cloud = A virtual server in AWS                     │
│   Think of it as: Renting a computer in Amazon's data center               │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │   Your EC2 Instance (t3.medium = 2 CPU, 4GB RAM)                    │   │
│   │   ┌───────────────────────────────────────────────────────────────┐ │   │
│   │   │   Ubuntu Linux                                                │ │   │
│   │   │   Docker installed                                            │ │   │
│   │   │   Your containers running                                     │ │   │
│   │   │   Public IP: 52.xx.xx.xx                                      │ │   │
│   │   └───────────────────────────────────────────────────────────────┘ │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   PROS:                          CONS:                                       │
│   ✅ Simple setup                ❌ No auto-scaling                         │
│   ✅ Low cost                    ❌ Single point of failure                 │
│   ✅ Full control                ❌ Manual management                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5.2 Step-by-Step Setup

### Step 1: Launch EC2 Instance

```bash
# In AWS Console:
# 1. Go to EC2 → Launch Instance
# 2. Choose: Amazon Linux 2023 or Ubuntu 22.04
# 3. Instance type: t3.medium (2 vCPU, 4GB RAM) - ~$30/month
# 4. Create key pair (download .pem file)
# 5. Security Group: Allow ports 22 (SSH), 80 (HTTP), 8000 (API)
# 6. Launch!
```

### Step 2: Connect and Install Docker

```bash
# Connect to EC2
ssh -i your-key.pem ec2-user@your-ec2-ip

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again
exit
ssh -i your-key.pem ec2-user@your-ec2-ip
```

### Step 3: Deploy Application

```bash
# Create app directory
mkdir -p ~/fraud-detection && cd ~/fraud-detection

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  inference:
    image: ghcr.io/YOUR_USERNAME/YOUR_REPO/fraud-inference:latest
    ports:
      - "8000:8000"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    restart: unless-stopped
EOF

# Create .env file
cat > .env << 'EOF'
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
EOF

# Login to GitHub Container Registry
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Start
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

## 5.3 CI/CD Workflow for EC2

```yaml
# .github/workflows/deploy-ec2.yml
name: Deploy to EC2

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: fraud-inference

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Login to GitHub Container Registry
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      # Build and push
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: ghcr.io/${{ github.repository }}/fraud-inference:latest
      
      # Deploy to EC2
      - uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ec2-user
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd ~/fraud-detection
            docker-compose pull
            docker-compose up -d
            sleep 10
            curl -f http://localhost:8000/health
            echo "✅ Deployed!"
```

**Deployment Mechanism (The "ssh-action"):**
*   **Connection**: GitHub Actions acts as a client. It SSHs into your EC2 server effectively pretending to be you.
*   **The Update**:
    1.  `cd ~/fraud-detection`: Goes to your folder.
    2.  `docker-compose pull`: Downloads the *new* image we just built in the previous job.
    3.  `docker-compose up -d`: Recreates the container using the new image. It's smart enough to only restart containers that changed.
    4.  `curl ...`: A "Health Check" to verify the new version is actually working before entering the deployed state.

## 5.4 GitHub Secrets for EC2

| Secret Name | Value |
|-------------|-------|
| `EC2_HOST` | Your EC2 public IP |
| `EC2_SSH_KEY` | Contents of your .pem file |

---

# 6. Option B: AWS EKS (Production)

> **Cost**: ~$180/month | **Complexity**: ⭐⭐⭐ Complex | **Best for**: Enterprise, High Traffic

## 6.1 What is EKS?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   EKS = Elastic Kubernetes Service = AWS manages Kubernetes for you        │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │   EKS Cluster                                                        │   │
│   │   ┌───────────────────────────────────────────────────────────────┐ │   │
│   │   │   Control Plane (AWS manages)  - $72/month                    │ │   │
│   │   └───────────────────────────────────────────────────────────────┘ │   │
│   │                          │                                           │   │
│   │   ┌───────────────────────────────────────────────────────────────┐ │   │
│   │   │   Worker Nodes (You pay for EC2)                              │ │   │
│   │   │   ┌──────────┐  ┌──────────┐  ┌──────────┐                   │ │   │
│   │   │   │ Pod 1    │  │ Pod 2    │  │ Pod 3    │  ← Auto-scales!   │ │   │
│   │   │   │ Inference│  │ Inference│  │ Inference│                   │ │   │
│   │   │   └──────────┘  └──────────┘  └──────────┘                   │ │   │
│   │   └───────────────────────────────────────────────────────────────┘ │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   COST BREAKDOWN:                                                            │
│   • Control Plane: $72/month                                                 │
│   • Worker Nodes (2x t3.medium): ~$60/month                                 │
│   • Load Balancer: ~$20/month                                               │
│   • ECR Storage: ~$10/month                                                 │
│   TOTAL: ~$162-180/month                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 6.2 AWS ECR: Container Registry

```
┌─────────────────────────────────────────────────────────────────────────────┐
│   ECR = Elastic Container Registry = AWS's Docker Hub                       │
│                                                                              │
│   WHY USE ECR FOR AWS DEPLOYMENTS?                                          │
│   ✅ Faster pulls (same AWS network)                                        │
│   ✅ Native IAM authentication                                              │
│   ✅ No imagePullSecrets needed for EKS                                     │
│   ✅ Built-in vulnerability scanning                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Create ECR Repositories

```bash
# Create repositories
aws ecr create-repository --repository-name fraud-detection/inference --region ap-south-1
aws ecr create-repository --repository-name fraud-detection/training --region ap-south-1

# Get your ECR URI
aws ecr describe-repositories --query 'repositories[*].repositoryUri' --output table
# Output: 123456789012.dkr.ecr.ap-south-1.amazonaws.com/fraud-detection/inference
```

## 6.3 Step-by-Step EKS Setup

### Step 1: Install Tools

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure
aws configure

# Install eksctl
curl -sL "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

### Step 2: Create EKS Cluster (15-20 minutes)

```bash
eksctl create cluster \
  --name fraud-detection \
  --region ap-south-1 \
  --nodegroup-name standard-nodes \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed

# Verify
kubectl get nodes
```

## 6.4 Kubernetes Manifests for EKS

### Namespace & Secrets

```yaml
# kubernetes/aws/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fraud-detection
---
# kubernetes/aws/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: fraud-detection
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "your-key"
  AWS_SECRET_ACCESS_KEY: "your-secret"
  AWS_REGION: "ap-south-1"
  S3_BUCKET: "your-bucket"
```

### Inference Deployment

```yaml
# kubernetes/aws/inference-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
  namespace: fraud-detection
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      containers:
      - name: inference
        image: 123456789012.dkr.ecr.ap-south-1.amazonaws.com/fraud-detection/inference:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        envFrom:
        - secretRef:
            name: aws-credentials
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Service (Load Balancer)

```yaml
# kubernetes/aws/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: inference-service
  namespace: fraud-detection
spec:
  type: LoadBalancer
  selector:
    app: inference
  ports:
  - port: 80
    targetPort: 8000
```

### Horizontal Pod Autoscaler

```yaml
# kubernetes/aws/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
  namespace: fraud-detection
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Training CronJob

```yaml
# kubernetes/aws/training-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: training-pipeline
  namespace: fraud-detection
spec:
  schedule: "0 2 * * 0"  # Every Sunday at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: training
            image: 123456789012.dkr.ecr.ap-south-1.amazonaws.com/fraud-detection/training:latest
            resources:
              requests:
                memory: "8Gi"
                cpu: "2"
            envFrom:
            - secretRef:
                name: aws-credentials
```

## 6.5 CI/CD Workflow for AWS EKS

```yaml
# .github/workflows/deploy-eks.yml
name: Deploy to AWS EKS

on:
  push:
    branches: [main]

env:
  AWS_REGION: ap-south-1
  ECR_REGISTRY: 123456789012.dkr.ecr.ap-south-1.amazonaws.com
  EKS_CLUSTER: fraud-detection

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Configure AWS
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      # Login to ECR
      - uses: aws-actions/amazon-ecr-login@v2
      
      # Build and push
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: ${{ env.ECR_REGISTRY }}/fraud-detection/inference:${{ github.sha }}
      
      # Update kubeconfig
      - run: aws eks update-kubeconfig --name ${{ env.EKS_CLUSTER }}
      
      # Deploy
      - run: |
          kubectl set image deployment/inference-service \
            inference=${{ env.ECR_REGISTRY }}/fraud-detection/inference:${{ github.sha }} \
            -n fraud-detection
          kubectl rollout status deployment/inference-service -n fraud-detection
```

**Deployment Mechanism (Kubernetes Logic):**
*   **Context**: `aws eks update-kubeconfig` authenticates GitHub Actions to talk to your cluster.
*   **The Rolling Update**: `kubectl set image ...` is distinct from the EC2 method.
    1.  It tells Kubernetes: "Change the image for `inference-service` to this new SHA specific version."
    2.  **Graceful Switch**: Kubernetes spins up NEW pods with the new image *while old ones are still running*.
    3.  Only when new pods are "Ready" (passing health checks), it terminates the old ones.
    4.  **Result**: Zero downtime during deployment!

## 6.6 GitHub Secrets for AWS

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | Your AWS Access Key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS Secret Key |

---

# 7. Option C: Azure AKS (Cost-Effective)

> **Cost**: ~$78/month 💰 | **Complexity**: ⭐⭐ Moderate | **Best for**: Budget-Conscious Production

## 7.1 Why AKS is Cheaper

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   💰 AZURE AKS CONTROL PLANE IS FREE!                                        │
│                                                                              │
│   ┌─────────────────────────┬───────────────┬───────────────┐               │
│   │       Component         │   AWS EKS     │   Azure AKS   │               │
│   ├─────────────────────────┼───────────────┼───────────────┤               │
│   │ Control Plane           │   $72/month   │   FREE! 🎉     │               │
│   │ Worker Nodes (2x)       │   $60/month   │   $55/month   │               │
│   │ Load Balancer           │   $20/month   │   $18/month   │               │
│   │ Container Registry      │   $10/month   │   $5/month    │               │
│   ├─────────────────────────┼───────────────┼───────────────┤               │
│   │ TOTAL                   │  ~$162/month  │  ~$78/month   │               │
│   └─────────────────────────┴───────────────┴───────────────┘               │
│                                                                              │
│   💡 Save ~$84/month ($1000/year) with same Kubernetes features!            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Azure Equivalents

| AWS | Azure |
|-----|-------|
| S3 | Azure Blob Storage |
| ECR | Azure Container Registry (ACR) |
| EKS | Azure Kubernetes Service (AKS) |
| IAM | Azure Active Directory |

## 7.3 Step-by-Step AKS Setup

### Step 1: Install Azure CLI

```bash
# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login
```

### Step 2: Create Resources

```bash
# Variables
RESOURCE_GROUP="fraud-detection-rg"
LOCATION="centralindia"
ACR_NAME="frauddetectionacr"
CLUSTER_NAME="fraud-detection-aks"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# Get ACR credentials (for CI/CD)
az acr credential show --name $ACR_NAME
```

### Step 3: Create AKS Cluster (5-10 minutes)

```bash
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --node-count 2 \
    --node-vm-size Standard_B2s \
    --enable-managed-identity \
    --attach-acr $ACR_NAME \
    --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME

# Verify
kubectl get nodes
```

## 7.4 Kubernetes Manifests for AKS

### Namespace & Secrets

```yaml
# kubernetes/azure/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fraud-detection
---
# kubernetes/azure/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: fraud-detection
type: Opaque
stringData:
  # Use AWS S3 or Azure Blob Storage
  AWS_ACCESS_KEY_ID: "your-key"
  AWS_SECRET_ACCESS_KEY: "your-secret"
  AWS_REGION: "ap-south-1"
  S3_BUCKET: "your-bucket"
```

### Inference Deployment

```yaml
# kubernetes/azure/inference-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
  namespace: fraud-detection
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      containers:
      - name: inference
        image: frauddetectionacr.azurecr.io/fraud-detection/inference:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        envFrom:
        - secretRef:
            name: app-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
```

### Service & HPA

```yaml
# kubernetes/azure/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: inference-service
  namespace: fraud-detection
spec:
  type: LoadBalancer
  selector:
    app: inference
  ports:
  - port: 80
    targetPort: 8000
---
# kubernetes/azure/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
  namespace: fraud-detection
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 7.5 CI/CD Workflow for Azure AKS

```yaml
# .github/workflows/deploy-aks.yml
name: Deploy to Azure AKS

on:
  push:
    branches: [main]

env:
  ACR_NAME: frauddetectionacr
  ACR_LOGIN_SERVER: frauddetectionacr.azurecr.io
  RESOURCE_GROUP: fraud-detection-rg
  CLUSTER_NAME: fraud-detection-aks

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Login to ACR
      - uses: azure/docker-login@v1
        with:
          login-server: ${{ env.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      
      # Build and push
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: ${{ env.ACR_LOGIN_SERVER }}/fraud-detection/inference:${{ github.sha }}
      
      # Azure login
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      # Get AKS credentials
      - run: |
          az aks get-credentials \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --name ${{ env.CLUSTER_NAME }}
      
      # Deploy
      - run: |
          kubectl set image deployment/inference-service \
            inference=${{ env.ACR_LOGIN_SERVER }}/fraud-detection/inference:${{ github.sha }} \
            -n fraud-detection
          kubectl rollout status deployment/inference-service -n fraud-detection
```


**Deployment Mechanism (Azure Logic):**
*   **Context**: `az aks get-credentials` authenticates GitHub Actions to talk to your Azure cluster.
*   **The Rolling Update**: Exactly the same as AWS! `kubectl` is cloud-agnostic.
    1.  `kubectl set image ...` triggers the update.
    2.  Kubernetes (AKS) starts new pods.
    3.  Old pods are terminated only after new ones are healthy.
    4.  **Result**: Seamless zero-downtime deployment.

## 7.6 GitHub Secrets for Azure


| Secret Name | How to Get |
|-------------|------------|
| `ACR_USERNAME` | `az acr credential show --name frauddetectionacr` |
| `ACR_PASSWORD` | Same command, copy password |
| `AZURE_CREDENTIALS` | See below |

### Create Azure Service Principal

```bash
az ad sp create-for-rbac \
    --name "github-actions-fraud-detection" \
    --role contributor \
    --scopes /subscriptions/{subscription-id}/resourceGroups/fraud-detection-rg \
    --sdk-auth

# Copy the JSON output as AZURE_CREDENTIALS secret
```

---

# PART 4: REFERENCE

---

# 8. Comparison & Decision Guide

## 8.1 Full Comparison

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT OPTIONS COMPARISON                         │
│                                                                               │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐  │
│  │     Aspect      │  EC2 (Simple)   │   AWS EKS       │   Azure AKS     │  │
│  ├─────────────────┼─────────────────┼─────────────────┼─────────────────┤  │
│  │ Cost/month      │  ~$30           │  ~$180          │  ~$78 💰        │  │
│  │ Control Plane   │  N/A            │  $72            │  FREE ✅        │  │
│  │ Complexity      │  ⭐ Easy         │  ⭐⭐⭐ Hard       │  ⭐⭐ Medium     │  │
│  │ Auto-scaling    │  ❌ Manual       │  ✅ Automatic    │  ✅ Automatic   │  │
│  │ High Avail.     │  ❌ No           │  ✅ Yes          │  ✅ Yes         │  │
│  │ Load Balancer   │  ❌ Manual       │  ✅ Built-in     │  ✅ Built-in    │  │
│  │ Registry        │  GHCR           │  ECR            │  ACR            │  │
│  └─────────────────┴─────────────────┴─────────────────┴─────────────────┤  │
│                                                                               │
│  💡 RECOMMENDATION:                                                           │
│  ├─ Learning/Dev:      EC2 (~$30/month)                                      │
│  ├─ Production Budget: Azure AKS (~$78/month) ← BEST VALUE                   │
│  └─ AWS Enterprise:    AWS EKS (~$180/month)                                 │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 8.2 Quick Command Reference

```bash
# ═══════════════════════════════════════════════════════════════════════════
# EC2 COMMANDS
# ═══════════════════════════════════════════════════════════════════════════
ssh -i key.pem ec2-user@EC2_IP              # Connect
docker-compose up -d                         # Start
docker-compose logs -f                       # View logs
docker-compose pull && docker-compose up -d  # Update

# ═══════════════════════════════════════════════════════════════════════════
# AWS EKS COMMANDS
# ═══════════════════════════════════════════════════════════════════════════
aws eks update-kubeconfig --name fraud-detection
kubectl get all -n fraud-detection
kubectl logs -f deploy/inference-service -n fraud-detection
kubectl rollout restart deploy/inference-service -n fraud-detection

# ═══════════════════════════════════════════════════════════════════════════
# AZURE AKS COMMANDS
# ═══════════════════════════════════════════════════════════════════════════
az aks get-credentials --resource-group fraud-detection-rg --name fraud-detection-aks
kubectl get all -n fraud-detection
kubectl get svc inference-service -n fraud-detection  # Get public IP
```

## 8.3 Project File Structure

```
IEEE-CIS-Fraud-detection/
├── docker/
│   ├── training.Dockerfile
│   ├── inference.Dockerfile
│   └── scripts/
│       └── run_training.sh
├── .github/workflows/
│   ├── deploy-ec2.yml        # Option A
│   ├── deploy-eks.yml        # Option B
│   └── deploy-aks.yml        # Option C
├── kubernetes/
│   ├── aws/                  # Option B manifests
│   │   ├── namespace.yaml
│   │   ├── secrets.yaml
│   │   ├── inference-deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── training-cronjob.yaml
│   └── azure/                # Option C manifests
│       ├── namespace.yaml
│       ├── secrets.yaml
│       ├── inference-deployment.yaml
│       ├── service.yaml
│       └── hpa.yaml
├── docker-compose.yml        # Local development
└── .dockerignore
```

---

> **Next Steps:**
> 1. ✅ Read this guide completely
> 2. 📦 Create Dockerfiles and test locally
> 3. 🎯 Choose your deployment option (A, B, or C)
> 4. 🚀 Set up CI/CD and deploy!
