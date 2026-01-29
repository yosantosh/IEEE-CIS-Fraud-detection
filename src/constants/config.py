"""
Centralized Configuration for IEEE-CIS Fraud Detection Pipeline
================================================================
All dataclass configurations for pipeline components are defined here.
Import these configs in your component files.

Usage:
    from src.constants.config import DataIngestionConfig, DataTransformationConfig, ModelTrainingConfig
"""

import os
from dataclasses import dataclass
from typing import Optional


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
    schema_yaml_path: str = "src/constants/schema.yaml"
    
    # Row limit for reading data (None = read all rows, set to int for sampling)
    # Useful for development/testing with large datasets
    nrows: Optional[int] = 10000  # e.g., 10000 for quick testing, None for full dataset
    
    # S3 settings (from environment variables)
    bucket_name: str = os.getenv("S3_BUCKET_NAME", "mlops-capstone-project-final")
    transaction_key: str = "train_transaction.csv"
    identity_key: str = "train_identity.csv"
    aws_region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


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
    schema_yaml_path: str = "src/constants/schema.yaml"
    
    # Split settings
    test_size: float = 0.2
    random_state: int = 6
    
    # Schema settings
    raw_schema_name: str = "raw_data"
    train_schema_name: str = "preprocessed_train"
    test_schema_name: str = "preprocessed_test"


# ============================================================================
# MODEL TRAINING CONFIGURATION
# ============================================================================

@dataclass
class ModelTrainingConfig:
    """Configuration for model training pipeline."""
    # Paths
    params_yaml_path: str = "src/constants/params.yaml"
    schema_yaml_path: str = "src/constants/schema.yaml"
    train_data_path: str = "artifacts/data/transformed/Train_transformed.csv"
    test_data_path: str = "artifacts/data/transformed/Test_transformed.csv"
    model_save_dir: str = "models"
    
    # MLflow settings
    experiment_name: str = "exp_1"
    run_name: str = "XGBClassifier_run"
    tracking_uri: str = "mlruns"  # Local mlruns folder, can be set to remote
    
    # Training settings
    test_size: float = 0.13
    random_state: int = 6
    target_column: str = "isFraud"
    
    # Schema validation
    schema_name: str = "preprocessed_train"
    strict_schema_validation: bool = False  # Set True to fail on mismatch


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
    
    # Data directories
    raw_data_dir: str = "artifacts/data/raw"
    transformed_data_dir: str = "artifacts/data/transformed"
    
    # Config files
    params_yaml: str = "src/constants/params.yaml"
    schema_yaml: str = "src/constants/schema.yaml"
