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
8. [Quick Reference Commands](#quick-reference-commands)

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
| Model Deployment | 🔄 Next | - |

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


# PHASE-8 : Prediction Pipeline for inference.  

**Last Updated**: January 29, 2026
**Author**: Santosh
**Commit**: Model training component completed with MLflow/DagsHub + S3 integration
