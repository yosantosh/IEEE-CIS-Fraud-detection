# CI Testing Strategies for MLOps
> **Focus**: Testing Machine Learning pipelines and APIs in Continuous Integration (CI)
> **Project**: IEEE-CIS Fraud Detection

---

## 1. The MLOps Testing Challenge
In traditional software, ``Code + Business Logic = Application``.
In Machine Learning, ``Code + Data + Model = System``.

This means in CI (Continuous Integration), we cannot just test the Python code. We must verify:
1.  **The Code**: logic, API endpoints, data transformations (Standard CI).
2.  **The Data**: Schema expectations, null checks (Data Validation).
3.  **The Model**: Input/Output signatures, expected behaviors (Model Validation).

### The "testing in CI" Constraint
**Crucial Concept**: CI environments (like GitHub Actions) are **ephemeral** and **isolated**.
*   They don't have access to your private Production S3 buckets (by default).
*   They don't have GPUs.
*   They shouldn't download 5GB model files for a simple 10-second test.

**Solution**: We use **Mocking** and **Lightweight Assets**.

---

## 2. Test Categories for Our Project

| Test Type | What it validates | Where it runs | Example |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | Individual functions/components | CI Phase | "Does `process_transaction()` clean the string correctly?" |
| **API Tests** | The web server endpoints | CI Phase | "Does `POST /predict` return JSON?" (Mocked model) |
| **Schema Tests** | Data structure expectations | Pre-training | "Does the input CSV have `TransactionID`?" |
| **Integration** | Components working together | CD/Staging | "Can the container actually fetch from real S3?" |

---

## 3. Implementation: Writing Tests for CI

### 3.1 Tools We Use
*   **pytest**: The industry standard runner.
*   **unittest.mock**: To fake external dependencies (S3, Model files).
*   **FastAPI TestClient**: To test APIs without starting a real server.

### 3.2 The Code: `tests/test_api.py` Explained

We implemented this file to test our Inference API. Let's analyze why it's written this way.

#### A. The Setup
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from src.api.main import app

client = TestClient(app)
```
*   **TestClient**: Creates a "virtual" web browser that sends requests to your API function directly. No network calls involved.

#### B. Mocking the Heavy Pipeline (The "MLOps Mock")
Real ML pipelines load massive files. We **CANNOT** do this in a simple CI test.

```python
# CODE FROM: tests/test_api.py

def test_predict_batch_success():
    # 1. MOCK THE DATA
    mock_input = {"transactions": [{"TransactionID": 1001, "TransactionAmt": 50.0}]}
    
    # 2. MOCK THE RESULT
    mock_result_df = pd.DataFrame({
        "TransactionID": [1001],
        "prediction_isFraud": [0]
    })
    
    # 3. MOCK THE PIPELINE OBJECT
    mock_pipeline = MagicMock()           # Create a fake object
    mock_pipeline.model = "loaded"        # Pretend model is loaded
    mock_pipeline.predict.return_value = mock_result_df  # Force specific output
    
    # 4. INJECT THE MOCK (The Patch)
    # This tells Python: "When src.api.main asks for 'prediction_pipeline', give it my fake one"
    with patch('src.api.main.prediction_pipeline', mock_pipeline):
        response = client.post("/predict", json=mock_input)
        
        # 5. ASSERTIONS
        assert response.status_code == 200
        assert response.json()["predictions"][0]["isFraud"] == 0
```
**Why this is great for MLOps CI:**
*   **Speed**: Runs in 0.01 seconds.
*   **Safety**: Testing logic (if-statements, JSON parsing, error handling) without needing the actual ML model artifact.
*   **Independence**: Code can be verified even if S3 is down.

---

## 4. Essential Tests for IEEE-CIS Fraud Detection

Based on our specific project structure (Features, UID, Config), here are the essential tests we **must** implement.

### 4.1 Feature Engineering Tests (`tests/test_fe.py`)
Our `Data_FE_Transformation` class has complex logic (e.g., email domains, UID creation). We must verify this logic operates correctly on edge cases.

**Key Logic to Test:**
*   **Email Domain Splitting**: Does `extract_domain_parts` handle `gmail.com` vs `yahoo.co.uk` correctly?
*   **UID Generation**: Does `uid1 = card1 + addr1` work even if `addr1` is missing?
*   **Time Features**: Does `create_time_features` correctly extract hour from `TransactionDT`?

**Implementation Example:**
```python
import pandas as pd
import pytest
from src.components.data_FE_transformation import Data_FE_Transformation

