# IEEE-CIS Fraud Detection - Complete EDA & Feature Engineering Guide

## 📌 Project Overview

This project tackles the **IEEE-CIS Fraud Detection** Kaggle competition challenge. The goal is to build a machine learning model that can accurately detect fraudulent online transactions. This is a real-world problem provided by **Vesta Corporation**, one of the leading payment service providers.

**Why is this important?**
- **Financial losses**: Fraud costs businesses billions of dollars annually
- **Customer trust**: Detecting fraud protects users and builds confidence
- **Automation**: Reduces manual review workload by automatically flagging risky transactions

---

## 📊 Dataset Description

The dataset consists of **two main tables** that need to be combined:

### 1. Transaction Table (~590K training rows, ~507K test rows)
Contains transaction details with **394 columns** including:

| Column | Description | Example Values |
|--------|-------------|----------------|
| `TransactionID` | Unique identifier for each transaction | 2987000, 2987001 |
| `isFraud` | **Target variable** (1 = Fraud, 0 = Legitimate) | 0, 1 |
| `TransactionDT` | Time elapsed in seconds from a reference point | 86400 (= 1 day) |
| `TransactionAmt` | Transaction amount in USD | $68.50, $29.00 |
| `ProductCD` | Product category code | W, H, C, S, R |
| `card1-card6` | Card information (hashed/anonymized) | card1: 13926, card4: visa |
| `addr1, addr2` | Billing address codes | 315, 87 |
| `P_emaildomain` | Purchaser's email domain | gmail.com, yahoo.com |
| `R_emaildomain` | Recipient's email domain | gmail.com, hotmail.com |
| `C1-C14` | Counting features (anonymized) | Various counts |
| `D1-D15` | Time delta features (days since events) | 14 days, 0 days |
| `M1-M9` | Match features (T/F flags) | T, F |
| `V1-V339` | Vesta engineered features (anonymized) | Various values |

### 2. Identity Table (~144K training rows, ~142K test rows)
Contains device and network information with **41 columns**:

| Column | Description | Example Values |
|--------|-------------|----------------|
| `DeviceType` | Type of device used | mobile, desktop |
| `DeviceInfo` | Device details | SAMSUNG SM-G892A |
| `id_12-id_38` | Identity verification features | New, Found, NotFound |
| `id_30` | Operating system | Android 7.0, iOS 11.2 |
| `id_31` | Browser information | samsung browser 6.2, chrome |
| `id_33` | Screen resolution | 2220x1080 |

---

## ⚠️ Key Challenges

### 1. **Severe Class Imbalance**
```
Legitimate transactions: 96.5% (569,877)
Fraudulent transactions:  3.5% (20,663)
```
This means a naive model predicting "not fraud" for everything would be 96.5% accurate but completely useless!

### 2. **Anonymized Features**
Many columns (V1-V339, C1-C14) are masked/encrypted. We can't interpret them directly, but we can use statistical patterns.

### 3. **High Dimensionality**
Over 400 raw features, which we expand to 550+ through engineering.

---

## 🎯 Evaluation Metric: ROC-AUC

We use **ROC-AUC** (Area Under the Receiver Operating Characteristic Curve) instead of accuracy because:

1. **Handles class imbalance**: Unlike accuracy, ROC-AUC isn't fooled by predicting the majority class
2. **Threshold independent**: Evaluates the model's ability to rank predictions across ALL possible thresholds
3. **Probabilistic interpretation**: Represents the probability that the model ranks a random fraud case higher than a random legitimate case

---

## 🔧 Step-by-Step Pipeline

### Step 1: Data Loading and Merging

We load 4 CSV files and merge them:
```python
Train_df = train_transaction.merge(train_identity, on='TransactionID', how='left')
Test_df = test_transaction.merge(test_identity, on='TransactionID', how='left')
```

**Why LEFT join?**
- Transaction table has ALL transactions
- Identity table only has info for ~24% of transactions
- LEFT join keeps all transactions, filling missing identity info with NaN

