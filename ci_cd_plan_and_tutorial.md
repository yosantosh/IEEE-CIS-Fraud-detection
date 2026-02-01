# CI/CD Complete Tutorial & Implementation Plan
> **Document Version**: 3.0 (Architecture Aligned)  
> **Created**: 2026-02-01  
> **For**: IEEE-CIS Fraud Detection Project

---

## Table of Contents

1. [Part 1: Architecture & Theory](#part-1-architecture--theory)
2. [Part 2: The Continuous Integration (CI) Phase](#part-2-the-continuous-integration-ci-phase)
3. [Part 3: Deployment Strategy A - Microservices on Azure AKS](#part-3-deployment-strategy-a---microservices-on-azure-aks)
4. [Part 4: Deployment Strategy B - Microservices on AWS EKS](#part-4-deployment-strategy-b---microservices-on-aws-eks)
5. [Part 5: Deployment Strategy C - Monolith Inference on AWS App Runner](#part-5-deployment-strategy-c---monolith-inference-on-aws-app-runner)

---

# Part 1: Architecture & Theory

## 1.1 The Golden Loop of CI/CD
In modern software engineering, we aim for a "Golden Loop":
1.  **Code**: You write code on your laptop.
2.  **Commit**: You push to GitHub.
3.  **CI (Continuous Integration)**: A robot (GitHub Actions) immediately runs tests to ensure you didn't break anything.
4.  **CD (Continuous Deployment)**: If tests pass, the robot packages your code into a Docker container and ships it to the cloud.

## 1.2 Our Three Deployment Architectures
We are supporting three specific architectures as requested:

| Architecture | Platform | Service Type | Role | Components |
| :--- | :--- | :--- | :--- | :--- |
| **Strategy A** | **Azure AKS** | **Microservices** | Full System | • **Inference Service** (Deployment)<br>• **Training Service** (CronJob) |
| **Strategy B** | **AWS EKS** | **Microservices** | Full System | • **Inference Service** (Deployment)<br>• **Training Service** (CronJob) |
| **Strategy C** | **AWS App Runner** | **Monolithic** | Inference Only | • **Inference Service** (Service) |

---

# Part 2: The Continuous Integration (CI) Phase

Before we can deploy anywhere, we must ensure our code is robust. This phase runs on **every push** to the `main` branch.

## 2.1 The CI Workflow (`.github/workflows/ci.yml`)
This workflow performs three key checks:
1.  **Linting**: Checks code style (PEP8).
2.  **Testing**: Runs robust unit tests using `pytest` and mocks.
3.  **Build Check**: Verifies that Docker images CAN be built (without pushing yet).

### Step-by-Step Implementation

**1. Create the Workflow File**
Create `.github/workflows/ci.yml`:

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Code Quality & Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'
      - run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8 httpx
      - name: 🔍 Lint Code
        run: flake8 src/ tests/ --count --max-line-length=127 --statistics
      - name: 🧪 Run Unit Tests
        run: pytest tests/ -v --cov=src --cov-report=xml

  build-and-push:
    name: Build & Push Docker Images
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      
      - name: 🔑 Login to Docker Hub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: 🐳 Build & Push Training Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/training.Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ secrets.DOCKERHUB_USERNAME }}/fraud-training:${{ github.sha }}, ${{ secrets.DOCKERHUB_USERNAME }}/fraud-training:latest

      - name: 🐳 Build & Push Inference Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ secrets.DOCKERHUB_USERNAME }}/fraud-inference:${{ github.sha }}, ${{ secrets.DOCKERHUB_USERNAME }}/fraud-inference:latest
```

## 2.2 The "Build Once" Philosophy (Best Practice)
We have upgraded this pipeline to follow the **Build Once, Deploy Many** pattern:
1.  **PRs**: Only perform a "dry run" build (ensure Dockerfile is valid).
2.  **Merge to Main**: Build the image **once** and push it to the registry (Docker Hub).
3.  **CD**: The deployment stages (CD) simply **pull** this exact image using its SHA tag. This guarantees that what you verified in CI is *exactly* what runs in production.

<!-- *(Note: Ensure you have `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` added to your GitHub Repository Secrets)* -->

## 2.3 Alternative: CI using AWS ECR
If you prefer using **AWS Elastic Container Registry (ECR)** instead of Docker Hub, use this configuration for the `build-and-push` job.

**Prerequisites:**
1.  Create ECR repositories in AWS Console (`fraud-training` and `fraud-inference`).
2.  Add Secrets to GitHub: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`.

```yaml
  build-and-push:
    name: Build & Push to ECR
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3

      # 1. Configure AWS Credentials
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      # 2. Login to ECR
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      # 3. Build & Push (Dynamic Registry URL)
      - name: 🐳 Build & Push Training Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/training.Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          # steps.login-ecr.outputs.registry returns your account URL (e.g., 123456789.dkr.ecr.us-east-1.amazonaws.com)
          tags: ${{ steps.login-ecr.outputs.registry }}/fraud-training:${{ github.sha }}, ${{ steps.login-ecr.outputs.registry }}/fraud-training:latest

      - name: 🐳 Build & Push Inference Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.login-ecr.outputs.registry }}/fraud-inference:${{ github.sha }}, ${{ steps.login-ecr.outputs.registry }}/fraud-inference:latest
```

---

# Part 3: Deployment Strategy A - Microservices on Azure AKS

**Goal**: Full system (Training + Inference) on Azure Kubernetes Service using **Azure Container Registry (ACR)**.

## 3.1 Infrastructure Setup (One-Time)
Run locally using Azure CLI:

```bash
# 1. Create Resource Group & ACR
az group create --name fraud-detection-rg --location eastus
az acr create --resource-group fraud-detection-rg --name frauddetectionacr --sku Basic --admin-enabled true

# 2. Create AKS Cluster (Attached to ACR for auto-auth)
az aks create --resource-group fraud-detection-rg --name fraud-aks-cluster --node-count 2 --attach-acr frauddetectionacr --generate-ssh-keys

# 3. Create Credentials for GitHub
az ad sp create-for-rbac --name "github-actions-fraud" --role contributor --scopes /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/fraud-detection-rg --sdk-auth
# SAVE OUTPUT AS 'AZURE_CREDENTIALS' in GitHub Secrets
```

## 3.2 Kubernetes Manifests (`kubernetes/aks/`)

**1. `inference.yaml` (The API Service)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
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
        image: IMAGE_PLACEHOLDER
        ports:
        - containerPort: 8000
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_ACCESS_KEY_ID}}
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_SECRET_ACCESS_KEY}}
---
apiVersion: v1
kind: Service
metadata:
  name: inference-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: inference
