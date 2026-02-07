# IEEE-CIS Fraud Detection - End-to-End MLOps Pipeline

A production-ready **Machine Learning Operations (MLOps)** project that detects fraudulent online transactions using the IEEE-CIS Fraud Detection dataset from Kaggle. This project demonstrates the complete lifecycle of an ML system—from data ingestion to Kubernetes deployment with monitoring.

---

## 🎯 Project Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        IEEE-CIS FRAUD DETECTION                                  │
│                    ═══════════════════════════════                               │
│                                                                                  │
│    ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐            │
│    │   DATA     │──►│  FEATURE   │──►│   MODEL    │──►│ PREDICTION │            │
│    │ INGESTION  │   │   ENG.     │   │ TRAINING   │   │   API      │            │
│    └────────────┘   └────────────┘   └────────────┘   └────────────┘            │
│         │                │                 │                │                    │
│         └────────────────┴─────────────────┴────────────────┘                   │
│                              │                                                   │
│                    ┌─────────▼─────────┐                                        │
│                    │     DVC + S3      │  Data & Model Versioning               │
│                    │   MLflow/DagsHub  │  Experiment Tracking                   │
│                    └───────────────────┘                                        │
│                                                                                  │
│    ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐            │
│    │  DOCKER    │──►│  CI/CD     │──►│ KUBERNETES │──►│ MONITORING │            │
│    │ CONTAINERS │   │  GITHUB    │   │    AKS     │   │  GRAFANA   │            │
│    └────────────┘   └────────────┘   └────────────┘   └────────────┘            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Goal**: Build a fraud detection system that can classify transactions as fraudulent or legitimate with high accuracy, deployed as a scalable microservice.

### Key Statistics
- **Dataset Size**: ~590K transactions, 434 features
- **Fraud Rate**: 3.5% (heavily imbalanced)
- **Model**: XGBoost Classifier with ROC-AUC optimization
- **Deployment**: Azure Kubernetes Service (AKS) with auto-scaling

---

## 🏗️ Architecture Overview