**Result**: 
- Training: 590,540 rows × 434 columns
- Testing: 506,691 rows × 433 columns

---

### Step 2: Memory Optimization

**Problem**: The dataset uses too much memory (1.9 GB for training alone)

**Solution**: Downcast data types based on actual value ranges:
- If max value < 127: use `int8` instead of `int64`
- If max value < 32,767: use `int16` instead of `int64`
- Use `float32` instead of `float64` for decimals

**Result**: Memory reduced from 1955 MB → 1044 MB (**46.6% reduction**)

---

### Step 3: Exploratory Data Analysis (EDA)

#### Target Distribution
```
Not Fraud (0): 569,877 (96.50%)
Fraud (1):      20,663 (3.50%)
```

#### Key Fraud Patterns Discovered:

**By Card Type:**
| Card Network | Card Type | Fraud Rate | Fraud Count |
|--------------|-----------|------------|-------------|
| Visa | Debit | 2.5% | 7,669 |
| Visa | Credit | 6.8% | 5,704 |
| Mastercard | Credit | 6.9% | 3,511 |
| Discover | Credit | 7.9% | 500 |

**By Email Domain:**
| Domain | Fraud Rate | Fraud Count |
|--------|------------|-------------|
| gmail.com | 4.4% | 9,943 |
| hotmail.com | 5.3% | 2,396 |
| outlook.com | **9.5%** | 482 |
| mail.com | **19.0%** | 106 |

**By Device/OS:**
Certain iOS + Safari combinations show elevated fraud rates (~9-17%).

---

### Step 4: Feature Engineering (135 New Features Created)

#### 4.1 Transaction Amount Features

| Feature | What it does | Why it matters |
|---------|--------------|----------------|
| `TransactionAmt_log` | Log transform of amount | Normalizes skewed distribution |
| `TransactionAmt_decimal` | Extracts decimal part (cents) | Bots often use round numbers |
| `TransactionAmt_is_round` | Flag if amount is whole number | Human vs. bot behavior |
| `TransactionAmt_is_micro` | Flag if amount < $10 | Fraudsters test cards with tiny amounts |
| `amount_jump_ratio` | Current / Previous amount | Detects sudden spending spikes |
| `rolling_median_amt` | Median of last 5 transactions | User's "normal" spending pattern |
| `amt_vs_rolling` | Current / Rolling median | How unusual is this transaction? |
| `amt_repeat_count` | Same amount used multiple times | Automated fraud patterns |

**Example of amount jump detection:**
```
Transaction history: $5 → $100 → $800
amount_jump_ratio:   NaN → 20x  → 8x  🚨 Suspicious!
```

#### 4.2 Time Features

| Feature | What it does | Why it matters |
|---------|--------------|----------------|
| `Transaction_hour` | Hour of day (0-23) | Fraud often happens at night |
| `Transaction_is_night` | Flag if 12am-6am | Night transactions are riskier |
| `Transaction_is_business_hour` | Flag if 9am-5pm | Normal behavior pattern |
| `Transaction_time_gap` | Seconds since last transaction | Detects rapid-fire bot activity |
| `Transaction_hour_sin/cos` | Cyclical encoding of hour | Helps model understand 11pm → 1am is close |

#### 4.3 Card & Address Features

| Feature | What it does | Why it matters |
|---------|--------------|----------------|
| `card_id` | Unique card fingerprint (card1-6 combined) | Identifies individual users |
| `card1_addr1` | Card + address combination | Detects card used from new locations |
| `card_id_count` | How many times this card appears | High-velocity card = suspicious |
| `card1_ProductCD` | Card + product type combination | Unusual product for this card |

#### 4.4 Email Features

| Feature | What it does | Why it matters |
|---------|--------------|----------------|
| `P_email_vendor` | Email provider (google, microsoft, etc.) | Some providers have higher fraud |
| `email_domain_match` | Does purchaser = recipient email? | Mismatch can indicate fraud |
| `email_presence` | Which emails are present | Missing emails = suspicious |
| `P_domain_fraud_rate` | Historical fraud rate of domain | Target encoding for email |

