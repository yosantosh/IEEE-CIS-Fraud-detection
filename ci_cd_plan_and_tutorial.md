# CI/CD Complete Tutorial & Implementation Plan

> **Document Version**: 1.0  
> **Created**: 2026-01-30  
> **For**: IEEE-CIS Fraud Detection Project

---

## Table of Contents

1. [What is CI/CD? (Theory)](#part-1-what-is-cicd-theory)
2. [GitHub Actions Fundamentals](#part-2-github-actions-fundamentals)
3. [CI/CD Pipeline Design for Our Project](#part-3-cicd-pipeline-design-for-our-project)
4. [Deployment Strategies](#part-4-deployment-strategies)
5. [Implementation Guide](#part-5-implementation-guide)

---

# Part 1: What is CI/CD? (Theory)

## 1.1 The Problem CI/CD Solves

```
TRADITIONAL DEVELOPMENT (Without CI/CD):
═══════════════════════════════════════

Developer A ──┐
Developer B ──┼──▶ Manual Integration ──▶ Manual Testing ──▶ Manual Deploy
Developer C ──┘         │                      │                  │
                        ▼                      ▼                  ▼
                   "It works on              Bugs found        Deployment
                    my machine!"              too late          failures
                   
PROBLEMS:
❌ Integration conflicts discovered late
❌ Manual testing is slow and error-prone
❌ Deployment is risky and stressful
❌ Long feedback loops (days/weeks)
```

```
MODERN DEVELOPMENT (With CI/CD):
════════════════════════════════

Developer A ──┐                    ┌──▶ Auto Build
Developer B ──┼──▶ Git Push ──▶ CI ├──▶ Auto Test   ──▶ CD ──▶ Auto Deploy
Developer C ──┘                    └──▶ Auto Lint
                                            │
                                            ▼
                                   Feedback in minutes!
                                   
BENEFITS:
✅ Immediate feedback on code changes
✅ Consistent, repeatable builds
✅ Automated testing catches bugs early
✅ Reliable, stress-free deployments
```

---

## 1.2 CI vs CD Explained

### Continuous Integration (CI)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONTINUOUS INTEGRATION (CI)                           │
│                                                                              │
│  "Integrate code changes frequently and verify each integration"            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          TRIGGER                                        ││
│  │                                                                          ││
│  │   Developer pushes code ──▶ GitHub receives push ──▶ CI Pipeline starts ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          CI PIPELINE                                     ││
│  │                                                                          ││
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ ││
│  │   │  Clone   │─▶│  Install │─▶│   Lint   │─▶│   Test   │─▶│  Build   │ ││
│  │   │   Repo   │  │   Deps   │  │   Code   │  │   Code   │  │ Artifact │ ││
│  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          RESULT                                          ││
│  │                                                                          ││
│  │   ✅ PASS: Code is good, ready for next stage                           ││
│  │   ❌ FAIL: Developer notified, must fix before merge                    ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘

CI ACTIVITIES:
• Code compilation/build
• Unit tests
• Integration tests
• Code linting (style checks)
• Security scanning
• Docker image building
```

### Continuous Delivery vs Continuous Deployment (CD)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONTINUOUS DELIVERY                                     │
│                                                                              │
│  "Automatically prepare releases, but deploy MANUALLY"                      │
│                                                                              │
│   CI ──▶ Build ──▶ Test ──▶ Stage ──▶ [MANUAL APPROVAL] ──▶ Production     │
│                                              │                               │
│                                       Human clicks                           │
│                                       "Deploy" button                        │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Regulatory requirements need human approval                              │
│  • You want control over release timing                                     │
│  • High-risk applications (banking, healthcare)                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONTINUOUS DEPLOYMENT                                   │
│                                                                              │
│  "Automatically deploy EVERY change that passes tests"                      │
│                                                                              │
│   CI ──▶ Build ──▶ Test ──▶ Stage ──▶ Auto Deploy ──▶ Production           │
│                                           │                                  │
│                                    No human needed!                          │
│                                                                              │
│  USE WHEN:                                                                   │
│  • Fast iteration is important                                              │
│  • Strong test coverage gives confidence                                    │
│  • Team is mature and experienced                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1.3 The Complete CI/CD Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       COMPLETE CI/CD PIPELINE                                │
│                                                                              │
│   PHASE 1: SOURCE                                                            │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Developer ──▶ Commit ──▶ Push to GitHub ──▶ Pull Request           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   PHASE 2: BUILD (CI)                                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Checkout ──▶ Install Dependencies ──▶ Compile/Build                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   PHASE 3: TEST (CI)                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Unit Tests ──▶ Integration Tests ──▶ Code Quality ──▶ Security     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   PHASE 4: PACKAGE                                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Build Docker Image ──▶ Push to Container Registry (ECR/GHCR)       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   PHASE 5: DEPLOY (CD)                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Deploy to Staging ──▶ Run Smoke Tests ──▶ Deploy to Production     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   PHASE 6: MONITOR                                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Health Checks ──▶ Metrics ──▶ Alerts ──▶ Rollback if needed        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# Part 2: GitHub Actions Fundamentals

## 2.1 What is GitHub Actions?

GitHub Actions is GitHub's built-in CI/CD platform. It runs your pipelines on GitHub's servers (or your own).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GITHUB ACTIONS ARCHITECTURE                            │
│                                                                              │
│   YOUR REPOSITORY                          GITHUB'S SERVERS                  │
│   ┌────────────────────┐                   ┌────────────────────────────┐   │
│   │  .github/          │                   │       RUNNERS               │   │
│   │  └── workflows/    │   ──Triggers──▶   │                            │   │
│   │      └── ci.yml    │                   │  ubuntu-latest ───────┐    │   │
│   │                    │                   │  windows-latest ──────┤    │   │
│   │  src/              │                   │  macos-latest ────────┤    │   │
│   │  tests/            │                   │  self-hosted ─────────┘    │   │
│   │  ...               │                   │                            │   │
│   └────────────────────┘                   │  Your workflow runs here!  │   │
│                                            └────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Key Concepts

```yaml
# .github/workflows/example.yml

name: My First Pipeline          # WORKFLOW NAME

on:                              # TRIGGERS - When to run
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:                            # JOBS - What to run
  build:                         # JOB NAME
    runs-on: ubuntu-latest       # RUNNER - Where to run
    
    steps:                       # STEPS - Individual tasks
      - name: Checkout code
        uses: actions/checkout@v4    # ACTION - Reusable task
        
      - name: Run custom command
        run: echo "Hello World"      # RUN - Shell command
```

### Concept Breakdown:

| Concept | Description | Example |
|---------|-------------|---------|
| **Workflow** | The entire pipeline defined in a YAML file | `ci.yml` |
| **Trigger** | Events that start the workflow | `push`, `pull_request`, `schedule` |
| **Job** | A set of steps that run on the same runner | `build`, `test`, `deploy` |
| **Step** | Individual task within a job | Checkout, Install, Test |
| **Action** | Reusable unit of code | `actions/checkout@v4` |
| **Runner** | Server that executes your workflow | `ubuntu-latest`, self-hosted |

## 2.3 Workflow Syntax Deep Dive

```yaml
name: Complete Example

# ═══════════════════════════════════════════════════════════════════════════
# TRIGGERS
# ═══════════════════════════════════════════════════════════════════════════
on:
  # Run on push to main
  push:
    branches: [main]
    paths:
      - 'src/**'           # Only if src/ files changed
      - '!**.md'           # Ignore markdown files
  
  # Run on PRs to main
  pull_request:
    branches: [main]
  
  # Run on schedule (cron)
  schedule:
    - cron: '0 2 * * 0'    # Every Sunday at 2 AM
  
  # Manual trigger
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'

# ═══════════════════════════════════════════════════════════════════════════
# ENVIRONMENT VARIABLES (available to all jobs)
# ═══════════════════════════════════════════════════════════════════════════
env:
  PYTHON_VERSION: '3.10'
  REGISTRY: ghcr.io

# ═══════════════════════════════════════════════════════════════════════════
# JOBS
# ═══════════════════════════════════════════════════════════════════════════
jobs:
  # ─────────────────────────────────────────────────────────────────────────
  # JOB 1: Build and Test
  # ─────────────────────────────────────────────────────────────────────────
  build:
    name: Build & Test
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'        # Cache pip dependencies
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: coverage.xml

  # ─────────────────────────────────────────────────────────────────────────
  # JOB 2: Build Docker Image
  # ─────────────────────────────────────────────────────────────────────────
  docker:
    name: Build Docker Image
    needs: build              # Wait for build job to complete
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # Only on main branch
    
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ github.repository }}
          tags: |
            type=sha
            type=raw,value=latest
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ─────────────────────────────────────────────────────────────────────────
  # JOB 3: Deploy
  # ─────────────────────────────────────────────────────────────────────────
  deploy:
    name: Deploy to Production
    needs: docker
    runs-on: ubuntu-latest
    environment: production    # Requires approval
    
    steps:
      - name: Deploy to server
        run: echo "Deploying ${{ needs.docker.outputs.image_tag }}"
```

---

# Part 3: CI/CD Pipeline Design for Our Project

## 3.1 Where CI/CD Fits in Our Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CI/CD IN OUR FRAUD DETECTION SYSTEM                       │
│                                                                              │
│   DEVELOPER WORKFLOW:                                                        │
│                                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────────────────────────────────────┐ │
│   │  Code   │───▶│  Push   │───▶│           GITHUB ACTIONS                │ │
│   │ Change  │    │   to    │    │                                          │ │
│   │         │    │  GitHub │    │  ┌──────────────────────────────────┐   │ │
│   └─────────┘    └─────────┘    │  │            CI STAGE              │   │ │
│                                 │  │                                   │   │ │
│                                 │  │  1. Checkout code                │   │ │
│                                 │  │  2. Install dependencies         │   │ │
│                                 │  │  3. Run linting (flake8)         │   │ │
│                                 │  │  4. Run unit tests (pytest)      │   │ │
│                                 │  │  5. Build Docker images          │   │ │
│                                 │  │  6. Push to Container Registry   │   │ │
│                                 │  │                                   │   │ │
│                                 │  └──────────────────────────────────┘   │ │
│                                 │                    │                     │ │
│                                 │                    ▼                     │ │
│                                 │  ┌──────────────────────────────────┐   │ │
│                                 │  │            CD STAGE              │   │ │
│                                 │  │                                   │   │ │
│                                 │  │  Option A: GitHub Runner          │   │ │
│                                 │  │  ─────────────────────────        │   │ │
│                                 │  │  Deploy to Kubernetes (kubectl)  │   │ │
│                                 │  │                                   │   │ │
│                                 │  │  Option B: AWS EC2                │   │ │
│                                 │  │  ──────────────                   │   │ │
│                                 │  │  SSH to EC2 + docker-compose     │   │ │
│                                 │  │                                   │   │ │
│                                 │  └──────────────────────────────────┘   │ │
│                                 │                                          │ │
│                                 └──────────────────────────────────────────┘ │
│                                                    │                         │
│                                                    ▼                         │
│                           ┌────────────────────────────────────────────────┐ │
│                           │              PRODUCTION                         │ │
│                           │                                                 │ │
│                           │  ┌─────────────────┐  ┌─────────────────────┐  │ │
│                           │  │   Training      │  │    Inference        │  │ │
│                           │  │   Service       │  │    Service          │  │ │
│                           │  │   (CronJob)     │  │    (Deployment+HPA) │  │ │
│                           │  └─────────────────┘  └─────────────────────┘  │ │
│                           │                                                 │ │
│                           └────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Our CI/CD Stages

| Stage | What Happens | Tools |
|-------|--------------|-------|
| **Source** | Code pushed to GitHub | Git, GitHub |
| **Build** | Dependencies installed, code compiled | pip, Python |
| **Test** | Unit tests, integration tests, linting | pytest, flake8 |
| **Package** | Docker images built and pushed | Docker, GHCR/ECR |
| **Deploy** | Application deployed to servers | kubectl, SSH, docker-compose |
| **Verify** | Smoke tests, health checks | curl, pytest |

---

# Part 4: Deployment Strategies

## 4.1 Option A: Deploy with GitHub-Hosted Runners

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   DEPLOYMENT VIA GITHUB-HOSTED RUNNERS                       │
│                                                                              │
│   GITHUB ACTIONS                           KUBERNETES CLUSTER               │
│   ┌────────────────────────┐               ┌────────────────────────────┐   │
│   │                        │               │                            │   │
│   │   ubuntu-latest        │    kubectl    │   ┌──────────────────┐    │   │
│   │   runner               │─────apply────▶│   │   Deployment     │    │   │
│   │                        │               │   │   (new image)    │    │   │
│   │   Has:                 │               │   └──────────────────┘    │   │
│   │   • kubectl installed  │               │            │              │   │
│   │   • kubeconfig secret  │               │            ▼              │   │
│   │                        │               │   ┌──────────────────┐    │   │
│   └────────────────────────┘               │   │   Rolling        │    │   │
│                                            │   │   Update         │    │   │
│                                            │   └──────────────────┘    │   │
│                                            │                            │   │
│                                            └────────────────────────────┘   │
│                                                                              │
│   PROS:                              CONS:                                   │
│   ✅ No infrastructure to manage    ❌ Need to expose K8s API              │
│   ✅ Free for public repos          ❌ Security: kubeconfig in secrets      │
│   ✅ Easy to set up                 ❌ Limited customization                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Workflow Code for Kubernetes Deployment:

```yaml
# .github/workflows/deploy-k8s.yml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/fraud-inference

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'
      
      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
          echo "KUBECONFIG=$(pwd)/kubeconfig" >> $GITHUB_ENV
      
      - name: Update deployment
        run: |
          kubectl set image deployment/inference-service \
            inference=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -n fraud-detection-inference
      
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/inference-service \
            -n fraud-detection-inference --timeout=300s
```

---

## 4.2 Option B: Deploy to AWS EC2

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT TO AWS EC2                                   │
│                                                                              │
│   GITHUB ACTIONS                               AWS EC2 INSTANCE             │
│   ┌────────────────────────┐                   ┌────────────────────────┐   │
│   │                        │                   │                        │   │
│   │   ubuntu-latest        │      SSH          │   ┌────────────────┐   │   │
│   │   runner               │─────────────────▶ │   │   Docker       │   │   │
│   │                        │                   │   │                │   │   │
│   │   Steps:               │                   │   │ docker-compose │   │   │
│   │   1. SSH to EC2        │                   │   │    pull        │   │   │
│   │   2. Pull new image    │                   │   │    up -d       │   │   │
│   │   3. Restart container │                   │   │                │   │   │
│   │                        │                   │   └────────────────┘   │   │
│   └────────────────────────┘                   │                        │   │
│                                                └────────────────────────┘   │
│                                                                              │
│   PROS:                              CONS:                                   │
│   ✅ Simple architecture            ❌ Single point of failure              │
│   ✅ Full control over server       ❌ Manual scaling                       │
│   ✅ Lower cost for small apps      ❌ Need to manage EC2 instance          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Setting Up EC2 for Deployment:

```bash
# On your EC2 instance (one-time setup)

# 1. Install Docker
sudo yum update -y  # Or apt-get for Ubuntu
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# 2. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Create app directory
mkdir -p /home/ec2-user/fraud-detection
cd /home/ec2-user/fraud-detection

# 4. Create docker-compose.yml (or copy from repo)
```

### Workflow Code for EC2 Deployment:

```yaml
# .github/workflows/deploy-ec2.yml
name: Deploy to EC2

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/fraud-inference

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to EC2
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /home/ec2-user/fraud-detection
            
            # Login to registry
            echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
            
            # Pull new image
            docker-compose pull
            
            # Restart with new image
            docker-compose up -d
            
            # Cleanup old images
            docker image prune -f
            
            # Verify health
            sleep 10
            curl -f http://localhost:8000/health || exit 1
```

---

## 4.3 Comparison: GitHub Runner vs EC2

| Aspect | GitHub Runner + K8s | EC2 + Docker Compose |
|--------|---------------------|----------------------|
| **Complexity** | Higher | Lower |
| **Scaling** | Automatic (HPA) | Manual |
| **Cost** | Higher (K8s cluster) | Lower (single instance) |
| **Reliability** | High (multi-pod) | Lower (single server) |
| **Best For** | Production, high traffic | Dev/staging, small apps |
| **Setup Time** | Days | Hours |

---

# Part 5: Implementation Guide

## 5.1 Repository Structure

```
IEEE-CIS-Fraud-detection/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Build & Test
│       ├── deploy-staging.yml     # Deploy to staging
│       └── deploy-production.yml  # Deploy to production
├── docker/
│   ├── training.Dockerfile
│   └── inference.Dockerfile
├── kubernetes/
│   ├── base/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   └── overlays/
│       ├── staging/
│       └── production/
├── src/
├── tests/
├── docker-compose.yml
└── requirements.txt
```

## 5.2 Complete CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.10'

jobs:
  # ═══════════════════════════════════════════════════════════════════════════
  # LINT & FORMAT CHECK
  # ═══════════════════════════════════════════════════════════════════════════
  lint:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install linting tools
        run: pip install flake8 black isort
      
      - name: Check formatting with black
        run: black --check src/ tests/
      
      - name: Check imports with isort
        run: isort --check-only src/ tests/
      
      - name: Lint with flake8
        run: flake8 src/ tests/ --max-line-length=100

  # ═══════════════════════════════════════════════════════════════════════════
  # UNIT TESTS
  # ═══════════════════════════════════════════════════════════════════════════
  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest tests/ -v \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        if: always()
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  # ═══════════════════════════════════════════════════════════════════════════
  # BUILD DOCKER IMAGES
  # ═══════════════════════════════════════════════════════════════════════════
  build-training:
    name: Build Training Image
    needs: [lint, test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/training.Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/fraud-training:${{ github.sha }}
            ghcr.io/${{ github.repository }}/fraud-training:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  build-inference:
    name: Build Inference Image
    needs: [lint, test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    outputs:
      image_tag: ghcr.io/${{ github.repository }}/fraud-inference:${{ github.sha }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/fraud-inference:${{ github.sha }}
            ghcr.io/${{ github.repository }}/fraud-inference:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## 5.3 Complete CD Workflow (Kubernetes)

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
      
      - name: Configure kubectl
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Update inference deployment
        run: |
          kubectl set image deployment/inference-service \
            inference=ghcr.io/${{ github.repository }}/fraud-inference:${{ github.sha }} \
            -n fraud-detection-inference
      
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/inference-service \
            -n fraud-detection-inference --timeout=300s
      
      - name: Verify deployment
        run: |
          # Get service endpoint
          ENDPOINT=$(kubectl get ingress inference-ingress -n fraud-detection-inference -o jsonpath='{.spec.rules[0].host}')
          
          # Health check
          curl -f https://${ENDPOINT}/health || exit 1
          
          echo "✅ Deployment successful!"
      
      - name: Notify on failure
        if: failure()
        run: |
          # Rollback on failure
          kubectl rollout undo deployment/inference-service -n fraud-detection-inference
          echo "❌ Deployment failed, rolled back!"
```

## 5.4 Complete CD Workflow (EC2)

```yaml
# .github/workflows/deploy-ec2.yml
name: Deploy to EC2

on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    name: Deploy to EC2
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment: production
    
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ec2-user
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            set -e
            
            echo "📦 Deploying new version..."
            cd /home/ec2-user/fraud-detection
            
            # Login to container registry
            echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
            
            # Update image tag in docker-compose
            export IMAGE_TAG=${{ github.sha }}
            
            # Pull new images
            docker-compose pull
            
            # Start new containers (zero-downtime with health checks)
            docker-compose up -d --remove-orphans
            
            # Wait for health check
            echo "⏳ Waiting for health check..."
            sleep 15
            
            # Verify
            if curl -sf http://localhost:8000/health; then
              echo "✅ Deployment successful!"
            else
              echo "❌ Health check failed, rolling back..."
              docker-compose down
              docker-compose up -d
              exit 1
            fi
            
            # Cleanup old images
            docker image prune -af
```

## 5.5 Required GitHub Secrets

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUIRED GITHUB SECRETS                              │
│                                                                              │
│   Go to: Repository → Settings → Secrets and variables → Actions            │
│                                                                              │
│   FOR KUBERNETES DEPLOYMENT:                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │   KUBE_CONFIG       = Base64 encoded kubeconfig file                │   │
│   │                       Run: cat ~/.kube/config | base64 | tr -d '\n'  │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   FOR EC2 DEPLOYMENT:                                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │   EC2_HOST          = Your EC2 public IP or DNS                     │   │
│   │                       Example: ec2-xx-xx-xx-xx.compute.amazonaws.com│   │
│   │                                                                      │   │
│   │   EC2_USER          = SSH username (usually ec2-user or ubuntu)     │   │
│   │                                                                      │   │
│   │   EC2_SSH_KEY       = Private SSH key content                       │   │
│   │                       Run: cat ~/.ssh/your-key.pem                   │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   FOR AWS (S3 Access):                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │   AWS_ACCESS_KEY_ID     = Your AWS access key                       │   │
│   │   AWS_SECRET_ACCESS_KEY = Your AWS secret key                       │   │
│   │   AWS_REGION            = ap-south-1                                │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5.6 Implementation Checklist

```
PHASE 1: CI Setup (Day 1-2)
═══════════════════════════
[ ] Create .github/workflows/ci.yml
[ ] Add linting configuration (pyproject.toml for black, isort)
[ ] Write basic tests in tests/
[ ] Push and verify CI runs successfully
[ ] Fix any linting/test failures

PHASE 2: Docker Setup (Day 2-3)
═══════════════════════════════
[ ] Create docker/training.Dockerfile
[ ] Create docker/inference.Dockerfile
[ ] Create docker-compose.yml
[ ] Test locally: docker-compose up
[ ] Verify both services work

PHASE 3: Container Registry (Day 3)
════════════════════════════════════
[ ] Enable GHCR for your repository
[ ] Update workflows to build and push images
[ ] Verify images appear in GitHub Packages

PHASE 4: CD Setup (Day 4-5)
═══════════════════════════
[ ] Choose deployment target (K8s or EC2)
[ ] Set up infrastructure (K8s cluster or EC2 instance)
[ ] Add required secrets to GitHub
[ ] Create deployment workflow
[ ] Test deployment

PHASE 5: Production Readiness (Day 5-7)
═══════════════════════════════════════
[ ] Add health check endpoints
[ ] Configure proper logging
[ ] Set up monitoring/alerting
[ ] Document runbook for incidents
[ ] Test rollback procedures
```

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CI/CD SUMMARY                                      │
│                                                                              │
│   CONTINUOUS INTEGRATION (CI):                                               │
│   • Runs on every push/PR                                                   │
│   • Lints code, runs tests                                                  │
│   • Builds Docker images                                                    │
│   • Pushes to container registry                                            │
│                                                                              │
│   CONTINUOUS DEPLOYMENT (CD):                                                │
│   • Runs after CI succeeds (on main branch)                                 │
│   • Deploys to Kubernetes or EC2                                            │
│   • Runs health checks                                                      │
│   • Rolls back on failure                                                   │
│                                                                              │
│   WHERE IT FITS:                                                             │
│   Code → CI (build/test) → Docker Images → CD (deploy) → Production        │
│                                                                              │
│   RECOMMENDATION FOR YOUR PROJECT:                                           │
│   • Start with EC2 deployment (simpler)                                     │
│   • Move to Kubernetes when you need scaling                                │
│   • Use GitHub-hosted runners (no infrastructure to manage)                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

> **Ready to implement?** Let me know and I'll create the actual workflow files in your repository!