def test_email_feature_logic():
    # Setup Data
    df = pd.DataFrame({
        "P_emaildomain": ["gmail.com", "yahoo.co.uk", None],
        "R_emaildomain": ["hotmail.com", "gmail.com", "unknown.net"],
        "TransactionDT": [86400, 86500, 90000] # Dummy DT
    })
    
    transformer = Data_FE_Transformation()
    
    # Run creation
    df_result = transformer.create_email_features(df)
    
    # Assert specific logic we relied on
    # 1. Vendor mapping
    assert df_result.iloc[0]['P_email_vendor'] == 'google'
    # 2. Null handling
    assert df_result.iloc[2]['P_emaildomain'] == 'missing'
    # 3. Domain Interaction
    assert df_result.iloc[0]['email_domain_match'] == 0 # gmail != hotmail
```

### 4.2 Configuration Tests (`tests/test_config.py`)
We use a centralized `config.py`. If someone changes `trans_amt_bins` to be empty or changes strict types, the pipeline might crash silently later.

**Key Logic to Test:**
*   **Bin Definitions**: Ensure bins are monotonically increasing.
*   **Critical Columns**: Ensure `uid_cols` are not empty.

**Implementation Example:**
```python
from config.config import DataTransformationConfig

def test_config_integrity():
    config = DataTransformationConfig()
    
    # 1. Check Bins
    assert len(config.trans_amt_bins) > 1
    assert config.trans_amt_bins == sorted(config.trans_amt_bins), "Bins must be sorted!"
    
    # 2. Check Required Columns
    assert 'uid1' in config.uid_cols
    assert 'card1' in config.card_cols
```

### 4.3 Schema/Pydantic Tests (`tests/test_schema.py`)
Our API uses Pydantic models. We need to ensure that invalid payloads are REJECTED by the API.

**Key Logic to Test:**
*   **Missing Fields**: What if `TransactionAmt` is missing?
*   **Wrong Types**: What if `TransactionAmt` is "Fifty" (string)?

**Implementation Example (via API Client):**
```python
def test_predict_invalid_schema():
    # Sending string instead of float for Amount
    bad_input = {"transactions": [{"TransactionID": 1, "TransactionAmt": "invalid_amount"}]}
    
    response = client.post("/predict", json=bad_input)
    assert response.status_code == 422 # Unprocessable Entity
```

---

## 5. How to Run Tests in CI

In your `.github/workflows/ci.yml`, the testing step runs all discovered tests:

```yaml
      - name: 🧪 Run Unit Tests
        run: |
          # -v: Verbose (show test names)
          # --cov: Calculate code coverage (how much code was actually run)
          # --cov-fail-under=80: Fail pipeline if coverage is <80% (Optional strictness)
          pytest tests/ -v --cov=src --cov-report=xml
```

### Understanding Code Coverage (MLOps Context)
*   **Good Coverage**: Testing the `predict()` function inputs, outputs, error handling, and data transformation logic.
*   **Bad Expectations**: You generally DO NOT test the "correctness" of the prediction (e.g., "Expected 0.98, got 0.99") in Unit Tests. That is **Model Evaluation**, which belongs in the Training Pipeline, not the CI Code Pipeline.

---

## 6. Summary Checklists for MLOps CI Tests

### ✅ DO Test:
1.  **API Contracts**: Does sending X return JSON Y?
2.  **Error Handling**: Does sending garbage data return a 400 or 500 error properly?
3.  **Data Transformers**: Does your function correctly handle `NaN` or missing columns?
4.  **Schema**: Is the input schema definition (Pydantic models) correct?

### ❌ DO NOT Test (in GitHub Actions CI):
1.  **Model Accuracy**: Do not run training here.
2.  **S3 Connectivity**: Do not use real credentials in unit tests (use Integration tests for that).
3.  **Heavy Loads**: Do not load 2GB CSV files.
