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
    raw_data_path: str = "artifacts/data/raw/raw_data.csv"
    
    # Row limit for reading data (None = read all rows, set to int for sampling)
    # Useful for development/testing with large datasets
    nrows: Optional[int] = 1000  # e.g., 10000 for quick testing, None for full dataset
    
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
        
        if self.config.nrows:
            logger.info(f"Reading only {self.config.nrows} rows (nrows limit set)")
        
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
            nrows=self.config.nrows,  # Limit rows if specified
            **aws_creds
        )
        logger.info(f"Transaction data: {df_transaction.shape}")
        
        # Fetch identity data
        logger.info(f"Loading: s3://{self.config.bucket_name}/{self.config.identity_key}")
        df_identity = Fetch_data.fetch_data_from_S3(
            bucket_name=self.config.bucket_name,
            object_key=self.config.identity_key,
            file_format="csv",
            # Note: Don't limit identity rows - we need all to match transactions
            **aws_creds
        )
        logger.info(f"Identity data: {df_identity.shape}")
        
        return df_transaction, df_identity

    def fetch_from_local(self, transaction_path: str, identity_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch transaction and identity data from local files."""
        logger.info("Fetching data from local files...")
        
        if self.config.nrows:
            logger.info(f"Reading only {self.config.nrows} rows (nrows limit set)")
        
        df_transaction = Fetch_data.fetch_data_from_local(
            file_path=transaction_path,
            file_format="csv",
            nrows=self.config.nrows  # Limit rows if specified
        )
        logger.info(f"Transaction data: {df_transaction.shape}")
        
        df_identity = Fetch_data.fetch_data_from_local(
            file_path=identity_path,
            file_format="csv"
            # Note: Don't limit identity rows - we need all to match transactions
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
            merged_df.to_csv(self.config.raw_data_path, index=False)
            
            logger.info(f"DATA HAS BEEN SAVED AT {self.config.raw_data_path}")
            logger.info("=" * 60)
            logger.info("DATA INGESTION COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            
            
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
    parser.add_argument("--nrows", type=int, default=None,
                        help="Number of rows to read (None = all rows). Useful for testing.")
    
    args = parser.parse_args()
    
    # Create config - use CLI nrows if provided, otherwise use class default (10000)
    if args.nrows is not None:
        config = DataIngestionConfig(nrows=args.nrows)
        logger.info(f"Using CLI-specified nrows: {args.nrows}")
    else:
        config = DataIngestionConfig()  # Uses default nrows=10000
        logger.info(f"Using default nrows: {config.nrows}")
    
    # Run pipeline
    ingestion = DataIngestion(config)
    
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