#### 4.5 Device Features

| Feature | What it does | Why it matters |
|---------|--------------|----------------|
| `DeviceType_is_mobile` | Is it a mobile device? | Mobile has different fraud patterns |
| `Device_brand` | Extracted brand (Samsung, Apple) | Certain brands used more in fraud |
| `Browser_is_chrome/safari/etc` | Browser identification | Some browsers = fraud farms |
| `OS_is_Windows/Mac/iOS/Android` | Operating system | Helps identify device profile |
| `Screen_area` | Width × Height | Unusual resolutions = emulators |

#### 4.6 V-Column Aggregations

The V columns (V1-V339) are Vesta's proprietary features. We group correlated columns and create:
- **Sum**: Total magnitude of activity
- **Mean**: Average value
- **Std**: Variability (high std = erratic behavior)
- **NaN count**: Missing values often indicate something

#### 4.7 Aggregation Features (C and D columns)

| Feature | What it does |
|---------|--------------|
| `card1_TransactionAmt_mean` | Average spend for this card |
| `card1_TransactionAmt_std` | Spending variability |
| `card1_TransactionAmt_dev` | How far is THIS transaction from card's average |

---

### Step 5: Results Summary

| Metric | Value |
|--------|-------|
| Original features | 434 |
| New features created | 135 |
| Total features | 569 |
| Memory after optimization | 1,335 MB |
| Memory saved | ~39% |

---

## 🚀 How to Run

### Prerequisites

1. **Clone the repository**
```bash
git clone https://github.com/santosh4thmarch/IEEE-CIS-Fraud-detection.git
cd IEEE-CIS-Fraud-detection
```

2. **Create and activate conda environment**
```bash
conda create -n mlops python=3.13 -y
conda activate mlops
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install dvc python-dotenv
```

4. **Set up AWS credentials** (for S3 data access)
```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your actual credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

---

## 🔐 AWS Credentials Management

### Understanding the Two Files

| File | Purpose | Contains Secrets? | Commit to Git? |
|------|---------|-------------------|----------------|
| **`.env`** | Your **actual** AWS credentials | ✅ YES | ❌ **NEVER** (gitignored) |
| **`.env.example`** | Template showing required variables | ❌ NO (placeholders only) | ✅ YES |

### How Credentials Are Loaded

This project uses **`python-dotenv`** to automatically load credentials. Here's the flow:

```python
# In data_ingestion.py
from dotenv import load_dotenv

load_dotenv()  # ← Reads .env file and loads into environment

# Then accessed via os.getenv()
aws_creds = {
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_DEFAULT_REGION")
}
```

### Key Points

1. **You DON'T need to manually `export` environment variables**
   - Just save credentials in `.env` file
   - `load_dotenv()` automatically loads them into the process

2. **Your `.env` file should look like:**
   ```bash
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   AWS_DEFAULT_REGION=us-east-1
   ```

3. **Security Best Practices:**
   - ✅ `.env` is already in `.gitignore`
   - ✅ Never commit credentials to Git
   - ✅ Use `.env.example` to show others what variables are needed
   - ✅ Rotate credentials if accidentally exposed

### Getting AWS Credentials

1. Go to [AWS Console](https://console.aws.amazon.com)
2. Navigate to **IAM → Users → Your User → Security Credentials**
3. Click **Create Access Key**
4. Download and save securely
5. Copy to your `.env` file



## 🔄 DVC Pipeline

This project uses **DVC (Data Version Control)** for reproducible ML pipelines.

### What is DVC?

DVC is a tool that helps manage:
- **Data versioning**: Track large files without storing them in Git
- **Pipeline automation**: Define and run ML pipelines with dependencies
- **Reproducibility**: Recreate exact results from any previous run

### Installing DVC

```bash
# Install DVC in your conda environment
pip install dvc