```

**2. `training.yaml` (The CronJob)**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: training-job
spec:
  schedule: "0 2 * * 0" # Every Sunday at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: training
            image: TRAINING_IMAGE_PLACEHOLDER
            env:
            - name: AWS_ACCESS_KEY_ID
              valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_ACCESS_KEY_ID}}
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_SECRET_ACCESS_KEY}}
          restartPolicy: OnFailure
```

## 3.3 CI/CD Workflow (`.github/workflows/deploy-aks.yml`)

```yaml
name: Deploy to Azure AKS

on:
  push:
    branches: [main]

env:
  ACR_NAME: frauddetectionacr
  RG: fraud-detection-rg
  CLUSTER: fraud-aks-cluster

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # 1. Login & Connect
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - run: az acr login --name ${{ env.ACR_NAME }}
      - uses: azure/aks-set-context@v3
        with:
          resource-group: ${{ env.RG }}
          cluster-name: ${{ env.CLUSTER }}

      # 2. Secrets
      - run: |
          kubectl create secret generic app-secrets \
            --from-literal=AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }} \
            --from-literal=AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }} \
            --dry-run=client -o yaml | kubectl apply -f -

      # 3. Build & Deploy Inference
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          tags: ${{ env.ACR_NAME }}.azurecr.io/inference:${{ github.sha }}
      - run: |
          sed -i "s|IMAGE_PLACEHOLDER|${{ env.ACR_NAME }}.azurecr.io/inference:${{ github.sha }}|g" kubernetes/aks/inference.yaml
          kubectl apply -f kubernetes/aks/inference.yaml

      # 4. Build & Deploy Training
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/training.Dockerfile
          push: true
          tags: ${{ env.ACR_NAME }}.azurecr.io/training:${{ github.sha }}
      - run: |
          sed -i "s|TRAINING_IMAGE_PLACEHOLDER|${{ env.ACR_NAME }}.azurecr.io/training:${{ github.sha }}|g" kubernetes/aks/training.yaml
          kubectl apply -f kubernetes/aks/training.yaml
```

