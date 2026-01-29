"""
Prediction Pipeline Component for IEEE-CIS Fraud Detection
===========================================================
This module handles the complete prediction pipeline including:
- Fetching the latest model from S3
- Schema validation against raw_data schema (excluding target column)
- Applying all feature engineering transformations (inherited from Data_FE_Transformation)
- Making predictions using the loaded model

Usage:
    from src.components.prediction import PredictionPipeline
    
    pipeline = PredictionPipeline()
    result_df = pipeline.predict(input_df)  # Returns df with TransactionID and prediction_isFraud
"""

import os
import sys
import yaml
import joblib
import numpy as np
import pandas as pd
from typing import Optional, Tuple

import boto3
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline

from src.logger import logger
from src.exception import CustomException
from src.constants.config import PredictionConfig, DataTransformationConfig
from src.utils import reduce_memory, SchemaValidationError

# Import the Data_FE_Transformation class to inherit from
from src.components.data_FE_transformation import Data_FE_Transformation


# ============================================================================
# PREDICTION PIPELINE CLASS (Inherits from Data_FE_Transformation)
# ============================================================================

class PredictionPipeline(Data_FE_Transformation):
    """
    Complete Prediction Pipeline for IEEE-CIS Fraud Detection.
    
    Inherits all feature engineering methods from Data_FE_Transformation.
    
    Handles:
    - Fetching and loading models from S3
    - Schema validation (excluding target column)
    - Feature engineering transformations (inherited)
    - Preprocessing for inference
    - Making predictions
    """
    
    def __init__(self, 
                 prediction_config: Optional[PredictionConfig] = None,
                 transformation_config: Optional[DataTransformationConfig] = None):
        """
        Initialize PredictionPipeline.
        
        Args:
            prediction_config: PredictionConfig instance. If None, uses defaults.
            transformation_config: DataTransformationConfig for parent class. If None, uses defaults.
        """
        # Initialize parent class with transformation config
        super().__init__(config=transformation_config)
        
        self.prediction_config = prediction_config or PredictionConfig()
        self.model = None
        
        logger.info("Prediction Pipeline initialized (inheriting from Data_FE_Transformation)")
    
    # ========================================================================
    # MODEL FETCHING AND LOADING
    # ========================================================================
    
    def fetch_model_from_s3(self) -> str:
        """
        Fetch the latest model from S3.
        
        Returns:
            str: Local path to downloaded model
            
        Raises:
            CustomException: If download fails
        """
        logger.info(f"Fetching model from S3: {self.prediction_config.s3_model_uri}")
        
        try:
            # Parse S3 URI
            s3_path = self.prediction_config.s3_model_uri[5:]  # Remove 's3://'
            if '/' in s3_path:
                bucket_name = s3_path.split('/')[0]
                s3_prefix = '/'.join(s3_path.split('/')[1:])
                if not s3_prefix.endswith('/'):
                    s3_prefix += '/'
            else:
                bucket_name = s3_path
                s3_prefix = ''
            
            # Determine filename based on version
            if self.prediction_config.model_version == "latest":
                filename = f"{self.prediction_config.model_name}_latest.joblib"
            else:
                v = self.prediction_config.model_version.replace('v', '')
                filename = f"{self.prediction_config.model_name}_v{v}.joblib"
            
            s3_key = f"{s3_prefix}{filename}"
            local_path = os.path.join(self.prediction_config.local_model_dir, filename)
            
            # Create local directory if needed
            os.makedirs(self.prediction_config.local_model_dir, exist_ok=True)
            
            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.prediction_config.aws_access_key,
                aws_secret_access_key=self.prediction_config.aws_secret_key,
                region_name=self.prediction_config.aws_region
            )
            
            logger.info(f"Downloading s3://{bucket_name}/{s3_key} to {local_path}...")
            s3_client.download_file(bucket_name, s3_key, local_path)
            logger.info(f"✓ Model downloaded: {local_path}")
            
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to fetch model from S3: {str(e)}")
            raise CustomException(e, sys)
    
    def load_model(self, model_path: Optional[str] = None):
        """
        Load model from local path or fetch from S3 if not available.
        
        Args:
            model_path: Optional local path to model. If None, fetches from S3.
            
        Returns:
            Loaded model object
            
        Raises:
            CustomException: If model loading fails
        """
        try:
            if model_path is None:
                # Check if model exists locally
                if self.prediction_config.model_version == "latest":
                    local_path = os.path.join(
                        self.prediction_config.local_model_dir, 
                        f"{self.prediction_config.model_name}_latest.joblib"
                    )
                else:
                    v = self.prediction_config.model_version.replace('v', '')
                    local_path = os.path.join(
                        self.prediction_config.local_model_dir,
                        f"{self.prediction_config.model_name}_v{v}.joblib"
                    )
                
                if not os.path.exists(local_path):
                    logger.info(f"Model not found locally at {local_path}, fetching from S3...")
                    local_path = self.fetch_model_from_s3()
            else:
                local_path = model_path
            
            logger.info(f"Loading model from {local_path}...")
            self.model = joblib.load(local_path)
            logger.info(f"✓ Model loaded successfully: {type(self.model).__name__}")
            
            return self.model
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise CustomException(e, sys)
    
    # ========================================================================
    # SCHEMA VALIDATION
    # ========================================================================
    
    def validate_input_schema(self, df: pd.DataFrame) -> dict:
        """
        Validate input DataFrame schema against raw_data schema (excluding target column).
        
        The client won't pass the target column 'isFraud', so we compare against
        raw_data schema but exclude the target column from expected columns.
        
        Args:
            df: Input DataFrame to validate
            
        Returns:
            dict: Schema comparison result
            
        Raises:
            SchemaValidationError: If schema validation fails
        """
        logger.info("Validating input schema against raw_data schema (excluding target)...")
        
        try:
            # Read raw_data schema from yaml
            if not os.path.exists(self.prediction_config.schema_yaml_path):
                raise FileNotFoundError(f"Schema file not found: {self.prediction_config.schema_yaml_path}")
            
            with open(self.prediction_config.schema_yaml_path, 'r') as file:
                all_schemas = yaml.safe_load(file) or {}
            
            if self.prediction_config.raw_schema_name not in all_schemas:
                raise ValueError(
                    f"Schema '{self.prediction_config.raw_schema_name}' not found in {self.prediction_config.schema_yaml_path}. "
                    f"Available schemas: {list(all_schemas.keys())}"
                )
            
            expected_schema = all_schemas[self.prediction_config.raw_schema_name].copy()
            
            # Remove target column from expected schema (client won't pass it)
            if self.prediction_config.target_column in expected_schema:
                del expected_schema[self.prediction_config.target_column]
                logger.info(f"✓ Excluded target column '{self.prediction_config.target_column}' from expected schema")
            
            # Get actual schema from input df
            actual_schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
            
            # Compare columns
            expected_cols = set(expected_schema.keys())
            actual_cols = set(actual_schema.keys())
            
            missing_columns = list(expected_cols - actual_cols)
            extra_columns = list(actual_cols - expected_cols)
            
            # Log comparison results
            result = {
                'match': len(missing_columns) == 0,  # Only fail on missing columns
                'missing_columns': missing_columns,
                'extra_columns': extra_columns,
            }
            
            if result['match']:
                logger.info(f"✓ Schema validation PASSED for input data")
                if extra_columns:
                    logger.warning(f"  Extra columns in input (will be ignored): {extra_columns[:5]}...")
            else:
                logger.error(f"✗ Schema validation FAILED!")
                logger.error(f"  Missing required columns ({len(missing_columns)}): {missing_columns[:10]}...")
                raise SchemaValidationError(
                    f"Schema validation failed. Missing {len(missing_columns)} required columns. "
                    f"First 10: {missing_columns[:10]}"
                )
            
            return result
            
        except SchemaValidationError:
            raise
        except Exception as e:
            logger.error(f"Schema validation error: {str(e)}")
            raise CustomException(e, sys)
    
    # ========================================================================
    # FEATURE ENGINEERING (Uses inherited methods from Data_FE_Transformation)
    # ========================================================================
    
    def apply_feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all feature engineering steps to the input DataFrame.
        
        This uses ALL the inherited methods from Data_FE_Transformation class.
        
        Args:
            df: Input DataFrame (raw features from client)
            
        Returns:
            DataFrame with all engineered features
        """
        logger.info("=" * 60)
        logger.info("STARTING FEATURE ENGINEERING FOR PREDICTION")
        logger.info("=" * 60)
        
        try:
            # Step 1: Reduce memory usage
            logger.info("Step 1: Reducing memory usage...")
            try:
                df = reduce_memory(df)
            except Exception as e:
                logger.warning(f"Memory reduction failed (non-critical): {str(e)}")
            
            # Step 2: Transaction Amount Features (inherited)
            logger.info("Step 2: Creating transaction amount features...")
            df = self.create_transaction_amount_features(df)
            
            # Step 3: Time Features (inherited)
            logger.info("Step 3: Creating time features...")
            df = self.create_time_features(df)
            
            # Step 4: Card Features (inherited)
            logger.info("Step 4: Creating card features...")
            df = self.create_card_features(df)
            
            # Step 5: Email Features (inherited) - pass target_col but won't be used for inference
            logger.info("Step 5: Creating email features...")
            df = self.create_email_features(df, target_col=self.prediction_config.target_column)
            
            # Step 6: Device Features (inherited)
            logger.info("Step 6: Creating device features...")
            df = self.create_device_features(df)
            
            # Step 7: Address Features (inherited)
            logger.info("Step 7: Creating address features...")
            df = self.create_address_features(df)
            
            # Step 8: V-Column Features (inherited)
            logger.info("Step 8: Creating V-column features...")
            df = self.create_v_features(df)
            
            # Step 9: Aggregation Features (inherited)
            logger.info("Step 9: Creating aggregation features...")
            df = self.create_aggregation_features(df)
            
            # Step 10: ID Features (inherited)
            logger.info("Step 10: Creating ID features...")
            df = self.create_id_features(df)
            
            # Step 11: UID Features (inherited)
            logger.info("Step 11: Creating UID features...")
            df = self.create_uid_features(df)
            
            # Step 12: UID Aggregations (inherited)
            logger.info("Step 12: Creating UID aggregation features...")
            df = self.create_uid_aggregations(df)
            
            # Step 13: Enhanced Frequency Features (inherited)
            logger.info("Step 13: Creating enhanced frequency features...")
            df = self.create_enhanced_frequency_features(df)
            
            logger.info("=" * 60)
            logger.info(f"✓ Feature Engineering Complete! Shape: {df.shape}")
            logger.info("=" * 60)
            
            return df
            
        except Exception as e:
            logger.error(f"Feature engineering failed: {str(e)}")
            raise CustomException(e, sys)
    
    # ========================================================================
    # PREPROCESSING FOR INFERENCE
    # ========================================================================
    
    def preprocess_for_inference(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess feature-engineered data for inference.
        
        Similar to Data_FE_Transformation.preprocessor() but without train/test split.
        
        Args:
            df: Feature-engineered DataFrame
            
        Returns:
            Tuple of (Preprocessed DataFrame, TransactionIDs)
        """
        logger.info("Preprocessing data for inference...")
        
        try:
            # Store TransactionID for final output
            transaction_ids = df['TransactionID'].copy() if 'TransactionID' in df.columns else pd.Series(df.index)
            
            # Identify column types
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            # If 'card_id' is categorical but missing from cat_cols (e.g. if mistakenly dropped), ensure it's handled if present
            
            # Use the full dataframe as X, but create a copy to avoid side effects
            X = df.copy()
            
            # Identify column types again based on X
            cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
            v_cols = [c for c in X.columns if c.startswith('V')]
            num_cols = [c for c in X.select_dtypes(include=np.number).columns.tolist() if c not in v_cols]
            
            # Ensure categorical columns are uniformly strings
            for col in cat_cols:
                X[col] = X[col].astype(str)
            
            logger.info(f"Categorical columns: {len(cat_cols)}, Numerical columns: {len(num_cols)}, V columns: {len(v_cols)}")
            
            # LOAD PREPROCESSOR from 'models/preprocessor.joblib'
            preprocessor_path = os.path.join("models", "preprocessor.joblib")
            
            if not os.path.exists(preprocessor_path):
                # Fallback to model directory if 'models' relative path fails
                preprocessor_path = os.path.join(self.config.model_dir, "preprocessor.joblib")
                
            if not os.path.exists(preprocessor_path):
                raise FileNotFoundError(f"Preprocessor not found at {preprocessor_path}. Please run feature engineering pipeline first.")
                
            logger.info(f"Loading preprocessor from {preprocessor_path}...")
            preprocessor = joblib.load(preprocessor_path)
            
            # Enforce types based on preprocessor expectations to handle string inputs (e.g. from JSON)
            if hasattr(preprocessor, 'transformers_'):
                for name, trans, cols in preprocessor.transformers_:
                    # Skip remainder or dropped columns
                    if name == 'remainder' or trans == 'drop': 
                        continue
                        
                    # Handle 'num' and 'pca' transformers -> expect numeric
                    if name in ['num', 'pca']:
                        for col in cols:
                            if col in X.columns:
                                X[col] = pd.to_numeric(X[col], errors='coerce')
                                
                    # Handle 'cat' transformer -> expect string
                    elif name == 'cat':
                        for col in cols:
                            if col in X.columns:
                                X[col] = X[col].astype(str)
            
            # Transform (do NOT fit)
            X_processed = preprocessor.transform(X)
            
            logger.info(f"✓ Preprocessing complete! Shape: {X_processed.shape}")
            
            return X_processed, transaction_ids
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {str(e)}")
            raise CustomException(e, sys)
    
    # ========================================================================
    # MAIN PREDICTION METHOD
    # ========================================================================
    
    def predict(self, df: pd.DataFrame, model_path: Optional[str] = None) -> pd.DataFrame:
        """
        Complete prediction pipeline: validate schema, engineer features, preprocess, predict.
        
        Args:
            df: Input DataFrame with raw features (same schema as raw_data.csv except isFraud)
            model_path: Optional local path to model. If None, fetches from S3.
            
        Returns:
            DataFrame with columns: ['TransactionID', 'prediction_isFraud']
            
        Raises:
            SchemaValidationError: If input schema doesn't match expected schema
            CustomException: If any step fails
        """
        logger.info("=" * 80)
        logger.info("STARTING FRAUD DETECTION PREDICTION PIPELINE")
        logger.info("=" * 80)
        
        try:
            # Step 1: Store TransactionID
            if 'TransactionID' not in df.columns:
                logger.warning("TransactionID not found in input, using index as TransactionID")
                df['TransactionID'] = df.index
            
            transaction_ids = df['TransactionID'].copy()
            logger.info(f"✓ Input data shape: {df.shape}, Transactions: {len(transaction_ids)}")
            
            # Step 2: Validate input schema
            logger.info("Step 1: Validating input schema...")
            self.validate_input_schema(df)
            
            # Step 3: Load model
            logger.info("Step 2: Loading model...")
            if self.model is None:
                self.load_model(model_path)
            
            # Step 4: Apply feature engineering (using inherited methods)
            logger.info("Step 3: Applying feature engineering...")
            df_engineered = self.apply_feature_engineering(df.copy())
            
            # Step 5: Preprocess for inference
            logger.info("Step 4: Preprocessing for inference...")
            X_processed, _ = self.preprocess_for_inference(df_engineered)
            
            # Step 6: Make predictions
            logger.info("Step 5: Making predictions...")
            predictions = self.model.predict(X_processed)
            
            # Step 7: Create output DataFrame
            result_df = pd.DataFrame({
                'TransactionID': transaction_ids.values,
                'prediction_isFraud': predictions
            })
            
            # Log summary
            fraud_count = (predictions == 1).sum()
            fraud_rate = fraud_count / len(predictions) * 100
            
            logger.info("=" * 80)
            logger.info("✓ PREDICTION COMPLETE!")
            logger.info(f"  Total transactions: {len(result_df)}")
            logger.info(f"  Predicted fraud: {fraud_count} ({fraud_rate:.2f}%)")
            logger.info(f"  Predicted non-fraud: {len(result_df) - fraud_count}")
            logger.info("=" * 80)
            
            return result_df
            
        except SchemaValidationError:
            raise
        except Exception as e:
            logger.error(f"Prediction pipeline failed: {str(e)}")
            raise CustomException(e, sys)
    
    def predict_proba(self, df: pd.DataFrame, model_path: Optional[str] = None) -> pd.DataFrame:
        """
        Predict with probability scores.
        
        Args:
            df: Input DataFrame with raw features
            model_path: Optional local path to model. If None, fetches from S3.
            
        Returns:
            DataFrame with columns: ['TransactionID', 'prediction_isFraud', 'fraud_probability']
        """
        logger.info("=" * 80)
        logger.info("STARTING FRAUD DETECTION PREDICTION PIPELINE (WITH PROBABILITIES)")
        logger.info("=" * 80)
        
        try:
            # Store TransactionID
            if 'TransactionID' not in df.columns:
                df['TransactionID'] = df.index
            
            transaction_ids = df['TransactionID'].copy()
            
            # Validate schema
            self.validate_input_schema(df)
            
            # Load model
            if self.model is None:
                self.load_model(model_path)
            
            # Apply feature engineering (using inherited methods)
            df_engineered = self.apply_feature_engineering(df.copy())
            
            # Preprocess
            X_processed, _ = self.preprocess_for_inference(df_engineered)
            
            # Predictions and probabilities
            predictions = self.model.predict(X_processed)
            probabilities = self.model.predict_proba(X_processed)[:, 1]  # Probability of fraud (class 1)
            
            # Create output DataFrame
            result_df = pd.DataFrame({
                'TransactionID': transaction_ids.values,
                'prediction_isFraud': predictions,
                'fraud_probability': probabilities
            })
            
            fraud_count = (predictions == 1).sum()
            logger.info(f"✓ Prediction complete! Predicted fraud: {fraud_count}/{len(result_df)}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Prediction pipeline failed: {str(e)}")
            raise CustomException(e, sys)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def predict_fraud(df: pd.DataFrame, model_version: str = "latest") -> pd.DataFrame:
    """
    Convenience function for quick predictions.
    
    Args:
        df: Input DataFrame with raw features (same schema as raw_data.csv except isFraud)
        model_version: Model version to use ('latest', 'v1', 'v2', etc.)
        
    Returns:
        DataFrame with columns: ['TransactionID', 'prediction_isFraud']
        
    Example:
        >>> from src.components.prediction import predict_fraud
        >>> result = predict_fraud(my_data_df)
        >>> print(result.head())
    """
    config = PredictionConfig(model_version=model_version)
    pipeline = PredictionPipeline(prediction_config=config)
    return pipeline.predict(df)


# ============================================================================
# MAIN ENTRY POINT (for testing)
# ============================================================================

def main():
    """Test the prediction pipeline with sample data."""
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logger.info("Testing Prediction Pipeline...")
    
    # Load sample data (raw_data.csv without isFraud column)
    try:
        sample_data = pd.read_csv("artifacts/data/raw/raw_data.csv", nrows=100)
        
        # Remove target column (simulating client input)
        if 'isFraud' in sample_data.columns:
            sample_data = sample_data.drop('isFraud', axis=1)
        
        logger.info(f"Sample data shape: {sample_data.shape}")
        
        # Run prediction
        pipeline = PredictionPipeline()
        result = pipeline.predict(sample_data)
        
        print("\n" + "=" * 50)
        print("PREDICTION RESULTS:")
        print("=" * 50)
        print(result.head(10))
        print(f"\nTotal predictions: {len(result)}")
        print(f"Fraud predictions: {(result['prediction_isFraud'] == 1).sum()}")
        
    except FileNotFoundError:
        logger.warning("Sample data not found. Skipping test.")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")


if __name__ == "__main__":
    main()