# Initialize DVC in the project (already done)
dvc init
```

### Pipeline Configuration (`dvc.yaml`)

The pipeline is defined in `dvc.yaml`:

```yaml
stages:
  data_ingestion:
    cmd: python -m src.data.data_ingestion --source s3
    deps:
      - src/data/data_ingestion.py
      - src/utils/fetch_data.py
      - config/config.yaml
    outs:
      - artifacts/data/processed/train.csv
      - artifacts/data/processed/test.csv
    params:
      - config/config.yaml:
          - data_ingestion.test_size
          - data_ingestion.random_state
```

**Key concepts:**
- `cmd`: The command to run for this stage
- `deps`: Files this stage depends on (if changed, stage reruns)
- `outs`: Output files produced by this stage
- `params`: Config parameters to track for changes

### Running the Pipeline

```bash
# Activate environment
conda activate mlops

# Run the entire pipeline
dvc repro

# Run a specific stage
dvc repro data_ingestion

# View pipeline structure
dvc dag

# Check what stages need to be run
dvc status
```

### DVC Commands Cheat Sheet

| Command | Description |
|---------|-------------|
| `dvc repro` | Run the entire pipeline |
| `dvc repro <stage>` | Run a specific stage and its dependencies |
| `dvc dag` | Visualize pipeline as a DAG |
| `dvc status` | Show which stages are outdated |
| `dvc push` | Push tracked data to remote storage |
| `dvc pull` | Pull tracked data from remote storage |

---

## 📦 Data Ingestion Component

### Overview

The **Data Ingestion** component is the first stage of the ML pipeline. It handles:

1. **Fetching data** from S3 (or local files)
2. **Merging** transaction and identity datasets
3. **Splitting** into train/test sets
4. **Saving** processed data to disk

### Component Files

```
IEEE-CIS-Fraud-detection/
├── src/
│   ├── data/
│   │   └── data_ingestion.py    # Main data ingestion class
│   ├── utils/
│   │   ├── fetch_data.py        # S3, MongoDB, BigQuery, PostgreSQL, Local fetchers
│   │   └── __init__.py          # YAML read/write utilities
│   ├── logger/
│   │   └── __init__.py          # Logging configuration
│   └── exception/
│       └── __init__.py          # Custom exception classes
├── config/
│   └── config.yaml              # Pipeline configuration
├── .env                         # AWS credentials (gitignored)
├── .env.example                 # Credential template
└── dvc.yaml                     # DVC pipeline definition
```

### File Descriptions

| File | Purpose |
|------|---------|
| `src/data/data_ingestion.py` | Main orchestrator - fetches, merges, splits, and saves data |
| `src/utils/fetch_data.py` | Data fetching adapters for multiple sources (S3, MongoDB, BigQuery, PostgreSQL, Local) |
| `src/logger/__init__.py` | Centralized logging with rotating file handler |
| `src/exception/__init__.py` | Custom exceptions for each pipeline stage |
| `config/config.yaml` | All pipeline parameters (bucket names, paths, split ratios) |
| `.env` | Sensitive credentials (AWS keys) - **never commit this!** |
| `dvc.yaml` | Pipeline stage definitions for DVC |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA INGESTION PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │     S3       │    │   .env       │                           │
│  │   Bucket     │◄───│ (credentials)│                           │
│  └──────┬───────┘    └──────────────┘                           │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────┐                           │
│  │ fetch_data.py                    │                           │
│  │ - fetch_data_from_S3()           │                           │
│  │ - fetch_data_from_local()        │                           │
│  └──────────────┬───────────────────┘                           │
│                 │                                                │
│         ┌───────┴───────┐                                       │
│         │               │                                        │
│         ▼               ▼                                        │
│  ┌─────────────┐ ┌─────────────┐                                │
│  │ Transaction │ │  Identity   │                                │
│  │   (590K)    │ │   (144K)    │                                │
│  └──────┬──────┘ └──────┬──────┘                                │
│         │               │                                        │
│         └───────┬───────┘                                       │
│                 │ MERGE (LEFT JOIN on TransactionID)            │
│                 ▼                                                │
│         ┌─────────────┐                                         │
│         │   Merged    │                                         │
│         │ (590K×434)  │                                         │
│         └──────┬──────┘                                         │
│                │ TRAIN/TEST SPLIT (80/20, stratified)           │
│         ┌──────┴──────┐                                         │
│         │             │                                          │
│         ▼             ▼                                          │
│  ┌─────────────┐ ┌─────────────┐                                │
│  │  train.csv  │ │  test.csv   │                                │
│  │  (472K)     │ │  (118K)     │                                │
│  └─────────────┘ └─────────────┘                                │
│                                                                  │
│  📁 Output: artifacts/data/processed/                           │
└─────────────────────────────────────────────────────────────────┘
```