### High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION ARCHITECTURE                              │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │                           GITHUB ACTIONS                                 │    │
│   │    ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐         │    │
│   │    │ TEST &   │───►│   BUILD      │───►│  PUSH TO AZURE ACR   │         │    │
│   │    │   LINT   │    │   DOCKER     │    │                      │         │    │
│   │    └──────────┘    └──────────────┘    └──────────────────────┘         │    │
│   └─────────────────────────────────────────────────────┬───────────────────┘    │
│                                                         │                         │
│                                                         ▼                         │
│   ┌───────────────────────────────────────────────────────────────────────┐      │
│   │                    AZURE KUBERNETES SERVICE (AKS)                      │      │
│   │                                                                        │      │
│   │   ┌───────────────────┐         ┌───────────────────────────────┐     │      │
│   │   │  TRAINING POD     │         │      INFERENCE POD            │     │      │
│   │   │  ─────────────    │         │      ─────────────            │     │      │
│   │   │                   │  Model  │                               │     │      │
│   │   │  • DVC Pipeline   │ ──────► │  • FastAPI Server             │     │      │
│   │   │  • XGBoost Train  │  (S3)   │  • Prometheus Metrics         │     │      │
│   │   │  • MLflow Logging │         │  • /predict endpoint          │     │      │
│   │   │  (CronJob)        │         │  (Deployment + HPA)           │     │      │
│   │   └───────────────────┘         └───────────────────────────────┘     │      │
│   │                                            │                           │      │
│   └────────────────────────────────────────────┼───────────────────────────┘      │
│                                                │                                   │
│           ┌────────────────────────────────────┼────────────────────────────┐     │
│           │                                    ▼                            │     │
│           │   ┌─────────────────┐    ┌─────────────────┐                   │     │
│           │   │   PROMETHEUS    │───►│    GRAFANA      │  Monitoring &     │     │
│           │   │   (Scrape)      │    │   (Dashboard)   │  Alerting         │     │
│           │   └─────────────────┘    └─────────────────┘                   │     │
│           └─────────────────────────────────────────────────────────────────┘     │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │                        EXTERNAL SERVICES                                 │    │
│   │    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │    │
│   │    │   AWS S3    │    │   DAGSHUB   │    │   AZURE     │                │    │
│   │    │ (Data/Model)│    │  (MLflow)   │    │   MONITOR   │                │    │
│   │    └─────────────┘    └─────────────┘    └─────────────┘                │    │
│   └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### ML Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DVC-MANAGED ML PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Stage 1: DATA INGESTION                                                         │
│  ════════════════════════                                                        │
│  ┌──────────┐    ┌──────────┐         ┌─────────────────────────────────┐       │
│  │  S3      │    │   S3     │         │                                 │       │
│  │ trans.csv│ +  │ iden.csv │  ─────► │  raw_data.csv (590K × 434)      │       │
│  └──────────┘    └──────────┘  MERGE  │  ↓                              │       │
│                                       │  Schema saved to schema.yaml    │       │
│                                       └─────────────────────────────────┘       │
│                                                    │                             │
│                                                    ▼                             │
│  Stage 2: FEATURE ENGINEERING                                                    │
│  ═════════════════════════════                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐      │
│  │  • Transaction Amount Features (log, decimal, bins)                    │      │
│  │  • Time Features (hour, day, is_night, is_business_hour)               │      │
│  │  • Card Features (combinations, frequencies)                           │      │
│  │  • Email Features (domain, vendor, TLD)                                │      │
│  │  • Device Features (type, brand, browser, OS)                          │      │
│  │  • V-Column Aggregations (sum, mean, std, NaN count)                   │      │
│  │  • Train/Test Split (80/20, stratified)                                │      │
│  └───────────────────────────────────────────────────────────────────────┘      │
│                                    │                                             │
│            ┌───────────────────────┴────────────────────────┐                   │
│            ▼                                                ▼                    │
│  ┌─────────────────────┐                      ┌─────────────────────┐           │
│  │ Train_transformed   │                      │ Test_transformed    │           │
│  │     (472K)          │                      │      (118K)         │           │
│  └─────────────────────┘                      └─────────────────────┘           │
│            │                                                                     │
│            ▼                                                                     │
│  Stage 3: MODEL TRAINING                                                         │
│  ════════════════════════                                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐      │
│  │  XGBoost Classifier                                                    │      │
│  │  ─────────────────                                                     │      │
│  │  • scale_pos_weight: 27 (handles class imbalance)                      │      │
│  │  • early_stopping_rounds: 80                                           │      │
│  │  • Metrics logged to MLflow/DagsHub                                    │      │
│  │  • Model saved: XGBClassifier_latest.joblib                            │      │
│  └───────────────────────────────────────────────────────────────────────┘      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
IEEE-CIS-Fraud-detection/
│
├── 🔧 src/                          # Source Code
│   ├── api/main.py                  # FastAPI server with prediction endpoints
│   ├── components/                  # ML Pipeline Components
│   │   ├── data_ingestion.py        #   → Stage 1: Fetch & merge data
│   │   ├── data_FE_transformation.py#   → Stage 2: Feature engineering
│   │   ├── model_training_evaluation.py # → Stage 3: Train XGBoost
│   │   └── prediction.py            #   → Inference pipeline
│   ├── constants/                   # Configurations
│   │   ├── config.py                #   → Centralized dataclass configs
│   │   ├── params.yaml              #   → Model hyperparameters
│   │   └── schema.yaml              #   → Data schemas
│   ├── utils/                       # Utility functions
│   ├── logger/                      # Structured logging
│   └── exception/                   # Custom exceptions
│
├── 🐳 docker/                       # Dockerfiles
│   ├── training.Dockerfile          # Multi-stage build for training
│   ├── inference.Dockerfile         # Lightweight inference container
│   └── scripts/run_training.sh      # Training entrypoint script
│
├── ☸️  kubernetes/aks/               # Kubernetes Manifests
│   ├── inference.yaml               # Deployment + Service + HPA
│   ├── training.yaml                # CronJob for periodic retraining
│   └── monitoring/                  # ServiceMonitor, AlertRules
│
├── 🔄 .github/workflows/            # CI/CD Pipelines
│   ├── ci_cd_azure.yml              # Main: Test → Build → Deploy to AKS
│   └── ci_dockerhub.yml             # Alt: Push to Docker Hub
│
├── 📊 static/                       # Frontend Web UI
│   ├── index.html                   # Main HTML page
│   ├── css/styles.css               # Glassmorphism styling
│   └── js/app.js                    # API interaction logic
│
├── 🧪 tests/                        # Test Suite
│   ├── test_api.py                  # API endpoint tests
│   ├── test_config.py               # Configuration tests
│   └── test_fe.py                   # Feature engineering tests
│
├── 📝 Notes/                        # Implementation Guides (READ THESE!)
│   ├── projectworkflow.md           # Complete step-by-step workflow
│   ├── 1_project_setup.md           # Phase 1: Environment setup
│   ├── 2_dvc_automation.md          # Phase 2: DVC + S3 configuration
│   ├── 3_build_components.md        # Phase 3: Building src modules
│   ├── 4_build_docker.md            # Phase 4: Dockerization
│   ├── 5.1_CICD.md                  # Phase 5: CI/CD with GitHub Actions
│   ├── 5.2_ci_stage_test.md         # Phase 5: Testing strategies
│   ├── 5.3_deployment_plan.md       # Phase 6: Kubernetes deployment
│   └── manage_azure_aks_acr.md      # Azure AKS/ACR commands
│
├── 📊 artifacts/                    # DVC-tracked outputs (→ S3)
├── 🔧 config/                       # Pipeline configs
├── 📦 models/                       # Trained models (→ S3)
├── dvc.yaml                         # DVC pipeline definition
└── docker-compose.yml               # Local development
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Clone the repository
git clone https://github.com/santosh4thmarch/IEEE-CIS-Fraud-detection.git
cd IEEE-CIS-Fraud-detection

