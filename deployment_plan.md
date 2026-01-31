# Fraud Detection System - Microservices Deployment Plan

> **Document Version**: 1.0  
> **Created**: 2026-01-30  
> **Architecture**: Microservices with Docker & Kubernetes

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Microservices Design](#microservices-design)
4. [Docker Containerization](#docker-containerization)
5. [Kubernetes Orchestration](#kubernetes-orchestration)
6. [Scaling Strategy](#scaling-strategy)
7. [Model Management](#model-management)
8. [Networking & Communication](#networking--communication)
9. [Monitoring & Observability](#monitoring--observability)
10. [CI/CD Pipeline](#cicd-pipeline)
11. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

This document outlines the deployment strategy for the IEEE-CIS Fraud Detection system using a **microservices architecture**. The system is split into two distinct services:

| Microservice | Purpose | Scaling Strategy |
|--------------|---------|------------------|
| **Training Pipeline Service** | Data ingestion → Feature Engineering → Model Training | No horizontal scaling (runs on schedule) |
| **Inference Service** | Frontend + Real-time predictions | Horizontal Pod Autoscaling (HPA) |

**Key Technologies:**
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **Model Storage**: AWS S3
- **API Framework**: FastAPI
- **Load Balancing**: Kubernetes Ingress / AWS ALB

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    AWS CLOUD                                             │
│                                                                                          │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│   │                              S3 BUCKET                                            │  │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │  │
│   │   │   Raw Data      │  │   Artifacts     │  │    Models       │                  │  │
│   │   │ (transaction,   │  │ (preprocessor,  │  │  (model.pkl,    │                  │  │
│   │   │  identity CSVs) │  │  feature_eng)   │  │   metadata)     │                  │  │
│   │   └─────────────────┘  └─────────────────┘  └─────────────────┘                  │  │
│   └──────────────────────────────────────────────────────────────────────────────────┘  │
│                    ▲                                      │                              │
│                    │ Push model                           │ Pull model                   │
│                    │ after training                       │ at startup                   │
│   ┌────────────────┴─────────────────┐    ┌──────────────┴────────────────────────┐    │
│   │                                  │    │                                        │    │
│   │     TRAINING PIPELINE            │    │        INFERENCE SERVICE               │    │
│   │        SERVICE                   │    │                                        │    │
│   │  ┌──────────────────────────┐   │    │   ┌────────────────────────────────┐   │    │
│   │  │      Kubernetes          │   │    │   │         Kubernetes             │   │    │
│   │  │   CronJob / Job          │   │    │   │   Deployment + HPA + Ingress   │   │    │
│   │  │                          │   │    │   │                                │   │    │
│   │  │  ┌────┐ ┌────┐ ┌────┐   │   │    │   │  ┌─────┐ ┌─────┐ ┌─────┐      │   │    │
│   │  │  │ DI │→│ FE │→│ MT │   │   │    │   │  │Pod 1│ │Pod 2│ │Pod N│      │   │    │
│   │  │  └────┘ └────┘ └────┘   │   │    │   │  │     │ │     │ │     │      │   │    │
│   │  │                          │   │    │   │  └─────┘ └─────┘ └─────┘      │   │    │
│   │  └──────────────────────────┘   │    │   └────────────────────────────────┘   │    │
│   │                                  │    │                  ▲                     │    │
│   │    Runs: Weekly / On-demand      │    │                  │                     │    │
│   │    Replicas: 1                   │    │            Load Balancer               │    │
│   │    Resources: High (burst)       │    │                  │                     │    │
│   │                                  │    │           User Traffic                 │    │
│   └──────────────────────────────────┘    └──────────────────────────────────────────┘    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Why This Split?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MICROSERVICE 1                                      │
│                    (Training Pipeline Service)                               │
│                                                                              │
│   Data Ingestion ──▶ Feature Engineering ──▶ Model Training                 │
│                                                                              │
│   WHY TOGETHER:                                                              │
│   ✓ These components have tight data dependencies                           │
│   ✓ Feature engineering output is direct input to training                  │
│   ✓ No benefit in scaling separately                                        │
│   ✓ Runs infrequently (weekly/monthly)                                      │
│   ✓ Requires consistent data transformations                                │
│                                                                              │
│   CHARACTERISTICS:                                                           │
│   • Single execution per training cycle                                     │
│   • High resource burst, then idle                                          │
│   • Needs access to raw data storage                                        │
│   • Outputs: Model artifacts to S3                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MICROSERVICE 2                                      │
│                      (Inference Service)                                     │
│                                                                              │
│   Frontend (UI) + FastAPI + Prediction Pipeline                             │
│                                                                              │
│   WHY SEPARATE:                                                              │
│   ✓ Receives majority of traffic                                            │
│   ✓ Needs low latency responses                                             │
│   ✓ Must handle variable load (scaling required)                            │
│   ✓ Stateless design enables horizontal scaling                             │
│                                                                              │
│   CHARACTERISTICS:                                                           │
│   • Always running (24/7)                                                   │
│   • Predictable resource usage per request                                  │
│   • Loads model ONCE at startup                                             │
│   • Horizontal scaling based on traffic                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Microservices Design

### Microservice 1: Training Pipeline Service

#### Purpose
Handles the complete ML training lifecycle from data ingestion to model deployment to S3.

#### Components

```
training-service/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── components/
│   │   ├── data_ingestion.py
│   │   ├── data_FE_transformation.py
│   │   └── model_trainer.py
│   ├── config/
│   │   └── config.py
│   ├── utils/
│   │   ├── s3_utils.py
│   │   └── common.py
│   └── pipeline/
│       └── training_pipeline.py      # Orchestrates all components
├── config/
│   └── config.yaml
└── run_training.py                   # Entry point
```

#### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRAINING PIPELINE WORKFLOW                                │
│                                                                              │
│   ┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐          │
│   │             │     │                  │     │                 │          │
│   │    Data     │────▶│    Feature       │────▶│    Model        │          │
│   │  Ingestion  │     │   Engineering    │     │   Training      │          │
│   │             │     │                  │     │                 │          │
│   └─────────────┘     └──────────────────┘     └────────┬────────┘          │
│         │                     │                         │                    │
│         ▼                     ▼                         ▼                    │
│   ┌───────────┐         ┌───────────┐            ┌───────────┐              │
│   │   S3:     │         │   S3:     │            │   S3:     │              │
│   │ Raw Data  │         │Artifacts  │            │  Models   │              │
│   │           │         │(preproc)  │            │           │              │
│   └───────────┘         └───────────┘            └───────────┘              │
│                                                                              │
│   TRIGGERS:                                                                  │
│   • Kubernetes CronJob (scheduled: weekly)                                  │
│   • Manual trigger via kubectl or API                                       │
│   • CI/CD pipeline (on data drift detection)                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Resource Requirements

| Resource | Request | Limit | Notes |
|----------|---------|-------|-------|
| CPU | 2 cores | 4 cores | High during feature engineering |
| Memory | 8Gi | 16Gi | Large dataset processing |
| Storage | 50Gi | 100Gi | Temporary data storage |
| GPU | Optional | 1 | If using deep learning models |

---

### Microservice 2: Inference Service

#### Purpose
Serves the frontend UI and handles real-time fraud prediction requests.

#### Components

```
inference-service/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── api/
│   │   └── main.py               # FastAPI application
│   ├── pipeline/
│   │   └── prediction_pipeline.py
│   ├── utils/
│   │   ├── s3_utils.py
│   │   └── common.py
│   └── static/                    # Frontend files
│       ├── index.html
│       ├── style.css
│       └── script.js
├── startup.py                     # Model loading at startup
└── config/
    └── config.yaml
```

#### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      INFERENCE SERVICE WORKFLOW                              │
│                                                                              │
│   STARTUP PHASE (Once per pod):                                             │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                                                                        │ │
│   │   Container Start ──▶ Download Model from S3 ──▶ Load into Memory     │ │
│   │                                                                        │ │
│   │   ┌─────────┐         ┌─────────────┐         ┌─────────────────┐     │ │
│   │   │   S3    │────────▶│  /tmp/      │────────▶│   RAM           │     │ │
│   │   │ Bucket  │         │  model.pkl  │         │   self.model    │     │ │
│   │   └─────────┘         └─────────────┘         └─────────────────┘     │ │
│   │                                                                        │ │
│   │   Time: ~10-30 seconds (one-time cost)                                │ │
│   │                                                                        │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│   REQUEST PHASE (Every request):                                            │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                                                                        │ │
│   │   User Request ──▶ Validate ──▶ Preprocess ──▶ Predict ──▶ Response   │ │
│   │                                                                        │ │
│   │   ┌─────────┐    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌───────┐ │ │
│   │   │  JSON   │───▶│ Schema  │──▶│  Apply  │──▶│  Model  │──▶│ JSON  │ │ │
│   │   │  Data   │    │  Check  │   │   FE    │   │.predict │   │Result │ │ │
│   │   └─────────┘    └─────────┘   └─────────┘   └─────────┘   └───────┘ │ │
│   │                                                                        │ │
│   │   Time: ~10-50ms (no S3 calls!)                                       │ │
│   │                                                                        │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Resource Requirements

| Resource | Request | Limit | Notes |
|----------|---------|-------|-------|
| CPU | 500m | 1 core | Per pod |
| Memory | 1Gi | 2Gi | Model + request processing |
| Storage | 1Gi | 5Gi | Model files only |

---

## Docker Containerization

### Training Service Dockerfile

```dockerfile
# training-service/Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY run_training.py .

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Entry point
CMD ["python", "run_training.py"]
```

### Training Service requirements.txt

```
# training-service/requirements.txt
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
lightgbm>=4.0.0
boto3>=1.28.0
mlflow>=2.8.0
pyyaml>=6.0
joblib>=1.3.0
dvc>=3.0.0
```

---

### Inference Service Dockerfile

```dockerfile
# inference-service/Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY startup.py .

# Create directory for model cache
RUN mkdir -p /tmp/models

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MODEL_CACHE_DIR=/tmp/models

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entry point with startup script
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Inference Service requirements.txt

```
# inference-service/requirements.txt
fastapi>=0.104.0
uvicorn>=0.24.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
lightgbm>=4.0.0
boto3>=1.28.0
joblib>=1.3.0
pyyaml>=6.0
python-multipart>=0.0.6
```

---

### Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Training Service (run manually when needed)
  training-service:
    build:
      context: .
      dockerfile: docker/training.Dockerfile
    container_name: fraud-training
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - S3_BUCKET=${S3_BUCKET}
      - MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
    volumes:
      - ./artifacts:/app/artifacts
      - ./logs:/app/logs
    profiles:
      - training  # Only runs when explicitly called

  # Inference Service (always running)
  inference-service:
    build:
      context: .
      dockerfile: docker/inference.Dockerfile
    container_name: fraud-inference
    ports:
      - "8000:8000"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - S3_BUCKET=${S3_BUCKET}
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped

  # Local S3 (MinIO) for development
  minio:
    image: minio/minio:latest
    container_name: fraud-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    profiles:
      - dev

volumes:
  minio_data:
```

---

## Kubernetes Orchestration

### Namespace Setup

```yaml
# kubernetes/namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fraud-detection-training
  labels:
    app: fraud-detection
    tier: training
---
apiVersion: v1
kind: Namespace
metadata:
  name: fraud-detection-inference
  labels:
    app: fraud-detection
    tier: inference
```

---

### Secrets Management

```yaml
# kubernetes/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: fraud-detection-inference
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "<your-access-key>"
  AWS_SECRET_ACCESS_KEY: "<your-secret-key>"
  AWS_REGION: "ap-south-1"
  S3_BUCKET: "fraud-detection-models"
---
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: fraud-detection-training
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "<your-access-key>"
  AWS_SECRET_ACCESS_KEY: "<your-secret-key>"
  AWS_REGION: "ap-south-1"
  S3_BUCKET: "fraud-detection-models"
  MLFLOW_TRACKING_URI: "<dagshub-mlflow-uri>"
  MLFLOW_TRACKING_USERNAME: "<dagshub-username>"
  MLFLOW_TRACKING_PASSWORD: "<dagshub-token>"
```

---

### Training Service - CronJob

```yaml
# kubernetes/training/cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: training-pipeline
  namespace: fraud-detection-training
  labels:
    app: fraud-detection
    component: training
spec:
  schedule: "0 2 * * 0"  # Every Sunday at 2 AM
  timeZone: "Asia/Kolkata"
  concurrencyPolicy: Forbid  # Don't run if previous is still running
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 14400  # 4 hours max
      template:
        metadata:
          labels:
            app: fraud-detection
            component: training
        spec:
          restartPolicy: OnFailure
          containers:
          - name: training
            image: your-registry/fraud-training:latest
            imagePullPolicy: Always
            resources:
              requests:
                memory: "8Gi"
                cpu: "2"
              limits:
                memory: "16Gi"
                cpu: "4"
            envFrom:
            - secretRef:
                name: aws-credentials
            volumeMounts:
            - name: training-storage
              mountPath: /app/artifacts
          volumes:
          - name: training-storage
            emptyDir:
              sizeLimit: 50Gi
```

### Training Service - Manual Job Template

```yaml
# kubernetes/training/manual-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: training-pipeline-manual
  namespace: fraud-detection-training
  labels:
    app: fraud-detection
    component: training
    trigger: manual
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 14400
  template:
    metadata:
      labels:
        app: fraud-detection
        component: training
    spec:
      restartPolicy: Never
      containers:
      - name: training
        image: your-registry/fraud-training:latest
        imagePullPolicy: Always
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
        envFrom:
        - secretRef:
            name: aws-credentials
        volumeMounts:
        - name: training-storage
          mountPath: /app/artifacts
      volumes:
      - name: training-storage
        emptyDir:
          sizeLimit: 50Gi
```

---

### Inference Service - Deployment

```yaml
# kubernetes/inference/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
  namespace: fraud-detection-inference
  labels:
    app: fraud-detection
    component: inference
spec:
  replicas: 2  # Minimum replicas
  selector:
    matchLabels:
      app: fraud-detection
      component: inference
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: fraud-detection
        component: inference
    spec:
      terminationGracePeriodSeconds: 30
      containers:
      - name: inference
        image: your-registry/fraud-inference:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
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
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        volumeMounts:
        - name: model-cache
          mountPath: /tmp/models
      volumes:
      - name: model-cache
        emptyDir:
          sizeLimit: 5Gi
```

---

### Inference Service - Service

```yaml
# kubernetes/inference/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: inference-service
  namespace: fraud-detection-inference
  labels:
    app: fraud-detection
    component: inference
spec:
  type: ClusterIP
  selector:
    app: fraud-detection
    component: inference
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP
```

---

### Inference Service - Horizontal Pod Autoscaler

```yaml
# kubernetes/inference/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
  namespace: fraud-detection-inference
  labels:
    app: fraud-detection
    component: inference
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  # Scale based on CPU utilization
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  # Scale based on Memory utilization
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

---

### Inference Service - Ingress

```yaml
# kubernetes/inference/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: inference-ingress
  namespace: fraud-detection-inference
  labels:
    app: fraud-detection
    component: inference
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - fraud-detection.yourdomain.com
    secretName: fraud-detection-tls
  rules:
  - host: fraud-detection.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: inference-service
            port:
              number: 80
```

---

## Scaling Strategy

### How Horizontal Scaling Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     KUBERNETES HORIZONTAL POD AUTOSCALER                     │
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                         S3 Bucket                                      │ │
│   │                   ┌─────────────────┐                                  │ │
│   │                   │   model.pkl     │                                  │ │
│   │                   │  preprocessor   │                                  │ │
│   │                   └────────┬────────┘                                  │ │
│   │                            │                                           │ │
│   │            Downloaded ONCE │ per pod at startup                        │ │
│   │                            │                                           │ │
│   └────────────────────────────┼───────────────────────────────────────────┘ │
│                                │                                             │
│   ┌────────────────────────────┼───────────────────────────────────────────┐ │
│   │                            ▼                                           │ │
│   │   LOW TRAFFIC (CPU < 70%)                                              │ │
│   │   ┌───────────┐    ┌───────────┐                                       │ │
│   │   │   Pod 1   │    │   Pod 2   │                                       │ │
│   │   │  Model ✓  │    │  Model ✓  │        2 replicas (minimum)           │ │
│   │   │  in RAM   │    │  in RAM   │                                       │ │
│   │   └───────────┘    └───────────┘                                       │ │
│   │                                                                         │ │
│   └─────────────────────────────────────────────────────────────────────────┘ │
│                                │                                             │
│                       Traffic Increases                                      │
│                                ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │
│   │                                                                          │ │
│   │   HIGH TRAFFIC (CPU > 70%)                                              │ │
│   │   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐│ │
│   │   │   Pod 1   │ │   Pod 2   │ │   Pod 3   │ │   Pod 4   │ │   Pod 5   ││ │
│   │   │  Model ✓  │ │  Model ✓  │ │  Model ✓  │ │  Model ✓  │ │  Model ✓  ││ │
│   │   │  in RAM   │ │  in RAM   │ │  in RAM   │ │  in RAM   │ │  in RAM   ││ │
│   │   └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘│ │
│   │                                                                          │ │
│   │   5 replicas (auto-scaled)                                              │ │
│   │                                                                          │ │
│   │   EACH NEW POD:                                                          │ │
│   │   1. Starts container                                                   │ │
│   │   2. Downloads model from S3                                            │ │
│   │   3. Loads model into RAM                                               │ │
│   │   4. Starts accepting requests                                          │ │
│   │                                                                          │ │
│   └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Point: S3 Is NOT a Bottleneck!

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   WRONG UNDERSTANDING ❌                                                     │
│   ─────────────────────                                                      │
│                                                                              │
│   User Request ──▶ Pod ──▶ S3 (get model) ──▶ Predict ──▶ Response          │
│                           │                                                  │
│                           └── S3 called for EACH request (SLOW!)            │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   CORRECT UNDERSTANDING ✓                                                    │
│   ────────────────────────                                                   │
│                                                                              │
│   STARTUP (once):                                                            │
│   Pod Start ──▶ S3 (get model) ──▶ Load to RAM ──▶ Ready                    │
│                                                                              │
│   RUNTIME (every request):                                                   │
│   User Request ──▶ Pod ──▶ RAM (model already loaded) ──▶ Predict ──▶ Resp  │
│                           │                                                  │
│                           └── NO S3 calls! Uses in-memory model (FAST!)     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Scaling Metrics Comparison

| Metric | 2 Pods | 5 Pods | 10 Pods |
|--------|--------|--------|---------|
| S3 Downloads | 2 | 5 | 10 |
| S3 Download Time | Startup only | Startup only | Startup only |
| Requests/sec | ~200 | ~500 | ~1000 |
| Memory Usage | 2 GB | 5 GB | 10 GB |
| Cost | $$ | $$$$ | $$$$$$ |

---

## Model Management

### Model Versioning Strategy

```
S3 Bucket Structure:
fraud-detection-models/
├── models/
│   ├── v1/
│   │   ├── model.pkl
│   │   ├── preprocessor.pkl
│   │   └── metadata.json
│   ├── v2/
│   │   ├── model.pkl
│   │   ├── preprocessor.pkl
│   │   └── metadata.json
│   └── latest/              # Symlink or copy to latest version
│       ├── model.pkl
│       ├── preprocessor.pkl
│       └── metadata.json
└── manifests/
    └── latest.txt           # Contains "v2"
```

### Model Update Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MODEL UPDATE WORKFLOW                                 │
│                                                                              │
│   1. TRAINING COMPLETES                                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Training Pipeline ──▶ New model.pkl ──▶ Upload to S3 (v3/)         │   │
│   │                                         ──▶ Update latest.txt → "v3" │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                │                                             │
│                                ▼                                             │
│   2. TRIGGER ROLLING UPDATE                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Either:                                                             │   │
│   │  a) kubectl rollout restart deployment/inference-service            │   │
│   │  b) CI/CD triggers new image deployment                              │   │
│   │  c) Custom controller detects model change                           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                │                                             │
│                                ▼                                             │
│   3. KUBERNETES ROLLING UPDATE                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │  BEFORE:  [Pod1-v2] [Pod2-v2]                                       │   │
│   │                                                                      │   │
│   │  STEP 1:  [Pod1-v2] [Pod2-v2] [Pod3-v3 (starting)]                  │   │
│   │                                                                      │   │
│   │  STEP 2:  [Pod1-v2] [Pod2-v2 (terminating)] [Pod3-v3 (ready)]       │   │
│   │                                                                      │   │
│   │  STEP 3:  [Pod1-v2] [Pod3-v3] [Pod4-v3 (starting)]                  │   │
│   │                                                                      │   │
│   │  STEP 4:  [Pod1-v2 (terminating)] [Pod3-v3] [Pod4-v3 (ready)]       │   │
│   │                                                                      │   │
│   │  AFTER:   [Pod3-v3] [Pod4-v3]                                       │   │
│   │                                                                      │   │
│   │  ✓ Zero downtime                                                    │   │
│   │  ✓ Gradual transition                                               │   │
│   │  ✓ Automatic rollback if new pods fail health checks                │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Model Loading Code Pattern

```python
# src/api/main.py (Inference Service)

from fastapi import FastAPI
from contextlib import asynccontextmanager
import boto3
import joblib
import os

# Global model holder
class ModelHolder:
    model = None
    preprocessor = None
    version = None

model_holder = ModelHolder()

async def load_model_from_s3():
    """Download and load model at startup"""
    s3 = boto3.client('s3')
    bucket = os.environ['S3_BUCKET']
    cache_dir = os.environ.get('MODEL_CACHE_DIR', '/tmp/models')
    
    # Download model files
    s3.download_file(bucket, 'models/latest/model.pkl', f'{cache_dir}/model.pkl')
    s3.download_file(bucket, 'models/latest/preprocessor.pkl', f'{cache_dir}/preprocessor.pkl')
    s3.download_file(bucket, 'models/latest/metadata.json', f'{cache_dir}/metadata.json')
    
    # Load into memory
    model_holder.model = joblib.load(f'{cache_dir}/model.pkl')
    model_holder.preprocessor = joblib.load(f'{cache_dir}/preprocessor.pkl')
    
    # Read version
    with open(f'{cache_dir}/metadata.json') as f:
        metadata = json.load(f)
        model_holder.version = metadata.get('version', 'unknown')
    
    print(f"✓ Model loaded successfully (version: {model_holder.version})")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Load model
    await load_model_from_s3()
    yield
    # Shutdown: Cleanup
    model_holder.model = None
    model_holder.preprocessor = None

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    """Health check endpoint"""
    if model_holder.model is None:
        return {"status": "unhealthy", "reason": "model not loaded"}
    return {
        "status": "healthy",
        "model_version": model_holder.version
    }

@app.post("/predict")
async def predict(data: dict):
    """Prediction endpoint - uses in-memory model"""
    # Model is already in RAM - no S3 call here!
    df = pd.DataFrame(data['transactions'])
    processed = model_holder.preprocessor.transform(df)
    predictions = model_holder.model.predict(processed)
    return {"predictions": predictions.tolist()}
```

---

## Networking & Communication

### Service Communication Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KUBERNETES CLUSTER                                 │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                          INTERNET                                    │   │
│   └────────────────────────────────┬────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                   INGRESS CONTROLLER                                 │   │
│   │              (nginx / AWS ALB / GCP LB)                              │   │
│   │                                                                       │   │
│   │  fraud-detection.yourdomain.com ──▶ inference-service:80            │   │
│   └────────────────────────────────┬────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                   SERVICE (ClusterIP)                                │   │
│   │                 inference-service:80                                 │   │
│   │                                                                       │   │
│   │         Load balances across all ready pods                          │   │
│   └────────────────────────────────┬────────────────────────────────────┘   │
│                                    │                                         │
│              ┌─────────────────────┼─────────────────────┐                  │
│              ▼                     ▼                     ▼                  │
│   ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐        │
│   │      Pod 1        │ │      Pod 2        │ │      Pod N        │        │
│   │ inference:8000    │ │ inference:8000    │ │ inference:8000    │        │
│   └───────────────────┘ └───────────────────┘ └───────────────────┘        │
│                                                                              │
│   ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│   EXTERNAL CONNECTIONS (from pods):                                          │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  S3 (model storage)      ◀────── Download model at startup          │   │
│   │  DagsHub/MLflow          ◀────── Training logs/metrics (training)   │   │
│   │  CloudWatch/Datadog      ◀────── Application metrics                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Monitoring & Observability

### Metrics to Monitor

```yaml
# Prometheus metrics (via ServiceMonitor)
Inference Service Metrics:
  - request_latency_seconds         # P50, P95, P99
  - request_count_total             # Total requests
  - prediction_count_total          # Predictions made
  - model_version                   # Current model version
  - model_load_time_seconds         # Time to load model
  
Training Service Metrics:
  - training_duration_seconds       # Total training time
  - data_ingestion_rows_total       # Rows processed
  - model_accuracy                  # Model metrics
  - feature_engineering_time        # FE processing time
  
Infrastructure Metrics:
  - container_cpu_usage_seconds     # CPU usage
  - container_memory_usage_bytes    # Memory usage
  - kube_pod_status_ready          # Pod health
  - kube_hpa_status_current_replicas # Current scale
```

### Logging Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LOGGING ARCHITECTURE                                │
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                         APPLICATION LOGS                              │ │
│   │                                                                        │ │
│   │   Format: JSON (structured logging)                                   │ │
│   │                                                                        │ │
│   │   {                                                                   │ │
│   │     "timestamp": "2026-01-30T14:30:00Z",                              │ │
│   │     "level": "INFO",                                                  │ │
│   │     "service": "inference",                                           │ │
│   │     "pod": "inference-abc123",                                        │ │
│   │     "request_id": "uuid-here",                                        │ │
│   │     "message": "Prediction completed",                                │ │
│   │     "latency_ms": 45,                                                 │ │
│   │     "transaction_count": 100                                          │ │
│   │   }                                                                   │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │              FLUENTD / FLUENT BIT (DaemonSet)                         │ │
│   │                                                                        │ │
│   │   Collects logs from:                                                 │ │
│   │   • /var/log/containers/*fraud-detection*.log                         │ │
│   │   • Application stdout/stderr                                         │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │              ELASTICSEARCH / CLOUDWATCH LOGS                          │ │
│   │                                                                        │ │
│   │   • Searchable logs                                                   │ │
│   │   • Retention policies                                                │ │
│   │   • Alerting on errors                                                │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  TRAINING_IMAGE: ghcr.io/${{ github.repository }}/fraud-training
  INFERENCE_IMAGE: ghcr.io/${{ github.repository }}/fraud-inference

jobs:
  # Build and test
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v
      
      - name: Build Training Image
        run: |
          docker build -f docker/training.Dockerfile -t $TRAINING_IMAGE:${{ github.sha }} .
          docker tag $TRAINING_IMAGE:${{ github.sha }} $TRAINING_IMAGE:latest
      
      - name: Build Inference Image
        run: |
          docker build -f docker/inference.Dockerfile -t $INFERENCE_IMAGE:${{ github.sha }} .
          docker tag $INFERENCE_IMAGE:${{ github.sha }} $INFERENCE_IMAGE:latest
      
      - name: Push Images
        if: github.ref == 'refs/heads/main'
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push $TRAINING_IMAGE:${{ github.sha }}
          docker push $TRAINING_IMAGE:latest
          docker push $INFERENCE_IMAGE:${{ github.sha }}
          docker push $INFERENCE_IMAGE:latest

  # Deploy to Kubernetes
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBE_CONFIG }}
      
      - name: Update Inference Deployment
        run: |
          kubectl set image deployment/inference-service \
            inference=$INFERENCE_IMAGE:${{ github.sha }} \
            -n fraud-detection-inference
      
      - name: Wait for Rollout
        run: |
          kubectl rollout status deployment/inference-service \
            -n fraud-detection-inference --timeout=300s
```

---

## Implementation Roadmap

### Phase 1: Containerization (Week 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: DOCKER SETUP                                                       │
│                                                                              │
│  [ ] Create project structure for microservices                              │
│      ├── docker/                                                             │
│      │   ├── training.Dockerfile                                            │
│      │   └── inference.Dockerfile                                           │
│      ├── docker-compose.yml                                                  │
│      └── .dockerignore                                                       │
│                                                                              │
│  [ ] Update application code                                                 │
│      ├── Add lifespan events for model loading                              │
│      ├── Add health check endpoints                                         │
│      └── Environment variable configuration                                  │
│                                                                              │
│  [ ] Test locally with docker-compose                                        │
│      ├── docker-compose up inference-service                                │
│      └── Verify predictions work                                             │
│                                                                              │
│  [ ] Push images to container registry                                       │
│      ├── docker build -t fraud-training:v1 -f docker/training.Dockerfile .  │
│      └── docker build -t fraud-inference:v1 -f docker/inference.Dockerfile . │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 2: Kubernetes Basics (Week 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: KUBERNETES DEPLOYMENT                                              │
│                                                                              │
│  [ ] Set up Kubernetes cluster                                               │
│      ├── Local: minikube or kind                                            │
│      ├── Cloud: EKS / GKE / AKS                                             │
│      └── Install kubectl                                                     │
│                                                                              │
│  [ ] Create Kubernetes manifests                                             │
│      ├── kubernetes/                                                         │
│      │   ├── namespaces.yaml                                                │
│      │   ├── secrets.yaml                                                   │
│      │   ├── training/                                                       │
│      │   │   ├── cronjob.yaml                                               │
│      │   │   └── manual-job.yaml                                            │
│      │   └── inference/                                                      │
│      │       ├── deployment.yaml                                            │
│      │       ├── service.yaml                                               │
│      │       ├── hpa.yaml                                                   │
│      │       └── ingress.yaml                                               │
│                                                                              │
│  [ ] Deploy and verify                                                       │
│      ├── kubectl apply -f kubernetes/                                       │
│      ├── kubectl get pods -n fraud-detection-inference                      │
│      └── Test endpoint with curl                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 3: Scaling & Production (Week 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: PRODUCTION READINESS                                               │
│                                                                              │
│  [ ] Configure HPA                                                           │
│      ├── Set resource requests/limits                                       │
│      ├── Configure scaling thresholds                                       │
│      └── Test with load generator                                           │
│                                                                              │
│  [ ] Set up Ingress                                                          │
│      ├── Install ingress controller                                         │
│      ├── Configure TLS certificates                                         │
│      └── DNS configuration                                                   │
│                                                                              │
│  [ ] Monitoring & Logging                                                    │
│      ├── Install Prometheus/Grafana                                         │
│      ├── Configure log aggregation                                          │
│      └── Create dashboards and alerts                                        │
│                                                                              │
│  [ ] CI/CD Pipeline                                                          │
│      ├── GitHub Actions workflow                                            │
│      ├── Automated testing                                                  │
│      └── Automated deployments                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Commands

```bash
# Build Docker images
docker build -f docker/training.Dockerfile -t fraud-training:latest .
docker build -f docker/inference.Dockerfile -t fraud-inference:latest .

# Run locally with docker-compose
docker-compose up inference-service

# Deploy to Kubernetes
kubectl apply -f kubernetes/namespaces.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/inference/
kubectl apply -f kubernetes/training/

# Check status
kubectl get pods -n fraud-detection-inference
kubectl get hpa -n fraud-detection-inference
kubectl logs -f deployment/inference-service -n fraud-detection-inference

# Trigger manual training
kubectl create job --from=cronjob/training-pipeline training-manual -n fraud-detection-training

# Scale manually (for testing)
kubectl scale deployment inference-service --replicas=5 -n fraud-detection-inference

# Rolling restart (after model update)
kubectl rollout restart deployment/inference-service -n fraud-detection-inference

# Check rollout status
kubectl rollout status deployment/inference-service -n fraud-detection-inference
```

---

## Summary Table

| Component | Monolithic | Microservices |
|-----------|------------|---------------|
| **Deployment** | Single container | 2 separate services |
| **Scaling** | Scale everything | Scale only what's needed |
| **Updates** | Full redeployment | Independent updates |
| **Failure** | Entire app fails | Isolated failures |
| **Resource Usage** | Inefficient | Optimized per service |
| **Complexity** | Simple | More complex to orchestrate |

---

> **Next Steps**: Review this plan and let me know if you want to proceed with implementation. I'll create the Docker files, Kubernetes manifests, and update the application code accordingly.
