"""
Centralized Configuration for IEEE-CIS Fraud Detection Pipeline
================================================================
All dataclass configurations for pipeline components are defined here.
Import these configs in your component files.

Usage:
    from config.config import DataIngestionConfig, DataTransformationConfig, ModelTrainingConfig
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


# ============================================================================
# MLFLOW / DAGSHUB CONFIGURATION
# ============================================================================

@dataclass
class MLflowConfig:
    """Configuration for MLflow and DagsHub tracking."""
    tracking_uri: str = "https://dagshub.com/santosh4thmarch/IEEE-CIS-Fraud-detection.mlflow"
    experiment_name: str = "IEEE-CIS-Fraud-Detection"
    
    @property
    def repo_owner(self) -> str:
        """Extract repo_owner from tracking_uri."""
        # URI format: https://dagshub.com/{repo_owner}/{repo_name}.mlflow
        return self.tracking_uri.replace("https://dagshub.com/", "").replace(".mlflow", "").split("/")[0]
    
    @property
    def repo_name(self) -> str:
        """Extract repo_name from tracking_uri."""
        return self.tracking_uri.replace("https://dagshub.com/", "").replace(".mlflow", "").split("/")[1]


# ============================================================================
# DATA INGESTION CONFIGURATION
# ============================================================================

@dataclass
class DataIngestionConfig:
    """Configuration for data ingestion pipeline."""
    # Paths
    raw_data_dir: str = "artifacts/data/raw"
    processed_data_dir: str = "artifacts/data/processed"
    raw_data_path: str = "artifacts/data/raw/raw_data.csv"
    schema_yaml_path: str = "config/schema.yaml"
    
    # Row limit for reading data (float for percentage, int for rows, None for all)
    nrows: Optional[float] = float(os.getenv("DATA_INGESTION_NROWS", 0.14))  # Default 10% to prevent OOM
    
    # S3 settings (from environment variables)
    bucket_name: str = os.getenv("S3_BUCKET_NAME", "mlops-capstone-project-final")
    transaction_key: str = "train_transaction.csv"
    identity_key: str = "train_identity.csv"
    aws_region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # Merge settings
    merge_on: str = "TransactionID"
    target_column: str = "isFraud"


# ============================================================================
# DATA TRANSFORMATION CONFIGURATION
# ============================================================================

@dataclass
class DataTransformationConfig:
    """Configuration for data transformation and feature engineering pipeline."""
    # Paths
    raw_data_path: str = "artifacts/data/raw/raw_data.csv"
    processed_data_dir: str = "artifacts/data/transformed"
    train_path: str = "artifacts/data/transformed/Train_transformed.csv"
    test_path: str = "artifacts/data/transformed/Test_transformed.csv"
    schema_yaml_path: str = "config/schema.yaml"
    model_dir: str = "models"  # For preprocessor.joblib
    
    # Split settings
    test_size: float = 0.2
    random_state: int = 6
    
    # Schema settings
    raw_schema_name: str = "raw_data"
    train_schema_name: str = "preprocessed_train"
    test_schema_name: str = "preprocessed_test"

    # Feature Engineering Parameters
    # Transaction Amount
    trans_amt_bins: List[int] = field(default_factory=lambda: [0, 50, 100, 200, 500, 1000, 5000, 10_000, float('inf')])
    trans_amt_labels: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6, 7])
    
    # Time Features
    time_of_day_bins: List[int] = field(default_factory=lambda: [-1, 6, 12, 18, 24])
    time_of_day_labels: List[int] = field(default_factory=lambda: [0, 1, 2, 3])
    
    # Column Groups
    card_cols: List[str] = field(default_factory=lambda: ['card1', 'card2', 'card3', 'card4', 'card5', 'card6'])
    address_cols: List[str] = field(default_factory=lambda: ['addr1', 'addr2'])
    email_domains: List[str] = field(default_factory=lambda: ['P_emaildomain', 'R_emaildomain'])
    
    # Aggregation & Frequency
    frequency_encoded_cols: List[str] = field(default_factory=lambda: [
        'card1', 'card2', 'card3', 'card4', 'card5', 'card6', 
        'addr1', 'addr2', 'P_emaildomain', 'R_emaildomain', 
        'ProductCD', 'DeviceType', 'DeviceInfo'
    ])
    aggregation_cols: List[str] = field(default_factory=lambda: ['card1', 'card2', 'addr1'])
    
    # UID Features
    uid_cols: List[str] = field(default_factory=lambda: ['uid1', 'uid2', 'uid3', 'uid4'])
    enhanced_freq_cols: List[str] = field(default_factory=lambda: [
        'uid1', 'uid2', 'uid3', 'uid4', 
        'card1', 'card2', 'addr1', 'P_emaildomain', 
        'DeviceType', 'DeviceInfo'
    ])
    
    # Email Maps
    email_vendor_map: Dict[str, str] = field(default_factory=lambda: {
        'gmail': 'google', 'yahoo': 'yahoo', 'hotmail': 'microsoft', 
        'outlook': 'microsoft', 'live': 'microsoft', 'msn': 'microsoft', 
        'icloud': 'apple', 'aol': 'aol'
    })
    
    # Preprocessing
    pca_n_components: float = 0.96
    fill_value: int = -999


# ============================================================================
# MODEL TRAINING CONFIGURATION
# ============================================================================

@dataclass
class ModelTrainingConfig:
    """Configuration for model training pipeline."""
    # Paths
    params_yaml_path: str = "config/params.yaml"
    schema_yaml_path: str = "config/schema.yaml"
    train_data_path: str = "artifacts/data/transformed/Train_transformed.csv"
    test_data_path: str = "artifacts/data/transformed/Test_transformed.csv"
    model_save_dir: str = "models"
    
    # MLflow settings (uses MLflowConfig)
    experiment_name: str = "exp_1"
    run_name: str = "XGBClassifier_run"
    
    # Training settings
    test_size: float = 0.13
    random_state: int = 6
    target_column: str = "isFraud"
    
    # Schema validation
    schema_name: str = "preprocessed_train"
    strict_schema_validation: bool = True  # STRICT MODE - fail on mismatch!


# ============================================================================
# PREDICTION CONFIGURATION
# ============================================================================

@dataclass
class PredictionConfig:
    """Configuration for prediction pipeline."""
    # S3 settings
    s3_model_uri: str = 's3://mlops-capstone-project-final/models/'
    model_name: str = "XGBClassifier"
    model_version: str = "latest"  # 'latest', 'v1', 'v2', etc.
    local_model_dir: str = os.getenv('MODEL_CACHE_DIR', 'models')
    
    # Schema settings
    schema_yaml_path: str = "config/schema.yaml"
    raw_schema_name: str = "raw_data"
    target_column: str = "isFraud"
    
    # AWS settings (from environment)
    aws_access_key: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    aws_secret_key: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    aws_region: str = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')


# ============================================================================
# COMMON PATHS (for convenience)
# ============================================================================

@dataclass
class PathConfig:
    """Common paths used across the pipeline."""
    # Root directories
    artifacts_dir: str = "artifacts"
    models_dir: str = "models"
    logs_dir: str = "logs"
    config_dir: str = "config"
    
    # Data directories
    raw_data_dir: str = "artifacts/data/raw"
    transformed_data_dir: str = "artifacts/data/transformed"
    
    # Config files
    params_yaml: str = "config/params.yaml"
    schema_yaml: str = "config/schema.yaml"


# ============================================================================
# SINGLETON INSTANCES (for easy access)
# ============================================================================

# MLflow config instance (used globally)
mlflow_config = MLflowConfig()