# Create environment
conda create -n mlops python=3.10 -y
conda activate mlops

# Install dependencies
pip install -r requirements.txt

# Setup credentials
cp .env.example .env
# Edit .env with your AWS credentials
```

### Run Locally

```bash
# Option 1: Docker Compose (Recommended)
docker compose up inference    # Start prediction API
docker compose up training     # Run training pipeline

# Option 2: Direct Python
dvc repro                      # Run full ML pipeline
uvicorn src.api.main:app       # Start API server
```

### Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| **Web UI** | http://localhost:8000 | Interactive fraud detection interface |
| **API Docs** | http://localhost:8000/docs | Swagger/OpenAPI documentation |
| **Health Check** | http://localhost:8000/health | Service health status |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |

---

## 🔧 Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            TECHNOLOGY STACK                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ML & DATA                    INFRASTRUCTURE                  MONITORING        │
│   ─────────                    ──────────────                  ──────────        │
│   • XGBoost                    • Docker                        • Prometheus      │
│   • Pandas/NumPy               • Kubernetes (AKS)              • Grafana         │
│   • Scikit-learn               • GitHub Actions                • Azure Monitor   │
│   • DVC                        • Azure ACR                                       │
│   • MLflow/DagsHub             • AWS S3                                          │
│                                                                                  │
│   API & FRONTEND               TESTING                                           │
│   ──────────────               ───────                                           │
│   • FastAPI                    • Pytest                                          │
│   • HTML/CSS/JS                • Flake8 (Linting)                                │
│   • Prometheus Client          • Coverage Reports                                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📖 How to Implement a Similar Project

The `Notes/` folder contains detailed step-by-step guides to build this project from scratch. Follow these phases in order:

### Implementation Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       IMPLEMENTATION PHASES                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  PHASE 1-3: FOUNDATION                                                           │
│  ═══════════════════════                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ 📁 Notes/1_project_setup.md       → Environment + Cookiecutter template  │   │
│  │ 📁 Notes/projectworkflow.md       → MLflow/DagsHub experiment tracking   │   │
│  │ 📁 Notes/3_build_components.md    → Logger, Exception, Utils modules     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│  PHASE 4-7: ML PIPELINE                                                          │
│  ═══════════════════════                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ 📁 Notes/2_dvc_automation.md      → DVC + S3 remote storage setup        │   │
│  │ 📁 Notes/projectworkflow.md       → Data Ingestion (Phase 5)             │   │
│  │                                   → Feature Engineering (Phase 6)        │   │
│  │                                   → Model Training (Phase 7)             │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│  PHASE 8-9: CONTAINERIZATION                                                     │
│  ════════════════════════════                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ 📁 Notes/4_build_docker.md        → Multi-stage Dockerfiles              │   │
│  │ 📁 Notes/projectworkflow.md       → Prediction Pipeline (Phase 8)        │   │
│  │                                   → Docker Compose setup (Phase 9)       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                                      ▼                                           │
│  PHASE 10-12: PRODUCTION                                                         │
│  ═══════════════════════════                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ 📁 Notes/5.1_CICD.md              → GitHub Actions CI/CD pipelines       │   │
│  │ 📁 Notes/5.2_ci_stage_test.md     → Testing strategies in CI             │   │
│  │ 📁 Notes/5.3_deployment_plan.md   → Kubernetes (AKS) deployment          │   │
│  │ 📁 Notes/manage_azure_aks_acr.md  → Azure CLI commands reference         │   │
│  │ 📁 Notes/projectworkflow.md       → Monitoring & Alerting (Phase 12)     │   │
│  │                                   → Frontend UI (Phase 13)               │   │
│  │                                   → Testing Suite (Phase 14)             │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Guide

| Phase | Title | Notes File | Key Actions |
|-------|-------|------------|-------------|
| **1** | Project Setup | `1_project_setup.md` | Conda env, Cookiecutter template, Git init |
| **2** | Experiment Tracking | `projectworkflow.md` (Phase 2) | DagsHub + MLflow integration |
| **3** | Build Components | `3_build_components.md` | Logger, Exception, Utils modules |
| **4** | DVC + S3 | `2_dvc_automation.md` | Data versioning, S3 remote storage |
| **5** | Data Ingestion | `projectworkflow.md` (Phase 5) | S3 fetch, merge transaction + identity |
| **6** | Feature Engineering | `projectworkflow.md` (Phase 6) | 135+ new features, preprocessing |
| **7** | Model Training | `projectworkflow.md` (Phase 7) | XGBoost training, MLflow logging |
| **8** | Prediction Pipeline | `projectworkflow.md` (Phase 8) | FastAPI inference endpoint |
| **9** | Dockerization | `4_build_docker.md` | Multi-stage builds, microservices |
| **10** | CI/CD | `5.1_CICD.md` | GitHub Actions, Azure ACR |
| **11** | Kubernetes | `5.3_deployment_plan.md` | AKS deployment, HPA, CronJobs |
| **12** | Monitoring | `projectworkflow.md` (Phase 12) | Prometheus, Grafana, Alerts |
| **13** | Frontend | `projectworkflow.md` (Phase 13) | Interactive web UI |
| **14** | Testing | `projectworkflow.md` (Phase 14) | Pytest, coverage reports |

### Key Commands

```bash
# ════════════════════════════════════════════════════════════════════════════════
# LOCAL DEVELOPMENT
# ════════════════════════════════════════════════════════════════════════════════