### Running Data Ingestion

**Option 1: Via DVC (Recommended)**
```bash
dvc repro data_ingestion
```

**Option 2: Direct Python**
```bash
# From S3
python -m src.data.data_ingestion --source s3

# From local files
python -m src.data.data_ingestion --source local \
    --transaction-path data/train_transaction.csv \
    --identity-path data/train_identity.csv
```

### Configuration (`config/config.yaml`)

```yaml
data_ingestion:
  source_type: "s3"
  
  s3:
    bucket_name: "mlops-capstone-project-final"
    transaction_key: "train_transaction.csv"
    identity_key: "train_identity.csv"
    region: "us-east-1"
  
  test_size: 0.2
  random_state: 42
  target_column: "isFraud"
  merge_on: "TransactionID"
```

### Output Artifacts

After running data ingestion:

```
artifacts/
└── data/
    └── processed/
        ├── train.csv    # Training data (80%)
        └── test.csv     # Test data (20%)
```

---

## 📁 Project Structure

```
IEEE-CIS-Fraud-detection/
│
├── 📊 Data & Notebooks
│   ├── notebooks/                   # Jupyter notebooks for EDA
│   └── data/                        # Local data files (optional)
│
├── 🔧 Source Code
│   ├── src/
│   │   ├── data/
│   │   │   └── data_ingestion.py    # Data ingestion component
│   │   ├── features/                # Feature engineering
│   │   ├── models/                  # Model training & evaluation
│   │   ├── utils/
│   │   │   ├── fetch_data.py        # Multi-source data fetchers
│   │   │   └── __init__.py          # YAML utilities
│   │   ├── logger/                  # Logging setup
│   │   ├── exception/               # Custom exceptions
│   │   └── constants/
│   │       └── schema.yaml          # Data schema definitions
│   │
├── ⚙️ Configuration
│   ├── config/
│   │   └── config.yaml              # Pipeline parameters
│   ├── .env                         # Credentials (gitignored)
│   ├── .env.example                 # Credential template
│   └── dvc.yaml                     # DVC pipeline definition
│
├── 📦 Artifacts (generated)
│   └── artifacts/
│       ├── data/
│       │   ├── raw/                 # Raw merged data
│       │   └── processed/           # Train/test splits
│       ├── features/                # Engineered features
│       ├── models/                  # Trained models
│       └── metrics/                 # Evaluation metrics
│
├── 📝 Documentation
│   ├── README.md                    # This file
│   └── LICENSE                      # MIT License
│
└── 🔒 Git/DVC
    ├── .gitignore                   # Git ignore rules
    ├── .dvc/                        # DVC internals
    └── dvc.lock                     # DVC lock file
```

---

## 🔗 Resources

- **Competition Page**: [IEEE-CIS Fraud Detection](https://www.kaggle.com/competitions/ieee-fraud-detection)
- **Dataset**: [Kaggle Data](https://www.kaggle.com/competitions/ieee-fraud-detection/data)
- **Vesta Corporation**: Dataset provider

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Vesta Corporation** for providing this real-world fraud detection dataset
- **IEEE Computational Intelligence Society** for sponsoring the competition
- **Kaggle** for hosting the competition platform
