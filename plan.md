# IEEE-CIS Fraud Detection: Complete Solution Guide

## Table of Contents
1. [Competition Overview](#1-competition-overview)
2. [Data Loading & Memory Optimization](#2-data-loading--memory-optimization)
3. [Exploratory Data Analysis (EDA)](#3-exploratory-data-analysis-eda)
4. [Feature Engineering](#4-feature-engineering)
5. [Feature Selection](#5-feature-selection)
6. [Model Training](#6-model-training)
7. [Model Ensembling](#7-model-ensembling)
8. [Submission Strategy](#8-submission-strategy)

---

## 1. Competition Overview

### 1.1 Problem Statement
- **Objective**: Predict the probability that an online transaction is fraudulent (`isFraud` = 1)
- **Evaluation Metric**: ROC-AUC (Area Under the Receiver Operating Characteristic Curve)
- **Key Insight**: The real task is predicting **fraudulent clients (credit cards)**, not just transactions

### 1.2 Dataset Description
| File | Description | Size |
|------|-------------|------|
| `train_transaction.csv` | Transaction data with target | 590,540 rows × 394 columns |
| `test_transaction.csv` | Transaction data for prediction | 506,691 rows × 393 columns |
| `train_identity.csv` | Identity info linked to transactions | ~144K rows |
| `test_identity.csv` | Identity info for test set | ~141K rows |

### 1.3 Column Categories
```
Transaction Data:
├── TransactionID      # Unique identifier
├── TransactionDT      # Timedelta from reference datetime (seconds)
├── TransactionAmt     # Transaction amount (USD)
├── ProductCD          # Product code (W, H, C, S, R)
├── card1-card6        # Card information (type, category, bank)
├── addr1, addr2       # Address (billing region, country)
├── dist1, dist2       # Distance
├── P_emaildomain      # Purchaser email domain
├── R_emaildomain      # Recipient email domain
├── C1-C14             # Counting features (cumulative)
├── D1-D15             # Timedelta features (days)
├── M1-M9              # Match features (T/F)
└── V1-V339            # Vesta engineered features

Identity Data:
├── id_01-id_38        # Identity information
├── DeviceType         # Desktop/Mobile
└── DeviceInfo         # Device details
```

---

## 2. Data Loading & Memory Optimization

### 2.1 Initial Setup
```python
import numpy as np
import pandas as pd
import os, sys, gc, warnings, random, datetime
from sklearn import metrics
from sklearn.model_selection import KFold, GroupKFold
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb
from catboost import CatBoostClassifier
import xgboost as xgb

warnings.filterwarnings('ignore')

# Set seed for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
os.environ['PYTHONHASHSEED'] = str(SEED)

TARGET = 'isFraud'
START_DATE = datetime.datetime.strptime('2017-11-30', '%Y-%m-%d')
```

### 2.2 Memory Reduction Function
```python
def reduce_mem_usage(df, verbose=True):
    """Reduce memory usage by downcasting numerical columns."""
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
    start_mem = df.memory_usage().sum() / 1024**2
    
    for col in df.columns:
        col_type = df[col].dtypes
        if col_type in numerics:
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df[col] = df[col].astype(np.float16)
                elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                    
    end_mem = df.memory_usage().sum() / 1024**2
    if verbose:
        print(f'Mem. usage decreased to {end_mem:5.2f} Mb ({100*(start_mem-end_mem)/start_mem:.1f}% reduction)')
    return df
```

### 2.3 Load Data
```python
# Load transaction data
train_transaction = pd.read_csv('train_transaction.csv')
test_transaction = pd.read_csv('test_transaction.csv')

# Load identity data
train_identity = pd.read_csv('train_identity.csv')
test_identity = pd.read_csv('test_identity.csv')

# Merge transaction and identity
train_df = train_transaction.merge(train_identity, on='TransactionID', how='left')
test_df = test_transaction.merge(test_identity, on='TransactionID', how='left')

# Apply memory reduction
train_df = reduce_mem_usage(train_df)
test_df = reduce_mem_usage(test_df)

# Cleanup
del train_transaction, test_transaction, train_identity, test_identity
gc.collect()

print(f'Train shape: {train_df.shape}, Test shape: {test_df.shape}')
```

---

## 3. Exploratory Data Analysis (EDA)

### 3.1 Target Distribution
```python
fraud_rate = train_df[TARGET].mean()
print(f'Fraud Rate: {fraud_rate:.4f} ({fraud_rate*100:.2f}%)')
# Expected: ~3.5% fraud rate (highly imbalanced)
```

### 3.2 Time Analysis
```python
# Convert TransactionDT to datetime
train_df['DT'] = train_df['TransactionDT'].apply(
    lambda x: START_DATE + datetime.timedelta(seconds=x)
)

# Extract time features
train_df['DT_M'] = (train_df['DT'].dt.year - 2017) * 12 + train_df['DT'].dt.month
train_df['DT_W'] = (train_df['DT'].dt.year - 2017) * 52 + train_df['DT'].dt.weekofyear
train_df['DT_D'] = (train_df['DT'].dt.year - 2017) * 365 + train_df['DT'].dt.dayofyear
train_df['DT_hour'] = train_df['DT'].dt.hour
train_df['DT_day_week'] = train_df['DT'].dt.dayofweek
train_df['DT_day_month'] = train_df['DT'].dt.day

# Key insight: Training data spans months 12-17, test data is month 18+
# There's a ~1 month gap between train and test
```

### 3.3 Card Analysis
```python
# Card1 distribution - most important card feature
# Many card1 values appear only in train OR test (not both)
train_cards = set(train_df['card1'].unique())
test_cards = set(test_df['card1'].unique())
common_cards = train_cards.intersection(test_cards)
print(f'Common cards: {len(common_cards)}, Train only: {len(train_cards - test_cards)}')

# Filter rare cards (appear <= 2 times)
valid_cards = train_df['card1'].value_counts()
valid_cards = valid_cards[valid_cards > 2].index
```

### 3.4 V Columns NaN Pattern Analysis
```python
# V columns have specific NaN patterns that indicate transaction type
nans_groups = {}
nans_df = train_df[['V' + str(i) for i in range(1, 340)]].isna()

for col in nans_df.columns:
    nan_count = nans_df[col].sum()
    if nan_count not in nans_groups:
        nans_groups[nan_count] = []
    nans_groups[nan_count].append(col)

# Columns with same NaN count are highly correlated
print(f'Number of NaN groups: {len(nans_groups)}')
```

### 3.5 Key EDA Insights
1. **Fraud is time-dependent**: Different fraud rates across months/weeks
2. **68.2% of test clients are NEW** (not in training data)
3. **Card columns are critical**: card1 + card2 combinations identify unique clients
4. **D columns are time deltas**: D1 = days since first transaction for that card
5. **C columns are cumulative counts**: C1-C14 only increase over time
6. **V columns have hierarchical NaN patterns**: Groups share missing values

---

## 4. Feature Engineering

### 4.1 Time Features
```python
from pandas.tseries.holiday import USFederalHolidayCalendar as calendar

dates_range = pd.date_range(start='2017-10-01', end='2019-01-01')
us_holidays = calendar().holidays(start=dates_range.min(), end=dates_range.max())

for df in [train_df, test_df]:
    # Convert to datetime
    df['DT'] = df['TransactionDT'].apply(lambda x: START_DATE + datetime.timedelta(seconds=x))
    
    # Time periods for aggregation
    df['DT_M'] = ((df['DT'].dt.year - 2017) * 12 + df['DT'].dt.month).astype(np.int8)
    df['DT_W'] = ((df['DT'].dt.year - 2017) * 52 + df['DT'].dt.weekofyear).astype(np.int8)
    df['DT_D'] = ((df['DT'].dt.year - 2017) * 365 + df['DT'].dt.dayofyear).astype(np.int16)
    
    # Time features
    df['DT_hour'] = df['DT'].dt.hour.astype(np.int8)
    df['DT_day_week'] = df['DT'].dt.dayofweek.astype(np.int8)
    df['DT_day_month'] = df['DT'].dt.day.astype(np.int8)
    
    # Special periods
    df['is_december'] = (df['DT'].dt.month == 12).astype(np.int8)
    df['is_holiday'] = df['DT'].dt.date.astype('datetime64').isin(us_holidays).astype(np.int8)
```

### 4.2 UID Detection (THE MAGIC FEATURE)
This is the most critical feature engineering step from the 1st place solution.

```python
# Step 1: Clean card columns - remove outliers
for col in ['card1']:
    valid_card = pd.concat([train_df[[col]], test_df[[col]]])
    valid_card = valid_card[col].value_counts()
    valid_card = valid_card[valid_card > 2].index.tolist()
    
    train_df[col] = np.where(train_df[col].isin(test_df[col]), train_df[col], np.nan)
    test_df[col] = np.where(test_df[col].isin(train_df[col]), test_df[col], np.nan)
    
    train_df[col] = np.where(train_df[col].isin(valid_card), train_df[col], np.nan)
    test_df[col] = np.where(test_df[col].isin(valid_card), test_df[col], np.nan)

# Step 2: Create UIDs (Virtual Client IDs)
for df in [train_df, test_df]:
    # Basic UID from card info
    df['uid'] = df['card1'].astype(str) + '_' + df['card2'].astype(str)
    
    # Extended UID with more card info
    df['uid2'] = df['uid'] + '_' + df['card3'].astype(str) + '_' + df['card5'].astype(str)
    
    # UID with address
    df['uid3'] = df['uid2'] + '_' + df['addr1'].astype(str) + '_' + df['addr2'].astype(str)
    
    # UID with email domains
    df['uid4'] = df['uid3'] + '_' + df['P_emaildomain'].astype(str)
    df['uid5'] = df['uid3'] + '_' + df['R_emaildomain'].astype(str)
    
    # Bank type
    df['bank_type'] = df['card3'].astype(str) + '_' + df['card5'].astype(str)

# Step 3: D column transformation for client identification
for df in [train_df, test_df]:
    for col in ['D1', 'D2', 'D3', 'D4', 'D5', 'D10', 'D11', 'D15']:
        new_col = 'uid_td_' + col
        df[new_col] = df['TransactionDT'] / (24 * 60 * 60)  # Convert to days
        df[new_col] = np.floor(df[new_col] - df[col])  # Registration date
```

### 4.3 Frequency Encoding
```python
def frequency_encoding(train_df, test_df, columns, self_encoding=False):
    """Encode categorical features with their frequency."""
    for col in columns:
        temp_df = pd.concat([train_df[[col]], test_df[[col]]])
        fq_encode = temp_df[col].value_counts(dropna=False).to_dict()
        
        if self_encoding:
            train_df[col] = train_df[col].map(fq_encode)
            test_df[col] = test_df[col].map(fq_encode)
        else:
            train_df[col + '_fq_enc'] = train_df[col].map(fq_encode)
            test_df[col + '_fq_enc'] = test_df[col].map(fq_encode)
    
    return train_df, test_df

# Apply frequency encoding
fq_columns = ['card1', 'card2', 'card3', 'card5', 'uid', 'uid2', 'uid3', 'uid4', 'uid5',
              'P_emaildomain', 'R_emaildomain', 'addr1', 'addr2', 'ProductCD']
train_df, test_df = frequency_encoding(train_df, test_df, fq_columns)
```

### 4.4 Aggregation Features
```python
def uid_aggregation(train_df, test_df, main_columns, uids, aggregations):
    """Create aggregation features based on UIDs."""
    for main_column in main_columns:
        for uid in uids:
            for agg_type in aggregations:
                new_col = f'{uid}_{main_column}_{agg_type}'
                temp_df = pd.concat([train_df[[uid, main_column]], test_df[[uid, main_column]]])
                temp_df = temp_df.groupby([uid])[main_column].agg([agg_type]).reset_index()
                temp_df = temp_df.rename(columns={agg_type: new_col})
                temp_df.index = temp_df[uid]
                temp_dict = temp_df[new_col].to_dict()
                
                train_df[new_col] = train_df[uid].map(temp_dict)
                test_df[new_col] = test_df[uid].map(temp_dict)
    
    return train_df, test_df

# Apply aggregations
main_cols = ['TransactionAmt', 'D1', 'D10', 'D15', 'C13']
uids = ['uid', 'uid2', 'uid3', 'card1', 'card2']
aggs = ['mean', 'std', 'min', 'max', 'count', 'nunique']

train_df, test_df = uid_aggregation(train_df, test_df, main_cols, uids, aggs)
```

### 4.5 Time-Block Features
```python
def timeblock_frequency_encoding(train_df, test_df, periods, columns):
    """Create frequency encoding within time blocks."""
    for period in periods:
        for col in columns:
            new_col = f'{col}_{period}'
            train_df[new_col] = train_df[col].astype(str) + '_' + train_df[period].astype(str)
            test_df[new_col] = test_df[col].astype(str) + '_' + test_df[period].astype(str)
            
            temp_df = pd.concat([train_df[[new_col]], test_df[[new_col]]])
            fq_encode = temp_df[new_col].value_counts().to_dict()
            
            train_df[new_col] = train_df[new_col].map(fq_encode)
            test_df[new_col] = test_df[new_col].map(fq_encode)
    
    return train_df, test_df

# Apply time-block encoding
periods = ['DT_M', 'DT_W', 'DT_D']
columns = ['uid', 'card1', 'card2', 'addr1']
train_df, test_df = timeblock_frequency_encoding(train_df, test_df, periods, columns)
```

### 4.6 Transaction Amount Features
```python
for df in [train_df, test_df]:
    # Decimal part analysis
    df['TransactionAmt_decimal'] = ((df['TransactionAmt'] - df['TransactionAmt'].astype(int)) * 1000).astype(int)
    
    # Log transformation
    df['TransactionAmt_log'] = np.log1p(df['TransactionAmt'])
    
    # Check if round amount
    df['TransactionAmt_check'] = (df['TransactionAmt'] == df['TransactionAmt'].astype(int)).astype(np.int8)
```

### 4.7 V Columns NaN Groups
```python
# Group V columns by NaN pattern and aggregate
nans_df = train_df[['V' + str(i) for i in range(1, 340)]].isna()
nans_groups = {}

for col in nans_df.columns:
    nan_count = nans_df[col].sum()
    if nan_count not in nans_groups:
        nans_groups[nan_count] = []
    nans_groups[nan_count].append(col)

for nan_count, cols in nans_groups.items():
    train_df[f'nan_group_sum_{nan_count}'] = train_df[cols].sum(axis=1)
    train_df[f'nan_group_mean_{nan_count}'] = train_df[cols].mean(axis=1)
    test_df[f'nan_group_sum_{nan_count}'] = test_df[cols].sum(axis=1)
    test_df[f'nan_group_mean_{nan_count}'] = test_df[cols].mean(axis=1)
```

---

## 5. Feature Selection

### 5.1 Remove Useless Features
```python
remove_features = [
    'TransactionID', 'TransactionDT',  # Pure identifiers
    TARGET,
    'DT', 'DT_M', 'DT_W', 'DT_D',  # Temporary time features
    'DT_hour', 'DT_day_week', 'DT_day_month',
    'uid', 'uid2', 'uid3', 'uid4', 'uid5',  # UIDs (use for aggregation only)
    'bank_type',
]

# Remove features not in test or with too many unique values
for col in train_df.columns:
    if col not in test_df.columns and col != TARGET:
        remove_features.append(col)
```

### 5.2 Feature Importance Based Selection
```python
def get_feature_importance(train_df, features, target, params):
    """Train a quick model to get feature importances."""
    X = train_df[features]
    y = train_df[target]
    
    # Handle categoricals
    for col in X.columns:
        if X[col].dtype == 'object':
            X[col] = X[col].fillna('unknown')
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
    
    train_data = lgb.Dataset(X, label=y)
    model = lgb.train(params, train_data, num_boost_round=500)
    
    importance = pd.DataFrame({
        'feature': features,
        'importance': model.feature_importance()
    }).sort_values('importance', ascending=False)
    
    return importance

# Get important features
lgb_params_quick = {
    'objective': 'binary',
    'metric': 'auc',
    'verbosity': -1,
    'num_leaves': 64,
    'learning_rate': 0.05,
}

features = [c for c in train_df.columns if c not in remove_features]
importance = get_feature_importance(train_df, features, TARGET, lgb_params_quick)

# Keep top features (e.g., top 400)
top_features = importance['feature'].head(400).tolist()
```

### 5.3 Remove Duplicate Features
```python
# Remove columns with identical values
cols_sum = {}
for col in train_df.columns:
    if train_df[col].dtype not in ['datetime64[ns]', 'category', 'object']:
        col_sum = train_df[col].mean()
        if col_sum not in cols_sum:
            cols_sum[col_sum] = []
        cols_sum[col_sum].append(col)

# Find and remove duplicates
for col_sum, cols in cols_sum.items():
    if len(cols) > 1:
        for col in cols[1:]:
            if train_df[cols[0]].equals(train_df[col]):
                print(f'Removing duplicate: {col}')
                if col in features:
                    features.remove(col)
```

---

## 6. Model Training

### 6.1 Validation Strategy
```python
# CRITICAL: Use time-based validation to mimic test conditions
# Training: months 12-17, skip month 17, validate on month 18 (or similar)

def create_time_split(df, train_months, val_months):
    """Create train/validation split based on months."""
    train_mask = df['DT_M'].isin(train_months)
    val_mask = df['DT_M'].isin(val_months)
    return train_mask, val_mask

# Option 1: Simple time split
train_months = [12, 13, 14, 15, 16]  # Skip month 17 (gap)
val_months = [17]  # Use last month for validation

# Option 2: GroupKFold by month
def grouped_kfold_predictions(train_df, test_df, features, target, params, n_folds=6):
    """Train with GroupKFold using month as group."""
    folds = GroupKFold(n_splits=n_folds)
    X = train_df[features]
    y = train_df[target]
    groups = train_df['DT_M']
    
    oof = np.zeros(len(train_df))
    predictions = np.zeros(len(test_df))
    
    for fold, (train_idx, val_idx) in enumerate(folds.split(X, y, groups)):
        print(f'Fold {fold}')
        
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        # LightGBM
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val)
        
        model = lgb.train(
            params,
            train_data,
            valid_sets=[train_data, val_data],
            num_boost_round=10000,
            callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)]
        )
        
        oof[val_idx] = model.predict(X_val)
        predictions += model.predict(test_df[features]) / n_folds
    
    print(f'OOF AUC: {metrics.roc_auc_score(y, oof):.5f}')
    return predictions, oof
```

### 6.2 LightGBM Model
```python
lgb_params = {
    'objective': 'binary',
    'boosting_type': 'gbdt',
    'metric': 'auc',
    'n_jobs': -1,
    'learning_rate': 0.01,
    'num_leaves': 256,
    'max_depth': -1,
    'tree_learner': 'serial',
    'colsample_bytree': 0.7,
    'subsample_freq': 1,
    'subsample': 0.7,
    'max_bin': 255,
    'verbose': -1,
    'seed': SEED,
}

lgb_predictions, lgb_oof = grouped_kfold_predictions(
    train_df, test_df, features, TARGET, lgb_params
)
```

### 6.3 CatBoost Model
```python
cat_params = {
    'n_estimators': 5000,
    'learning_rate': 0.07,
    'eval_metric': 'AUC',
    'loss_function': 'Logloss',
    'random_seed': SEED,
    'metric_period': 500,
    'od_wait': 500,
    'task_type': 'GPU',  # Use 'CPU' if no GPU
    'depth': 8,
}

# Identify categorical features for CatBoost
categorical_features = [
    'ProductCD', 'card4', 'card6', 'P_emaildomain', 'R_emaildomain',
    'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9',
    'DeviceType', 'DeviceInfo',
]

def train_catboost(train_df, test_df, features, target, params, cat_features, n_folds=6):
    folds = GroupKFold(n_splits=n_folds)
    X = train_df[features]
    y = train_df[target]
    groups = train_df['DT_M']
    
    oof = np.zeros(len(train_df))
    predictions = np.zeros(len(test_df))
    
    # Prepare categorical features
    cat_features_idx = [features.index(c) for c in cat_features if c in features]
    
    for fold, (train_idx, val_idx) in enumerate(folds.split(X, y, groups)):
        print(f'Fold {fold}')
        
        model = CatBoostClassifier(**params)
        model.fit(
            X.iloc[train_idx], y.iloc[train_idx],
            eval_set=(X.iloc[val_idx], y.iloc[val_idx]),
            cat_features=cat_features_idx,
            use_best_model=True,
            verbose=500
        )
        
        oof[val_idx] = model.predict_proba(X.iloc[val_idx])[:, 1]
        predictions += model.predict_proba(test_df[features])[:, 1] / n_folds
    
    print(f'OOF AUC: {metrics.roc_auc_score(y, oof):.5f}')
    return predictions, oof

cat_predictions, cat_oof = train_catboost(
    train_df, test_df, features, TARGET, cat_params, categorical_features
)
```

### 6.4 XGBoost Model
```python
xgb_params = {
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'tree_method': 'gpu_hist',  # Use 'hist' if no GPU
    'learning_rate': 0.01,
    'max_depth': 9,
    'subsample': 0.7,
    'colsample_bytree': 0.7,
    'seed': SEED,
}

def train_xgboost(train_df, test_df, features, target, params, n_folds=6):
    folds = GroupKFold(n_splits=n_folds)
    X = train_df[features]
    y = train_df[target]
    groups = train_df['DT_M']
    
    oof = np.zeros(len(train_df))
    predictions = np.zeros(len(test_df))
    
    for fold, (train_idx, val_idx) in enumerate(folds.split(X, y, groups)):
        print(f'Fold {fold}')
        
        train_data = xgb.DMatrix(X.iloc[train_idx], label=y.iloc[train_idx])
        val_data = xgb.DMatrix(X.iloc[val_idx], label=y.iloc[val_idx])
        
        model = xgb.train(
            params,
            train_data,
            num_boost_round=10000,
            evals=[(train_data, 'train'), (val_data, 'valid')],
            early_stopping_rounds=100,
            verbose_eval=200
        )
        
        oof[val_idx] = model.predict(val_data)
        predictions += model.predict(xgb.DMatrix(test_df[features])) / n_folds
    
    print(f'OOF AUC: {metrics.roc_auc_score(y, oof):.5f}')
    return predictions, oof

xgb_predictions, xgb_oof = train_xgboost(
    train_df, test_df, features, TARGET, xgb_params
)
```

---

## 7. Model Ensembling

### 7.1 Simple Weighted Average
```python
# Simple average
ensemble_predictions = (lgb_predictions + cat_predictions + xgb_predictions) / 3

# Weighted average based on CV scores
weights = [0.4, 0.35, 0.25]  # LGB, CatBoost, XGBoost
ensemble_predictions = (
    weights[0] * lgb_predictions +
    weights[1] * cat_predictions +
    weights[2] * xgb_predictions
)

# Validate ensemble
ensemble_oof = (
    weights[0] * lgb_oof +
    weights[1] * cat_oof +
    weights[2] * xgb_oof
)
print(f'Ensemble OOF AUC: {metrics.roc_auc_score(train_df[TARGET], ensemble_oof):.5f}')
```

### 7.2 Rank Average (More Robust)
```python
from scipy.stats import rankdata

def rank_average(predictions_list):
    """Ensemble by averaging ranks."""
    ranked = [rankdata(p) for p in predictions_list]
    return np.mean(ranked, axis=0)

ensemble_predictions = rank_average([lgb_predictions, cat_predictions, xgb_predictions])
```

### 7.3 Stacking
```python
from sklearn.linear_model import LogisticRegression

# Create stacking features from OOF predictions
stack_features = np.column_stack([lgb_oof, cat_oof, xgb_oof])
stack_test = np.column_stack([lgb_predictions, cat_predictions, xgb_predictions])

# Train meta-model
meta_model = LogisticRegression(C=1.0)
meta_model.fit(stack_features, train_df[TARGET])

# Final predictions
final_predictions = meta_model.predict_proba(stack_test)[:, 1]
print(f'Stacked OOF AUC: {metrics.roc_auc_score(train_df[TARGET], meta_model.predict_proba(stack_features)[:, 1]):.5f}')
```

---

## 8. Submission Strategy

### 8.1 Create Submission File
```python
submission = pd.DataFrame({
    'TransactionID': test_df['TransactionID'],
    'isFraud': ensemble_predictions
})

submission.to_csv('submission.csv', index=False)
print(f'Submission shape: {submission.shape}')
print(submission.head())
```

### 8.2 Post-Processing Tips
```python
# Clip predictions to valid range
submission['isFraud'] = submission['isFraud'].clip(0.0001, 0.9999)

# Optional: Apply UID-based adjustments
# If you identified UIDs, transactions from same UID should have similar predictions
```

---

## Key Takeaways

1. **UID Detection is Critical**: The "magic feature" that won the competition was identifying unique clients through card and time delta columns

2. **Time-Based Validation**: Always use time-based splits to mimic the real test scenario

3. **Feature Engineering > Model Tuning**: Heavy feature engineering (aggregations, frequency encoding) contributed more than model hyperparameter tuning

4. **Handle New Clients**: 68% of test clients are unseen - focus on features that generalize

5. **Memory Management**: Essential for large datasets - use `reduce_mem_usage()` early

6. **Ensemble Diverse Models**: Combine LightGBM, CatBoost, and XGBoost for robust predictions

---

## Expected Results

| Model | CV AUC | Public LB | Private LB |
|-------|--------|-----------|------------|
| LightGBM | ~0.93 | ~0.94 | ~0.93 |
| CatBoost | ~0.93 | ~0.94 | ~0.93 |
| XGBoost | ~0.92 | ~0.93 | ~0.92 |
| Ensemble | ~0.94 | ~0.95 | ~0.94 |

**1st Place Solution achieved: 0.945914 Private LB**