---

# Part 4: Deployment Strategy B - Microservices on AWS EKS

**Goal**: Full system (Training + Inference) on AWS EKS using **Amazon ECR**.

## 4.1 Infrastructure Setup (One-Time)
```bash
# 1. Create ECR Repos
aws ecr create-repository --repository-name fraud-inference --region us-east-1
aws ecr create-repository --repository-name fraud-training --region us-east-1

# 2. Create EKS Cluster
eksctl create cluster --name fraud-eks-cluster --region us-east-1 --nodes 2
```

## 4.2 Kubernetes Manifests (`kubernetes/eks/`)

**1. `inference.yaml`**: Same as Azure, but add `imagePullSecrets` if needed or rely on IAM Roles for Service Accounts (IRSA).
**2. `training.yaml`**: Same as Azure CronJob structure.

## 4.3 CI/CD Workflow (`.github/workflows/deploy-eks.yml`)

```yaml
name: Deploy to AWS EKS

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_INFERENCE: fraud-inference
  ECR_TRAINING: fraud-training
  CLUSTER: fraud-eks-cluster

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      - id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      # 1. Build & Push Inference
      - env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          TAG: ${{ github.sha }}
        run: |
          docker build -t $REGISTRY/$ECR_INFERENCE:$TAG -f docker/inference.Dockerfile .
          docker push $REGISTRY/$ECR_INFERENCE:$TAG

      # 2. Build & Push Training
      - env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          TAG: ${{ github.sha }}
        run: |
          docker build -t $REGISTRY/$ECR_TRAINING:$TAG -f docker/training.Dockerfile .
          docker push $REGISTRY/$ECR_TRAINING:$TAG

      # 3. Deploy
      - run: aws eks update-kubeconfig --name ${{ env.CLUSTER }} --region ${{ env.AWS_REGION }}
      - env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          TAG: ${{ github.sha }}
        run: |
          # Inject image names
          sed -i "s|IMAGE_PLACEHOLDER|$REGISTRY/$ECR_INFERENCE:$TAG|g" kubernetes/eks/inference.yaml
          sed -i "s|TRAINING_IMAGE_PLACEHOLDER|$REGISTRY/$ECR_TRAINING:$TAG|g" kubernetes/eks/training.yaml
          
          # Apply
          kubectl apply -f kubernetes/eks/inference.yaml
          kubectl apply -f kubernetes/eks/training.yaml
          kubectl rollout restart deployment/inference-service
```

---

# Part 5: Deployment Strategy C - Monolith Inference on AWS App Runner

**Goal**: Simple, serverless deployment of **just the Inference API** using **Amazon ECR**.

## 5.1 Architecture
*   **Service**: AWS App Runner (Managed Container Service).
*   **Scope**: Monolithic (Inference only). Training happens elsewhere or manually.

## 5.2 CI/CD Workflow (`.github/workflows/deploy-apprunner.yml`)

```yaml
name: Deploy to AWS App Runner

on: workflow_dispatch

env:
  AWS_REGION: us-east-1
  ECR_REPO: fraud-inference

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      - id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build & Push
        env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          TAG: ${{ github.sha }}
        run: |
          docker build -t $REGISTRY/$ECR_REPO:$TAG -f docker/inference.Dockerfile .
          docker push $REGISTRY/$ECR_REPO:$TAG

      - name: Deploy
        uses: awslabs/amazon-app-runner-deploy@v1.2.0
        with:
          service: fraud-inference-service
          image: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPO }}:${{ github.sha }}
          access-role-arn: ${{ secrets.APP_RUNNER_ROLE_ARN }}
          region: ${{ env.AWS_REGION }}
          port: 8000
```
