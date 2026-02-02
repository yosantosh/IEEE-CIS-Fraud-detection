# CI/CD Pipeline Documentation 🚀

This document details the complete **GitHub Actions** workflow used to build, test, and deploy the application to Azure.

---

## 1. The Full Workflow Code
**File**: `.github/workflows/ci_cd_azure.yml`

```yaml
name: CI/CD - Azure (Full Pipeline)

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      deploy_target:
        description: 'Deploy to AKS?'
        required: true
        default: 'yes'
        type: choice
        options:
        - 'yes'
        - 'no'

env:
  ACR_NAME: mlopsfraud
  RG: fraud-detection-rg
  CLUSTER: fraud-aks-cluster

jobs:
  # ------------------------------------------------------------------
  # JOB 1: QUALITY & TEST
  # ------------------------------------------------------------------
  test:
    name: 🧪Code Quality & Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      - run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8 httpx
      - name: 🔍 Lint Code
        run: |
          # Warning only mode to match DockerHub pipeline
          flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
      - name: 🧪 Run Unit Tests
        run: pytest tests/ -v --cov=src --cov-report=xml

  # ------------------------------------------------------------------
  # JOB 2: BUILD & PUSH TO AZURE ACR
  # ------------------------------------------------------------------
  build-and-push-azure:
    name: Build & Push (Azure)
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: ACR Login
        run: az acr login --name ${{ env.ACR_NAME }}
      
      - uses: docker/setup-buildx-action@v3

      - name: Build & Push Training
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/training.Dockerfile
          push: true
          # Tag with SHA (for tracking) and Latest (for ease of use)
          tags: ${{ env.ACR_NAME }}.azurecr.io/fraud-training:${{ github.sha }}, ${{ env.ACR_NAME }}.azurecr.io/fraud-training:latest

      - name: Build & Push Inference
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: ${{ env.ACR_NAME }}.azurecr.io/fraud-inference:${{ github.sha }}, ${{ env.ACR_NAME }}.azurecr.io/fraud-inference:latest

  # ------------------------------------------------------------------
  # JOB 3: DEPLOY TO AKS
  # ------------------------------------------------------------------
  deploy-aks:
    name: Deploy to AKS
    needs: build-and-push-azure
    runs-on: ubuntu-latest
    # Only run if push to main OR manual trigger says yes
    if: github.event_name == 'push' || github.event.inputs.deploy_target == 'yes'
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Check & Start AKS Cluster
        run: |
          echo "Checking cluster status..."
          STATUS=$(az aks show --resource-group ${{ env.RG }} --name ${{ env.CLUSTER }} --query "powerState.code" -o tsv)
          echo "Current Status: $STATUS"
          if [ "$STATUS" == "Stopped" ]; then
            echo "Cluster is stopped. Starting it now..."
            az aks start --resource-group ${{ env.RG }} --name ${{ env.CLUSTER }}
            echo "Cluster started."
          fi

      - name: Set AKS Context
        uses: azure/aks-set-context@v3
        with:
          resource-group: ${{ env.RG }}
          cluster-name: ${{ env.CLUSTER }}

      # Create/Update Secrets (Including DagsHub Token for Training)
      - name: Update App Secrets
        run: |
          kubectl create secret generic app-secrets \
            --from-literal=AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }} \
            --from-literal=AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }} \
            --from-literal=DAGSHUB_TOKEN=${{ secrets.DAGSHUB_TOKEN }} \
            --dry-run=client -o yaml | kubectl apply -f -

      # Deploy Inference Service using the SHA tag we just built
      - name: Deploy Inference
        run: |
          sed -i "s|IMAGE_PLACEHOLDER|${{ env.ACR_NAME }}.azurecr.io/fraud-inference:${{ github.sha }}|g" kubernetes/aks/inference.yaml
          kubectl apply -f kubernetes/aks/inference.yaml
          # Force restart to ensure new code is picked up
          kubectl rollout restart deployment/inference-service

      # Deploy/Update Training Job (Manual Trigger Setup)
      - name: Deploy Training Job
        run: |
          sed -i "s|TRAINING_IMAGE_PLACEHOLDER|${{ env.ACR_NAME }}.azurecr.io/fraud-training:${{ github.sha }}|g" kubernetes/aks/training.yaml
          kubectl apply -f kubernetes/aks/training.yaml
```