# Run ML Pipeline
dvc repro                           # Run all stages
dvc repro data_ingestion            # Run specific stage
dvc push                            # Push artifacts to S3

# Docker
docker compose up inference         # Start API
docker compose up training          # Run training

# Tests
pytest tests/ -v --cov=src          # Run tests with coverage

# ════════════════════════════════════════════════════════════════════════════════
# KUBERNETES (AKS)
# ════════════════════════════════════════════════════════════════════════════════

# Connect to cluster
az aks get-credentials --resource-group fraud-detection-rg --name fraud-aks-cluster

# Check services
kubectl get pods -l app=inference
kubectl get svc inference-service

# Manual training run
kubectl create job --from=cronjob/training-job manual-training-$(date +%s)

# Monitoring
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring

# Cost management
az aks stop  --resource-group fraud-detection-rg --name fraud-aks-cluster
az aks start --resource-group fraud-detection-rg --name fraud-aks-cluster
```

---

## 📊 Project Status

| Component | Status | Technology |
|-----------|--------|------------|
| ✅ ML Pipeline (DVC) | Complete | DVC, XGBoost, MLflow |
| ✅ API (FastAPI) | Complete | FastAPI, Prometheus |
| ✅ Docker Containers | Complete | Multi-stage builds |
| ✅ CI/CD Pipeline | Complete | GitHub Actions |
| ✅ Kubernetes Deployment | Complete | Azure AKS, HPA |
| ✅ Monitoring & Alerting | Complete | Prometheus, Grafana |
| ✅ Frontend UI | Complete | HTML/CSS/JS |
| ✅ Testing Suite | Complete | Pytest |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Vesta Corporation** for providing the real-world fraud detection dataset
- **IEEE Computational Intelligence Society** for sponsoring the competition
- **Kaggle** for hosting the competition platform

---

## 📚 Resources

- **Competition**: [IEEE-CIS Fraud Detection](https://www.kaggle.com/competitions/ieee-fraud-detection)
- **MLflow Dashboard**: [DagsHub MLflow](https://dagshub.com/santosh4thmarch/IEEE-CIS-Fraud-detection.mlflow)
- **Implementation Notes**: See `Notes/` folder for detailed guides
