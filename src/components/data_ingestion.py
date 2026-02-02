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
from typing import Optional, Tuple

import pandas as pd
from sklearn.model_selection import train_test_split

from src.logger import logger
from src.exception import CustomException, DataIngestionException
from src.utils import Read_write_yaml_schema
from src.utils.fetch_data import Fetch_data
from config.config import DataIngestionConfig


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
            logger.info(f"Reading subset of data: {self.config.nrows} (nrows/percentage)")
        
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
            logger.info(f"Reading subset of data: {self.config.nrows} (nrows/percentage)")
        
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

    def validate_input_schemas(self, df_transaction: pd.DataFrame, df_identity: pd.DataFrame) -> bool:
        """
        Validate transaction and identity DataFrames against expected schemas.
        
        Args:
            df_transaction: Transaction DataFrame
            df_identity: Identity DataFrame
            
        Returns:
            True if schemas are valid, raises exception otherwise
        """
        logger.info("Validating input data schemas...")
        schema_yaml_path = self.config.schema_yaml_path
        
        try:
            # Validate train_transaction schema
            logger.info("Validating train_transaction schema...")
            result_transaction = Read_write_yaml_schema.compare_schema(
                df=df_transaction,
                schema_name="train_transaction",
                schema_yaml_filepath=schema_yaml_path,
                strict=True  # STRICT MODE - fail on mismatch!
            )
            logger.info("✓ train_transaction schema validation PASSED")
            
            # Validate train_identity schema
            logger.info("Validating train_identity schema...")
            result_identity = Read_write_yaml_schema.compare_schema(
                df=df_identity,
                schema_name="train_identity",
                schema_yaml_filepath=schema_yaml_path,
                strict=True  # STRICT MODE - fail on mismatch!
            )
            logger.info("✓ train_identity schema validation PASSED")
            
            return True
            
        except FileNotFoundError as e:
            logger.warning(f"Schema file not found - skipping validation (first run?): {e}")
            return True  # Allow first run without schema file
        except ValueError as e:
            logger.warning(f"Schema not defined - skipping validation (first run?): {e}")
            return True  # Allow first run without schema defined
        except Exception as e:
            logger.error(f"Schema validation FAILED: {str(e)}")
            raise DataIngestionException(e, sys)

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
            
            # Step 2: Validate input schemas BEFORE merging
            logger.info("Step 2: Validating input data schemas...")
            self.validate_input_schemas(df_transaction, df_identity)
            
            # Step 3: Merge data
            merged_df = self.merge_data(df_transaction, df_identity)
            merged_df.to_csv(self.config.raw_data_path, index=False)
            
            logger.info(f"DATA HAS BEEN SAVED AT {self.config.raw_data_path}")
            
            # Step 3: Save raw_data schema to schema.yaml
            logger.info("Saving raw_data schema to schema.yaml...")
            schema_yaml_path = self.config.schema_yaml_path
            Read_write_yaml_schema.save_dataframe_schema(
                df=merged_df,
                schema_name="raw_data",
                schema_yaml_filepath=schema_yaml_path
            )
            logger.info(f"✓ Raw data schema saved to {schema_yaml_path}")
            
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
    parser.add_argument("--nrows", type=float, default=None,
                        help="Number of rows (int) or percentage (float <= 1.0) to read.")
    
    args = parser.parse_args()
    
    # Create config - use CLI nrows if provided, otherwise use class default (10000)
    if args.nrows is not None:
        nrows_val = args.nrows
        # If input is > 1.0, treat as integer row count (e.g. 5000.0 -> 5000)
        if nrows_val > 1.0:
            nrows_val = int(nrows_val)
            
        config = DataIngestionConfig(nrows=nrows_val)
        logger.info(f"Using CLI-specified nrows: {nrows_val}")
    else:
        config = DataIngestionConfig()  # Uses default
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