---

## 2. How Everything Connects 🔗

This YAML file is the conductor of the orchestra. Here's exactly how it talks to other files in the project:

### 🔗 Connecting to Python Tests (Job 1)
- **Line 37 (`pip install -r requirements.txt`)**: It reads your project dependencies. This ensures the CI environment matches your local Dev environment.
- **Line 45 (`pytest tests/`)**: It executes your Python test suite located in `tests/`.
  - If **ANY** test fails, the pipeline **stops immediately**.
  - This prevents bad code (like the 422 validation error we fixed) from ever being built into a container.

### 🔗 Connecting to Dockerfiles (Job 2)
- **Line 71 (`file: docker/training.Dockerfile`)**: It reads the instructions in this file to build the Training image.
- **Line 80 (`file: docker/inference.Dockerfile`)**: It reads the instructions for the Inference image.
- **Context**: It uses `.` (root) as context, meaning the Dockerfiles can access `src/`, `config/`, and `dvc.yaml`.

### 🔗 Connecting to Kubernetes Manifests (Job 3)
This is the magic part where CI meets CD.

- **The Problem**: Kubernetes YAML files (`kubernetes/aks/inference.yaml`) are static. You can't hardcode the image tag `...:latest` because Kubernetes won't always pull a new image if the tag name is the same. We want to deploy the *exact code* we just built (e.g., commit `abc1234`).
- **The Solution**: Logic at **Line 130**:
  ```bash
  sed -i "s|IMAGE_PLACEHOLDER|...:${{ github.sha }}|g" kubernetes/aks/inference.yaml
  ```
  - It opens `kubernetes/aks/inference.yaml`.
  - It finds the word `IMAGE_PLACEHOLDER`.
  - It replaces it with the actual image URL + Commit SHA (e.g., `mlopsfraud.azurecr.io/fraud-inference:f4b3d...`).
  - Then it runs `kubectl apply`.

### 🔗 Connecting to Secrets
- **Line 121 (`kubectl create secret ...`)**:
  - It reads secrets from **GitHub Secrets** (`${{ secrets.AWS_ACCESS_KEY_ID }}`).
  - It pushes them into the **AKS Cluster** as a Kubernetes Secret named `app-secrets`.
  - Result: Your pods can read environment variables securely without you ever writing them in code.

---

## 3. Pipeline Behavior & Logic 🧠

### 1. The "Gatekeeper" Logic
- **`needs: test` (Line 52)**: The Build job *waits* for the Test job. If tests fail, no Docker image is built. This saves money and storage.
- **`needs: build-and-push-azure` (Line 89)**: The Deployment job *waits* for the Build.

### 2. The "Smart Cluster" Logic (Lines 101-110)
This script solves a common pain point: **Cost Savings vs Reliability**.
- "I stopped the cluster to save money, but the generic pipeline failed because it couldn't connect."
- **Solution**: The script asks Azure: *"Is the cluster stopped?"*
- If **Yes**: It wakes the cluster up (`az aks start`) and waits before proceeding.
- If **No**: It proceeds immediately.

### 3. The "Rollout" Logic (Line 133)
`kubectl rollout restart deployment/inference-service`
- This ensures that even if you didn't change the Image Tag (e.g. if you used `latest`), Kubernetes is forced to kill the old Pods and start new ones. This guarantees the new code is live.

---

## 4. Summary of artifacts
- **2 Images Created**: `fraud-training:SHA` and `fraud-inference:SHA`.
- **1 Cluster Updated**: The inference service on AKS gets updated to the new image.
- **1 Secret Synced**: Keys are refreshed.
