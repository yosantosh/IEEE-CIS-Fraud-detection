"""
Data Ingestion Component for IEEE-CIS Fraud Detection Pipeline
===============================================================
This module handles fetching data from various sources (S3, local, etc.),
merging transaction and identity datasets, and saving processed data.

Usage with DVC:
    dvc repro data_ingestion
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
from sklearn.model_selection import train_test_split

from src.logger import logger
from src.exception import CustomException, DataIngestionException
from src.utils import Read_write_yaml_schema
from src.utils.fetch_data import Fetch_data


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class DataIngestionConfig:
    """Configuration for data ingestion paths."""
    # Paths
    raw_data_dir: str = "artifacts/data/raw"
    processed_data_dir: str = "artifacts/data/processed"
    train_path: str = "artifacts/data/processed/train.csv"
    test_path: str = "artifacts/data/processed/test.csv"
    
    # Split settings
    test_size: float = 0.2
    random_state: int = 42
    
    # S3 settings (from environment variables)
    bucket_name: str = os.getenv("S3_BUCKET_NAME", "mlops-capstone-project-final")
    transaction_key: str = "train_transaction.csv"
    identity_key: str = "train_identity.csv"
    aws_region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


# ============================================================================
# DATA INGESTION CLASS
# ============================================================================

class DataIngestion:
    """
    Data Ingestion class for IEEE-CIS Fraud Detection.
    
    Handles:
    - Fetching data from S3 or local sources
    - Merging transaction and identity datasets
    - Train/test split
    - Saving processed data
    """
    
    def __init__(self, config: Optional[DataIngestionConfig] = None):
        """Initialize with configuration."""
        self.config = config or DataIngestionConfig()
        
        # Create directories
        os.makedirs(self.config.raw_data_dir, exist_ok=True)
        os.makedirs(self.config.processed_data_dir, exist_ok=True)
        
        logger.info("DataIngestion initialized")

    def fetch_from_s3(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch transaction and identity data from S3."""
        logger.info("Fetching data from S3...")
        
        # AWS credentials from environment
        aws_creds = {
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "aws_region": self.config.aws_region
        }
        
        # Fetch transaction data
        logger.info(f"Loading: s3://{self.config.bucket_name}/{self.config.transaction_key}")
        df_transaction = Fetch_data.fetch_data_from_S3(
            bucket_name=self.config.bucket_name,
            object_key=self.config.transaction_key,
            file_format="csv",
            **aws_creds
        )
        logger.info(f"Transaction data: {df_transaction.shape}")
        
        # Fetch identity data
        logger.info(f"Loading: s3://{self.config.bucket_name}/{self.config.identity_key}")
        df_identity = Fetch_data.fetch_data_from_S3(
            bucket_name=self.config.bucket_name,
            object_key=self.config.identity_key,
            file_format="csv",
            **aws_creds
        )
        logger.info(f"Identity data: {df_identity.shape}")
        
        return df_transaction, df_identity

    def fetch_from_local(self, transaction_path: str, identity_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch transaction and identity data from local files."""
        logger.info("Fetching data from local files...")
        
        df_transaction = Fetch_data.fetch_data_from_local(
            file_path=transaction_path,
            file_format="csv"
        )
        logger.info(f"Transaction data: {df_transaction.shape}")
        
        df_identity = Fetch_data.fetch_data_from_local(
            file_path=identity_path,
            file_format="csv"
        )
        logger.info(f"Identity data: {df_identity.shape}")
        
        return df_transaction, df_identity

    def merge_data(self, df_transaction: pd.DataFrame, df_identity: pd.DataFrame) -> pd.DataFrame:
        """Merge transaction and identity datasets on TransactionID."""
        logger.info("Merging datasets on TransactionID...")
        
        merged_df = df_transaction.merge(
            df_identity, 
            how='left', 
            on='TransactionID'
        )
        
        logger.info(f"Merged data shape: {merged_df.shape}")
        return merged_df

    def split_and_save(self, df: pd.DataFrame) -> Tuple[str, str]:
        """Split data into train/test and save to disk."""
        logger.info(f"Splitting data (test_size={self.config.test_size})...")
        
        train_df, test_df = train_test_split(
            df,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=df['isFraud']
        )
        
        logger.info(f"Train: {train_df.shape}, Test: {test_df.shape}")
        
        # Save
        logger.info(f"Saving train data to {self.config.train_path}")
        train_df.to_csv(self.config.train_path, index=False)
        
        logger.info(f"Saving test data to {self.config.test_path}")
        test_df.to_csv(self.config.test_path, index=False)
        
        return self.config.train_path, self.config.test_path

    def run(self, source: str = "s3", **kwargs) -> Tuple[str, str]:
        """
        Run the complete data ingestion pipeline.
        
        Args:
            source: Data source type ("s3" or "local")
            **kwargs: Additional arguments (e.g., local file paths)
            
        Returns:
            Tuple of (train_path, test_path)
        """
        try:
            logger.info("=" * 60)
            logger.info("STARTING DATA INGESTION PIPELINE")
            logger.info("=" * 60)
            
            # Step 1: Fetch data
            if source == "s3":
                df_transaction, df_identity = self.fetch_from_s3()
            elif source == "local":
                df_transaction, df_identity = self.fetch_from_local(
                    kwargs.get("transaction_path"),
                    kwargs.get("identity_path")
                )
            else:
                raise ValueError(f"Unknown source: {source}")
            
            # Step 2: Merge data
            merged_df = self.merge_data(df_transaction, df_identity)
            
            # Step 3: Split and save
            train_path, test_path = self.split_and_save(merged_df)
            
            logger.info("=" * 60)
            logger.info("DATA INGESTION COMPLETED SUCCESSFULLY")
            logger.info(f"Train: {train_path}")
            logger.info(f"Test: {test_path}")
            logger.info("=" * 60)
            
            return train_path, test_path
            
        except Exception as e:
            logger.error(f"Data ingestion failed: {str(e)}")
            raise DataIngestionException(e, sys)


# ============================================================================
# MAIN ENTRY POINT (for DVC pipeline)
# ============================================================================

def main():
    """Main entry point for DVC pipeline."""
    import argparse
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Data Ingestion Pipeline")
    parser.add_argument("--source", type=str, default="s3", choices=["s3", "local"],
                        help="Data source (s3 or local)")
    parser.add_argument("--transaction-path", type=str, default="data/train_transaction.csv",
                        help="Local path to transaction data")
    parser.add_argument("--identity-path", type=str, default="data/train_identity.csv",
                        help="Local path to identity data")
    
    args = parser.parse_args()
    
    # Run pipeline
    ingestion = DataIngestion()
    
    if args.source == "local":
        ingestion.run(
            source="local",
            transaction_path=args.transaction_path,
            identity_path=args.identity_path
        )
    else:
        ingestion.run(source="s3")


if __name__ == "__main__":
    main()