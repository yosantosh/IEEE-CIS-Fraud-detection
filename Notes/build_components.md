# Building Project Components 🏗️

This document details how we implemented the core building blocks of our MLOps pipeline. We followed a modular design ensuring code reusability, proper error handling, and robust logging.

---

## 1. The Foundation Modules
Before building the actual ML pipelines (Ingestion/Training), we established three critical support modules.

### 1.1 The Logger (`src/logger`)
**Goal:** To stop using `print()` statements. We need a persistent record of what happened, when it happened, and where it went wrong.

**Implementation:**
- We created `src/logger/__init__.py`.
- We configured the standard python `logging` library to write logs to a `logs/` directory with timestamps.
- **Key Detail:** We set the format to include `[timestamp] - module_name - line_number - message`.

**Usage:**
```python
from src.logger import logger
logger.info("Starting data ingestion...")
```

### 1.2 Custom Exceptions (`src/exception`)
**Goal:** Standard Python errors (like `ValueError`) don't tell us *which file* or *line number* caused the crash in a complex pipeline.

**Implementation:**
- We created a `CustomException` class that inherits from Python's built-in `Exception`.
- It captures `sys.exc_info()` automatically when initialized.
- It formats the error message to say: *"Error occurred in python script name [X] line number [Y] error message [Z]"*.

### 1.3 Utilities (`src/utils`)
**Goal:** Don't repeat code. Common tasks like reading YAML files or saving binary objects should be defined once.

**Key functions we built:**
- `read_yaml()`: Safely loads `params.yaml` or `schema.yaml`.
- `save_object()` / `load_object()`: Wrappers around `dill` or `joblib` for saving pickle files.
- `reduce_memory()`: A smart function that iterates through DataFrame columns and downcasts types (e.g., `float64` -> `float32`) to save RAM.

---

## 2. Configuration Management
We separated **Code** from **Config**.
- **Code** (`src/`) defines *how* to do things.
- **Config** (`params.yaml`, `config.py`) defines *what* to use (paths, hyperparameters).

We used Python `dataclasses` to strongly type our configuration. For example, `DataIngestionConfig` automatically validates that we have all necessary paths before the pipeline even starts.

---

## 3. The Core Components
We implemented the pipeline in stages, where each stage depends on the previous one's output (Artifacts).

### 3.1 Data Ingestion (`src/components/data_ingestion.py`)
- **Input:** S3 bucket URL or local path.
- **Logic:** Reads raw CSVs (`identity` and `transaction`), merges them on `TransactionID`, and saves the raw artifacts.
- **Output:** `raw_data.csv`.

### 3.2 Feature Engineering (`src/components/data_FE_transformation.py`)
- **Input:** `raw_data.csv`.
- **Logic:** This is the heavy lifter. It performs strict schema validation, fills missing values, creating substantial new features (time-based, aggregations), and splits data into Train/Test sets.
- **Output:** `Train_transformed.csv` and `Test_transformed.csv`.

### 3.3 Model Training (`src/components/model_training_evaluation.py`)
- **Input:** Transformed Train/Test CSVs.
- **Logic:** Loads XGBoost parameters from `params.yaml`, trains the model, and logs everything to **MLflow/DagsHub**.
- **Output:** `model.joblib` and evaluation metrics.

---

## 4. The Prediction Pipeline (`src/components/prediction.py`)
Unlike the training components (which are run via DVC), the Prediction Pipeline is designed for **Inference**. It does not split data or calculate metrics. It simply:
1. Loads the saved model from S3.
2. Accepts a single or batch input.
3. Applies the *exact same* transformations as step 3.2.
4. Returns the fraud probability.
