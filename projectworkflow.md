# IEEE-CIS Fraud Detection - Complete Project Workflow
## From Setup to Model Training Pipeline

This document explains the complete step-by-step workflow for building the IEEE-CIS Fraud Detection MLOps pipeline.

---

# 📋 TABLE OF CONTENTS

1. [Phase 1: Project Setup](#phase-1-project-setup)
2. [Phase 2: MLflow + DagsHub Setup](#phase-2-mlflow--dagshub-setup)
3. [Phase 3: Building src Components](#phase-3-building-src-components)
4. [Phase 4: DVC + S3 Remote Storage](#phase-4-dvc--s3-remote-storage)
5. [Phase 5: Data Ingestion Component](#phase-5-data-ingestion-component)
6. [Phase 6: Feature Engineering Component](#phase-6-feature-engineering-component)
7. [Phase 7: Model Training Component](#phase-7-model-training-component)
8. [Phase 8: Prediction Pipeline](#phase-8-prediction-pipeline--completed)
9. [Phase 9: Dockerization](#phase-9-dockerization--completed)
10. [Quick Reference Commands](#quick-reference-commands)

---

# PHASE 1: PROJECT SETUP
## Setting up the project structure

### Steps:

1. **Create virtual environment**
   ```bash
   conda create -n mlops python=3.10
   conda activate mlops
   ```

2. **Install cookiecutter** (for project structure templates)
   ```bash
   pip install cookiecutter
   ```

3. **Create project structure from template**
   ```bash
   cookiecutter -c v1 https://github.com/drivendata/cookiecutter-data-science
   ```
   > Skip AWS things during setup, we'll configure manually later

4. **Organize files**
   - Cut all files from newly created folder and paste in root
   - Rename `src.models` to `src.model` to avoid confusion with `models/` folder

5. **Initial Git push**
   ```bash
   git init
   git add .
   git commit -m "Initial project structure"
   git push origin main
   ```

---

# PHASE 2: MLFLOW + DAGSHUB SETUP
## Setting up experiment tracking

### Steps:

1. **Go to DagsHub Dashboard**: https://dagshub.com/dashboard

2. **Create & Connect Repository**
   - Create > New Repo > Connect a repo > (GitHub) Connect
   - Select your repo > Connect

3. **Copy experiment tracking credentials**
   - Copy the MLflow URI and code snippet
   - Try: Go To MLFlow UI to verify

4. **Install required packages**
   ```bash
   pip install dagshub mlflow
   ```

5. **Test experiment tracking** (in `notebooks/exp1.ipynb`)
   - Track 3 models (XGBoost, CatBoost, LightGBM) using MLflow + DagsHub

### DagsHub Integration Code:
```python
import dagshub
import mlflow

dagshub.init(
    repo_owner='santosh4thmarch', 
    repo_name='IEEE-CIS-Fraud-detection', 
    mlflow=True
)
mlflow.set_tracking_uri('https://dagshub.com/santosh4thmarch/IEEE-CIS-Fraud-detection.mlflow')
```

---

# PHASE 3: BUILDING SRC COMPONENTS
## Creating reusable modules

### 3.1 Logger Module

**Purpose**: Save logs for important steps throughout the project.

**Steps**:
1. Create `src/logger/` directory
2. Create `__init__.py` inside logger folder
3. Write logging configuration code

**Best Practice**: Don't run `logger()` at the end of `__init__.py`. Instead, import and run it where you're using it.

**Usage**:
```python
from src.logger import logger
logger.info("Data ingestion started")
```

### 3.2 Exception Module

**Purpose**: Custom exception handling for better error messages.

**Location**: `src/exception/__init__.py`

**Usage**:
```python
from src.exception import CustomException
raise CustomException(e, sys)
```

### 3.3 Utils Module

**Purpose**: Utility functions used across components.

**Location**: `src/utils/__init__.py`

**Key Functions**:
- `Read_write_yaml_schema.read_yaml()` - Read YAML configurations
- `Read_write_yaml_schema.save_dataframe_schema()` - Save DataFrame schema to YAML
- `Read_write_yaml_schema.compare_schema()` - Compare DataFrame against saved schema
- `reduce_memory()` - Reduce DataFrame memory usage

### 3.4 Local Package Installation

**Steps**:
1. List packages in `requirements.txt`
2. Add `-e .` at the end of requirements.txt (installs local packages)
3. Install:
   ```bash
   pip install -r requirements.txt
   # OR
   pip install -e .
   ```

---

# PHASE 4: DVC + S3 REMOTE STORAGE
## Data Version Control with AWS S3

### Understanding DVC + Git

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THE BIG PICTURE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   YOUR LOCAL MACHINE                      REMOTE STORAGE                     │
│   ─────────────────                       ──────────────                     │
│                                                                              │
│   ┌─────────────────┐                     ┌─────────────────┐               │
│   │ artifacts/      │ ──── dvc push ────► │  AWS S3 Bucket  │               │
│   │ models/         │ ◄─── dvc pull ───── │  (large files)  │               │
│   └─────────────────┘                     └─────────────────┘               │
│           │                                                                  │
│           │ DVC tracks hashes                                                │
│           ▼                                                                  │
│   ┌─────────────────┐                     ┌─────────────────┐               │
│   │ dvc.lock        │ ──── git push ────► │    GitHub       │               │
│   │ dvc.yaml        │ ◄─── git pull ───── │  (code + refs)  │               │
│   └─────────────────┘                     └─────────────────┘               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Gets Tracked Where?

| Git (small files) | DVC (large files) |
|-------------------|-------------------|
| dvc.yaml (pipeline) | artifacts/ folder |
| dvc.lock (hashes) | models/ folder |
| .dvc/config | CSVs, model weights |
| Code files | Training data |

### Step-by-Step DVC Setup

#### Step 1: Install DVC with S3 Support
```bash
pip install dvc[s3]
dvc init
```

#### Step 2: Configure S3 Remote
```bash
# Add S3 bucket as remote storage
dvc remote add S3REMOTE -d s3://mlops-capstone-project-final/artifacts/

# Verify
dvc remote list
```

#### Step 3: Configure AWS Credentials
```bash
# Option 1: AWS CLI (Recommended)
aws configure

# Option 2: Environment Variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### Step 4: Enable Auto-Staging
```bash
dvc config core.autostage true
```

#### Step 5: Push/Pull Data
```bash
# Push data to S3
dvc push

# Pull data from S3
dvc pull
```

---

# PHASE 5: DATA INGESTION COMPONENT
## Loading and merging raw data

### Location: `src/components/data_ingestion.py`

### What it does:
1. Fetches data from **AWS S3** (or local source)
2. Reads `train_transaction.csv` and `train_identity.csv`
3. Merges both DataFrames on `TransactionID`
4. Saves merged data to `artifacts/data/raw/raw_data.csv`
5. Saves schema to `src/constants/schema.yaml`

### Configuration: `src/constants/config.py`
```python
@dataclass
class DataIngestionConfig:
    raw_data_dir: str = "artifacts/data/raw"
    raw_data_path: str = "artifacts/data/raw/raw_data.csv"
    nrows: Optional[int] = 10000  # None for full dataset
    bucket_name: str = "mlops-capstone-project-final"
    transaction_key: str = "train_transaction.csv"
    identity_key: str = "train_identity.csv"
```

### DVC Pipeline Stage:
```yaml
# In dvc.yaml
data_ingestion:
  cmd: python -m src.components.data_ingestion --source s3
  deps:
    - src/components/data_ingestion.py
    - src/utils/fetch_data.py
  outs:
    - artifacts/data/raw/raw_data.csv
```

### Run:
```bash
dvc repro data_ingestion
```

---

# PHASE 6: FEATURE ENGINEERING COMPONENT
## Transforming raw data into features

### Location: `src/components/data_FE_transformation.py`

### What it does:
1. **Validates schema** against `raw_data` in schema.yaml
2. Creates **transaction amount features** (log, decimal, bins)
3. Creates **time features** (hour, day, is_night, etc.)
4. Creates **card features** (card combinations, frequencies)
5. Creates **email features** (domain, vendor, TLD)
6. Creates **device features** (type, brand, browser, OS)
7. Creates **address features** (missing flags, combinations)
8. Creates **V column features** (aggregations, PCA)
9. Creates **aggregation features** (frequency counts)
10. Creates **ID features** (binary flags)
11. Creates **UID features** (unique identifiers)
12. **Preprocesses data** (train/test split, encoding, PCA)
13. Saves **Train_transformed.csv** and **Test_transformed.csv**
14. Saves schemas to `schema.yaml`

### Key Point:
Both Train and Test files include the **target column `isFraud`** for easy loading in model training.

### Configuration: `src/constants/config.py`
```python
@dataclass
class DataTransformationConfig:
    raw_data_path: str = "artifacts/data/raw/raw_data.csv"
    processed_data_dir: str = "artifacts/data/transformed"
    train_path: str = "artifacts/data/transformed/Train_transformed.csv"
    test_path: str = "artifacts/data/transformed/Test_transformed.csv"
    test_size: float = 0.2
    random_state: int = 6
```

### DVC Pipeline Stage:
```yaml
data_transformation_Feature_engineering:
  cmd: python -m src.components.data_FE_transformation
  deps:
    - src/components/data_FE_transformation.py
    - artifacts/data/raw/raw_data.csv
  outs:
    - artifacts/data/transformed/Train_transformed.csv
    - artifacts/data/transformed/Test_transformed.csv
```

### Run:
```bash
dvc repro data_transformation_Feature_engineering
```

---

# PHASE 7: MODEL TRAINING COMPONENT ✅ COMPLETED
## Training and evaluating the model

### Location: `src/components/model_training_evaluation.py`

### What it does:
1. **Initializes DagsHub + MLflow** for remote experiment tracking
2. **Loads model parameters** from `src/constants/params.yaml`
3. **Loads both** Train_transformed.csv and Test_transformed.csv
4. **Validates schemas** against schema.yaml
5. **Trains XGBClassifier** on training data
6. **Evaluates on both** train and test sets
7. **Logs to MLflow/DagsHub**:
   - Parameters
   - Metrics (accuracy, precision, recall, F1, ROC-AUC)
   - Model artifacts
8. **Saves outputs**:
   - `models/XGBClassifier_latest.joblib` (model)
   - `models/XGBClassifier_v{N}.joblib` (versioned)
   - `models/metrics.json` (for DVC tracking)
   - `models/confusion_matrix.png` (visualization)
   - `models/XGBClassifier_v{N}_metadata.yaml` (metadata)

### Configuration: `src/constants/config.py`
```python
@dataclass
class ModelTrainingConfig:
    params_yaml_path: str = "src/constants/params.yaml"
    schema_yaml_path: str = "src/constants/schema.yaml"
    train_data_path: str = "artifacts/data/transformed/Train_transformed.csv"
    test_data_path: str = "artifacts/data/transformed/Test_transformed.csv"
    model_save_dir: str = "models"
    experiment_name: str = "exp_1"
    run_name: str = "XGBClassifier_run"
    target_column: str = "isFraud"
```

### Model Parameters: `src/constants/params.yaml`
```yaml
model_params:
  XGBClassifier:
    objective: binary:logistic
    eval_metric: auc
    tree_method: hist
    device: cuda
    scale_pos_weight: 27
    max_depth: 10
    min_child_weight: 5
    learning_rate: 0.02
    n_estimators: 3000
    subsample: 0.8
    colsample_bytree: 0.7
    reg_alpha: 1
    reg_lambda: 2
    early_stopping_rounds: 80
```

### DagsHub + MLflow Integration:
```python
import dagshub
import mlflow

# Initialized at module level
dagshub.init(
    repo_owner='santosh4thmarch', 
    repo_name='IEEE-CIS-Fraud-detection', 
    mlflow=True
)
mlflow.set_tracking_uri('https://dagshub.com/santosh4thmarch/IEEE-CIS-Fraud-detection.mlflow')
```

### DVC Pipeline Stage:
```yaml
model_training:
  cmd: python -m src.components.model_training_evaluation
  deps:
    - src/components/model_training_evaluation.py
    - src/constants/config.py
    - src/constants/params.yaml
    - artifacts/data/transformed/Train_transformed.csv
    - artifacts/data/transformed/Test_transformed.csv
  params:
    - src/constants/params.yaml:
        - model_params.XGBClassifier
        - model_training
  outs:
    - models/XGBClassifier_latest.joblib
  metrics:
    - models/metrics.json:
        cache: false
  plots:
    - models/confusion_matrix.png:
        cache: false
```

### Run:
```bash
dvc repro model_training

# Push model to S3
dvc push
```

### View Experiments:
- **DagsHub MLflow UI**: https://dagshub.com/santosh4thmarch/IEEE-CIS-Fraud-detection
- **Local MLflow**: `mlflow ui` (if using local tracking)

---

# QUICK REFERENCE COMMANDS

## DVC Commands
```bash
# Run full pipeline
dvc repro

# Run specific stage
dvc repro data_ingestion
dvc repro data_transformation_Feature_engineering
dvc repro model_training

# Push to S3
dvc push

# Pull from S3
dvc pull

# View pipeline DAG
dvc dag

# Check status
dvc status
```

## Git + DVC Workflow
```bash
# After making changes
dvc repro                    # Run pipeline
dvc push                     # Push artifacts to S3
git add .
git commit -m "Update pipeline"
git push origin main
```

## Environment Setup
```bash
# Activate environment
conda activate mlops

# Set AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

---

# 📊 PROJECT STRUCTURE

```
IEEE-CIS-Fraud-detection/
├── .dvc/                           # DVC configuration
│   ├── config                      # Remote storage settings
│   └── cache/                      # Local file cache
├── artifacts/                      # DVC-tracked data (→ S3)
│   └── data/
│       ├── raw/raw_data.csv
│       └── transformed/
│           ├── Train_transformed.csv
│           └── Test_transformed.csv
├── models/                         # DVC-tracked models (→ S3)
│   ├── XGBClassifier_latest.joblib
│   ├── XGBClassifier_v1.joblib
│   ├── metrics.json
│   └── confusion_matrix.png
├── src/
│   ├── components/
│   │   ├── data_ingestion.py
│   │   ├── data_FE_transformation.py
│   │   └── model_training_evaluation.py
│   ├── constants/
│   │   ├── config.py               # Centralized configurations
│   │   ├── params.yaml             # Model hyperparameters
│   │   └── schema.yaml             # Data schemas
│   ├── logger/                     # Logging module
│   ├── exception/                  # Exception handling
│   └── utils/                      # Utility functions
├── dvc.yaml                        # DVC pipeline definition
├── dvc.lock                        # DVC pipeline state
├── requirements.txt                # Python dependencies
└── projectworkflow.md             # This file!
```

---

# 🎯 CURRENT STATUS

| Stage | Status | DVC Tracked |
|-------|--------|-------------|
| Project Setup | ✅ Complete | - |
| MLflow/DagsHub Setup | ✅ Complete | - |
| Logger & Exception | ✅ Complete | - |
| DVC + S3 Setup | ✅ Complete | ✅ |
| Data Ingestion | ✅ Complete | ✅ |
| Feature Engineering | ✅ Complete | ✅ |
| Model Training | ✅ Complete | ✅ |
| Model Evaluation | ✅ Complete | ✅ |
| Prediction Pipeline | ✅ Complete | - |
| Dockerization | ✅ Complete | - |
| CI/CD Pipeline | 🔄 Next | - |

---

# 📝 NOTES

### Model Not Saving in S3?
Since `dvc.yaml` already tracks `models/XGBClassifier_latest.joblib` as output, DVC handles the caching automatically. Just run:
```bash
dvc repro model_training
dvc push
```

### Schema Validation Failing?
The preprocessed data schemas are auto-generated. If there's a mismatch:
1. Set `strict_schema_validation: bool = False` in config
2. Or manually update `schema.yaml`

### Changing Model Parameters?
1. Edit `src/constants/params.yaml`
2. Run `dvc repro model_training`
3. DVC will detect the param change and re-run training

---


# PHASE 8: PREDICTION PIPELINE ✅ COMPLETED
## Building the inference prediction system

### Location: `src/components/prediction.py`

### What it does:
1. **Fetches latest model** from S3 bucket
2. **Loads model and preprocessor** for inference
3. **Validates input data** against the raw_data schema
4. **Applies all feature engineering** transformations
5. **Preprocesses data** for model consumption
6. **Makes predictions** using the XGBoost model
7. **Returns results** with TransactionID and prediction

### DVC is NOT used for prediction:
- Model is fetched directly from S3 using `s3_model_pusher` utility
- This keeps inference lightweight and independent

---

# PHASE 9: DOCKERIZATION ✅ COMPLETED
## Containerizing the ML Pipeline with Docker

### Overview
We're using a **microservices architecture** instead of a monolithic approach. This means we have two separate Docker containers:
- **Training Container**: Runs the DVC pipeline to train models
- **Inference Container**: Serves the FastAPI prediction API

This approach enables:
- ✅ Independent scaling of training and inference
- ✅ Kubernetes deployment (AKS/EKS) ready
- ✅ Isolated environments for each service
- ✅ Easier CI/CD integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MICROSERVICES ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────┐          ┌─────────────────────┐                  │
│   │  TRAINING CONTAINER │          │ INFERENCE CONTAINER │                  │
│   │  ─────────────────  │          │  ─────────────────  │                  │
│   │                     │          │                     │                  │
│   │  • DVC Pipeline     │  Model   │  • FastAPI Server   │                  │
│   │  • Data Ingestion   │ ──────►  │  • Model Loading    │                  │
│   │  • Feature Eng.     │  (S3)    │  • Predictions      │                  │
│   │  • Model Training   │          │  • REST API         │                  │
│   │                     │          │                     │                  │
│   └─────────────────────┘          └─────────────────────┘                  │
│            │                                │                                │
│            ▼                                ▼                                │
│   ┌─────────────────────┐          ┌─────────────────────┐                  │
│   │     AWS S3          │          │  Port 8000          │                  │
│   │  (Model Storage)    │          │  (API Endpoint)     │                  │
│   └─────────────────────┘          └─────────────────────┘                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9.1 Training Dockerfile
### Location: `docker/training.Dockerfile`

### Multi-Stage Build Strategy
We use a 2-stage build for smaller image size:

```dockerfile
# Stage 1: Builder (installs dependencies)
FROM python:3.13-slim as builder
# ... install build tools & pip packages

# Stage 2: Runtime (copies only what's needed)
FROM python:3.13-slim as runtime
# ... lean production image
```

### Key Components Explained:

| What's Copied | Why It's Needed |
|--------------|-----------------|
| `src/` | Application source code |
| `config/` | Configuration files (params.yaml, schema.yaml) |
| `dvc.yaml` | DVC pipeline definition |
| `.dvc/` | DVC remote config (S3 URLs) |

### What's NOT Copied:

| Excluded | Reason |
|----------|--------|
| `dvc.lock` | Fresh pipeline run, no cached hashes |
| `.dvc/cache/` | Large files, will pull from S3 |
| `.dvc/config.local` | Contains local secrets |
| `artifacts/` | Data pulled from S3 |
| `models/` | Model pulled from S3 |

### Training Dockerfile Structure:
```dockerfile
# Stage 1: Builder
FROM python:3.13-slim as builder
WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y build-essential git

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.13-slim as runtime
WORKDIR /app

# Runtime deps (git for DVC, libgomp1 for XGBoost)
RUN apt-get update && apt-get install -y git libgomp1

# Copy venv from builder
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

# Entry point
COPY docker/scripts/run_training.sh .
CMD ["./run_training.sh"]
```

### Training Entrypoint Script: `docker/scripts/run_training.sh`
```bash
#!/bin/bash
set -e  # Exit on error

# Initialize git (required by DVC)
git init
git config user.email "ci@example.com"
git config user.name "CI Runner"

# Configure DagsHub authentication
export DAGSHUB_USER_TOKEN=$DAGSHUB_TOKEN

# Configure DVC with AWS credentials
dvc remote modify s3remote access_key_id $AWS_ACCESS_KEY_ID
dvc remote modify s3remote secret_access_key $AWS_SECRET_ACCESS_KEY

# Pull cached data from S3
dvc pull --allow-missing --force || true

# Run training pipeline
dvc repro --force

# Push artifacts to S3
dvc push
```

---

## 9.2 Inference Dockerfile
### Location: `docker/inference.Dockerfile`

### Key Differences from Training:
- ✅ Lighter dependencies (no DVC, no git)
- ✅ Exposes port 8000 for API
- ✅ Includes healthcheck endpoint
- ✅ Uses `/tmp/models` for model caching

### Model Path Solution:
**Problem**: Local code uses `models/` but Docker needs `/tmp/models` for ephemeral storage.

**Solution**: Environment variable with fallback
```python
# In config.py
local_model_dir: str = os.getenv('MODEL_CACHE_DIR', 'models')
```

```dockerfile
# Sets it in Docker
ENV MODEL_CACHE_DIR=/tmp/models
```

This way:
- **Local**: Uses `models/` directory
- **Docker**: Uses `/tmp/models` (persists across requests, not rebuilds)

### Inference Dockerfile Structure:
```dockerfile
# Stage 1: Builder
FROM python:3.13-slim as builder
WORKDIR /app

RUN apt-get update && apt-get install -y build-essential

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Lighter requirements for inference only
COPY requirements-inference.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.13-slim as runtime
WORKDIR /app

# Runtime deps (curl for healthcheck, libgomp1 for XGBoost)
RUN apt-get update && apt-get install -y curl libgomp1

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
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

# Health check (for Kubernetes readiness probe)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI server
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 9.3 Docker Compose (Local Testing)
### Location: `docker-compose.yml`

Docker Compose orchestrates both services for local development and testing.

### Configuration:
```yaml
services:
  # Inference API Service
  inference:
    build:
      context: .
      dockerfile: docker/inference.Dockerfile
    container_name: fraud-inference
    ports:
      - "8000:8000"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
      - MODEL_CACHE_DIR=/tmp/models
    volumes:
      - model-cache:/tmp/models    # Persist model between restarts
      - ./src:/app/src             # Hot-reload for development
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  # Training Pipeline Service
  training:
    build:
      context: .
      dockerfile: docker/training.Dockerfile
    container_name: fraud-training
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - DAGSHUB_TOKEN=${DAGSHUB_TOKEN}
    volumes:
      - ./artifacts:/app/artifacts  # Inspect outputs
      - ./models:/app/models
      - ./logs:/app/logs
    restart: "no"  # Run once and exit

volumes:
  model-cache:
    name: fraud-model-cache
```

---

## 9.4 Requirements Setup

### Step 1: Export Dependencies
```bash
conda activate mlops
pip freeze > requirements.txt
```

### Step 2: Clean Up requirements.txt
Remove these lines:
- Lines with `@ file:///` (local path references)
- `-e .` (local package)
- Any weird formatting

**Why?** Docker automatically finds `src/` at `/app/src` because of `PYTHONPATH=/app`.

### Step 3: Create Inference Requirements (Optional)
For a smaller inference image:
```bash
# requirements-inference.txt (lighter version)
fastapi
uvicorn
pandas
numpy
xgboost
scikit-learn
boto3
joblib
python-dotenv
```

---

## 9.5 Environment Variables & Secrets

### Local Development (.env file):
```bash
# .env (DO NOT COMMIT!)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
DAGSHUB_TOKEN=your_dagshub_token
S3_BUCKET=mlops-capstone-project-final
```

### DagsHub Token Setup:
1. Go to DagsHub → Settings → Access Tokens
2. Create new token with MLflow permissions
3. Add to `.env` locally
4. Add to GitHub Secrets for CI/CD

### Why DAGSHUB_TOKEN?
Without it, MLflow prompts for interactive authentication which fails in Docker containers.

---

## 9.6 Docker Commands Reference

### Build Images
```bash
# Build both images
docker compose build

# Build specific image
docker build -t fraud-detection-training -f docker/training.Dockerfile .
docker build -t fraud-detection-inference -f docker/inference.Dockerfile .
```

### Run Services
```bash
# Start Inference API only
docker compose up inference
# → Access at http://localhost:8000
# → Health check at http://localhost:8000/health

# Run Training Pipeline
docker compose up training
# → Runs DVC pipeline and exits

# Start both
docker compose up

# Run in background
docker compose up -d
```

### Debug & Monitor
```bash
# View logs
docker logs -f fraud-training
docker logs -f fraud-inference

# Enter container shell
docker exec -it fraud-inference /bin/bash

# Check running containers
docker ps

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## 9.7 Project Structure After Dockerization

```
IEEE-CIS-Fraud-detection/
├── docker/
│   ├── training.Dockerfile      # Training container
│   ├── inference.Dockerfile     # Inference container
│   └── scripts/
│       └── run_training.sh      # Training entrypoint script
├── docker-compose.yml           # Local orchestration
├── requirements.txt             # Full dependencies (training)
├── requirements-inference.txt   # Minimal dependencies (inference)
├── .env                         # Local secrets (NOT committed)
├── .dockerignore                # Exclude from Docker build
└── ...
```

---

## 9.8 Docker Compose Test Status

| Service | Status | Test Command |
|---------|--------|--------------|
| Training Container | ✅ Working | `docker compose up training` |
| Inference Container | ✅ Working | `docker compose up inference` |
| Health Check | ✅ Working | `curl http://localhost:8000/health` |
| Prediction API | ✅ Working | `curl -X POST http://localhost:8000/predict` |

---

## 9.9 Key Takeaways

### Model Storage Strategy:
- **DVC Push**: Pushes data artifacts (CSVs) to S3
- **S3 Model Pusher**: Pushes trained models directly to S3
- **Inference**: Fetches model directly from S3 (no DVC needed)

### Multi-Stage Build Benefits:
- **Smaller images**: Only runtime dependencies in final image
- **Security**: Build tools not in production image
- **Caching**: Faster rebuilds when only code changes

### Environment Flexibility:
```
Local Development:  models/           (via default)
Docker Container:   /tmp/models       (via ENV variable)
Kubernetes Pod:     Persistent Volume (via mount)
```

---

## 9.10 S3 Data Flow: What Gets Pushed & Pulled? 🔄

### Visual Overview:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        S3 DATA FLOW DIAGRAM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────┐                                                    │
│  │  TRAINING SERVICE   │                                                    │
│  └──────────┬──────────┘                                                    │
│             │                                                                │
│             ▼                                                                │
│  ┌─────────────────────────────────────────────────┐                        │
│  │                   PUSHES TO S3                   │                        │
│  ├─────────────────────────────────────────────────┤                        │
│  │                                                  │                        │
│  │  📦 DVC Push (run_training.sh)                  │                        │
│  │  ─────────────────────────────                  │                        │
│  │  • artifacts/data/raw/raw_data.csv              │                        │
│  │  • artifacts/data/transformed/Train_transformed │                        │
│  │  • artifacts/data/transformed/Test_transformed  │                        │
│  │                                                  │                        │
│  │  🚀 S3 Model Pusher (model_training.py)         │                        │
│  │  ─────────────────────────────                  │                        │
│  │  • models/XGBClassifier_v{N}.joblib             │                        │
│  │  • models/XGBClassifier_v{N}_metadata.yaml      │                        │
│  │  • models/preprocessor.joblib                   │                        │
│  │                                                  │                        │
│  └─────────────────────────────────────────────────┘                        │
│                          │                                                   │
│                          ▼                                                   │
│            ┌──────────────────────────┐                                     │
│            │        AWS S3 BUCKET      │                                     │
│            │ mlops-capstone-project    │                                     │
│            └──────────────────────────┘                                     │
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────┐                        │
│  │                  PULLS FROM S3                   │                        │
│  ├─────────────────────────────────────────────────┤                        │
│  │                                                  │                        │
│  │  🔽 Inference Service (prediction.py)           │                        │
│  │  ─────────────────────────────                  │                        │
│  │  • models/XGBClassifier_latest.joblib           │                        │
│  │  • models/preprocessor.joblib                   │                        │
│  │                                                  │                        │
│  │  ❌ Does NOT pull:                              │                        │
│  │  • Training data (CSVs)                         │                        │
│  │  • DVC artifacts                                │                        │
│  │                                                  │                        │
│  └─────────────────────────────────────────────────┘                        │
│             │                                                                │
│             ▼                                                                │
│  ┌─────────────────────┐                                                    │
│  │ INFERENCE SERVICE   │                                                    │
│  └─────────────────────┘                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Training Service → S3 (PUSH)

| What | Method | S3 Path | When |
|------|--------|---------|------|
| `raw_data.csv` | `dvc push` | `s3://bucket/artifacts/data/raw/` | After data ingestion |
| `Train_transformed.csv` | `dvc push` | `s3://bucket/artifacts/data/transformed/` | After feature engineering |
| `Test_transformed.csv` | `dvc push` | `s3://bucket/artifacts/data/transformed/` | After feature engineering |
| `XGBClassifier_v{N}.joblib` | `S3ModelPusher` | `s3://bucket/models/` | After model training |
| `preprocessor.joblib` | `S3ModelPusher` | `s3://bucket/models/` | After feature engineering |
| `metadata.yaml` | `S3ModelPusher` | `s3://bucket/models/` | After model training |

### Inference Service ← S3 (PULL)

| What | Method | Pulled From | When |
|------|--------|-------------|------|
| `XGBClassifier_latest.joblib` | `fetch_model_from_s3()` | `s3://bucket/models/` | On first request or cache miss |
| `preprocessor.joblib` | `_fetch_preprocessor()` | `s3://bucket/models/` | On first request or cache miss |

### Important Notes:

1. **Two Different Push Methods**:
   - `dvc push` → For data artifacts (tracked by DVC)
   - `S3ModelPusher` → For model files (direct S3 upload, NOT tracked by DVC)

2. **Why Model is NOT DVC Tracked?**
   - Faster deployment (no DVC overhead)
   - Inference service doesn't need DVC installed
   - Simpler model versioning with `_v{N}` suffix

3. **Model Caching in Inference**:
   ```
   First Request:  S3 → /tmp/models/         (downloaded)
   Next Requests:  /tmp/models/              (cached, no download)
   Container Restart: S3 → /tmp/models/      (re-downloaded)
   ```

4. **What Inference DOES NOT Need**:
   - ❌ Training data (CSVs)
   - ❌ DVC installation
   - ❌ Git repository
   - ❌ DagsHub credentials

---

## 9.11 Quick Summary Table

| Aspect | Training Container | Inference Container |
|--------|-------------------|---------------------|
| **Purpose** | Run ML pipeline | Serve predictions |
| **Base Image** | python:3.13-slim | python:3.13-slim |
| **Needs DVC?** | ✅ Yes | ❌ No |
| **Needs Git?** | ✅ Yes (for DVC) | ❌ No |
| **Exposes Port?** | ❌ No | ✅ 8000 |
| **Pushes to S3?** | ✅ Data + Model | ❌ No |
| **Pulls from S3?** | ✅ Cached data | ✅ Model only |
| **Run Mode** | One-shot (exits) | Long-running (server) |
| **Restart Policy** | `no` | `unless-stopped` |

---



# PHASE 10: Continues Integration(CI)

## 10.1 : Code .github/workflows/c.yaml  
          - This file will have script to run ci stage like when to trigger ci, which runner you are using, ect

## 10.2 : Code test files
          - we need to test if your api endpoint is working or not , config.py is in the format that we need. etc

          - run test in local system :conda run -n mlops pytest tests/ (if env is not activated), if activated : pytest tests/
          - add these test in ci stage by modifyng ci.yaml.
          

## 10.3 Build check :
    - in this stage we have two either push:false (just build and check) or push:true (build and push the docker image)



1. On Push (to main):

CI Stage: Builds the image AND Pushes it to the registry.
CD Stage: Does NOT push. It simply Pulls the existing image that the CI stage just created and deploys it.
2. On Pull Request:

CI Stage: Builds the image to verify it works, but does NOT Push it anywhere. (It discards the image immediately after the check).
CD Stage: Typically does NOT run at all for Pull Requests.


## 10.4 Add secrect in github actions secrests: 
  - for dockerhub : name : santoshsoni4
  - for AWS ECR : name : AWS_ACCESS_KEY_ID , name: AWS_SECRET_ACCESS_KEY , name : AWS_REGION



**Last Updated**: January 31, 2026
**Author**: Santosh
**Phase**: Dockerization completed with Training & Inference microservices
