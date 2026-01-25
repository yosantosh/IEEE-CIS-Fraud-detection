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

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/IEEE-CIS-Fraud-detection.git
cd IEEE-CIS-Fraud-detection
```

2. **Install dependencies**
```bash
pip install numpy pandas matplotlib seaborn scikit-learn lightgbm tldextract
```

3. **Download the dataset**
   - Go to [Kaggle Competition](https://www.kaggle.com/competitions/ieee-fraud-detection/data)
   - Download and place files in `/kaggle/input/ieee-fraud-detection/`

4. **Run the notebook**
   - Open `eda-ieee-cis-fraud-detection.ipynb` in Jupyter/Kaggle
   - Execute all cells

---

## 📁 Project Structure

```
IEEE-CIS-Fraud-detection/
├── eda-ieee-cis-fraud-detection.ipynb   # Main EDA & Feature Engineering notebook
├── README.md                             # This documentation
├── LICENSE                               # MIT License
└── .gitignore                           # Git ignore rules
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
