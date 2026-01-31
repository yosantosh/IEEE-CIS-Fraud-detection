"""
Model Training & Evaluation Component for IEEE-CIS Fraud Detection Pipeline
=============================================================================
This module handles model training with MLflow integration, schema validation,
evaluation on both train and test sets, and proper model versioning/saving.

Usage with DVC:
    dvc repro model_training
"""

import os
import sys
import json
import joblib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Load environment variables from .env FIRST (before any imports that use them)
from dotenv import load_dotenv
load_dotenv()

# Set DagsHub token from .env (DagsHub library looks for DAGSHUB_USER_TOKEN)
if os.getenv('DAGSHUB_TOKEN'):
    os.environ['DAGSHUB_USER_TOKEN'] = os.getenv('DAGSHUB_TOKEN')

import pandas as pd
import numpy as np
import dagshub
import mlflow
import mlflow.xgboost
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBClassifier
from sklearn.metrics import (
    precision_score, f1_score, roc_auc_score,
    accuracy_score, recall_score, average_precision_score,
    confusion_matrix, classification_report
)

from src.logger import logger
from src.exception import CustomException
from src.utils import Read_write_yaml_schema, compare_schema_for_model_training, S3ModelUploader, convert_xgboost_to_onnx
from config.config import ModelTrainingConfig, PredictionConfig, mlflow_config


# ============================================================================
# DAGSHUB + MLFLOW CONFIGURATION (loaded from config.py)
# ============================================================================

# Initialize DagsHub for remote MLflow tracking
dagshub.init(
    repo_owner=mlflow_config.repo_owner,
    repo_name=mlflow_config.repo_name,
    mlflow=True
)

# Set MLflow tracking URI
mlflow.set_tracking_uri(mlflow_config.tracking_uri)

logger.info(f"✓ DagsHub MLflow tracking initialized")
logger.info(f"  Repo: {mlflow_config.repo_owner}/{mlflow_config.repo_name}")
logger.info(f"  URI: {mlflow_config.tracking_uri}")


# ============================================================================
# MODEL TRAINING CLASS
# ============================================================================

class ModelTraining:
    """
    Model Training class for IEEE-CIS Fraud Detection.
    
    Handles:
    - Loading separate train and test datasets
    - Schema validation of input data
    - Model training with XGBClassifier on training data
    - Evaluation on both train and test data
    - MLflow experiment tracking and logging
    - Model saving with version management
    - Metrics saving to JSON for DVC tracking
    """
    
    def __init__(self, config: Optional[ModelTrainingConfig] = None):
        """
        Initialize ModelTraining with configuration.
        
        Args:
            config: ModelTrainingConfig instance. If None, uses defaults.
            
        Raises:
            CustomException: If params.yaml cannot be loaded
        """
        self.config = config or ModelTrainingConfig()
        self.model = None
        self.metrics = {}
        self.run_id = None
        
        # Load model params from YAML (required - no fallback)
        try:
            params_config = Read_write_yaml_schema.read_yaml(self.config.params_yaml_path)
            self.model_params = dict(params_config.model_params.XGBClassifier)
            logger.info(f"✓ Loaded model parameters from {self.config.params_yaml_path}")
            logger.info(f"  Parameters: {self.model_params}")
        except FileNotFoundError:
            logger.error(f"params.yaml not found at: {self.config.params_yaml_path}")
            raise CustomException(
                FileNotFoundError(f"params.yaml not found: {self.config.params_yaml_path}"), 
                sys
            )
        except KeyError as e:
            logger.error(f"Missing required key in params.yaml: {str(e)}")
            raise CustomException(e, sys)
        except Exception as e:
            logger.error(f"Failed to load params.yaml: {str(e)}")
            raise CustomException(e, sys)
        
        # Create model save directory
        os.makedirs(self.config.model_save_dir, exist_ok=True)
        
        logger.info("ModelTraining initialized")

    def load_train_data(self) -> pd.DataFrame:
        """
        Load preprocessed training data from CSV.
        
        Returns:
            DataFrame with preprocessed features and target
        """
        logger.info(f"Loading training data from {self.config.train_data_path}...")
        
        try:
            if not os.path.exists(self.config.train_data_path):
                raise FileNotFoundError(f"Training data not found: {self.config.train_data_path}")
            
            df = pd.read_csv(self.config.train_data_path)
            logger.info(f"✓ Train data loaded. Shape: {df.shape}")
            
            if self.config.target_column not in df.columns:
                raise ValueError(f"Target column '{self.config.target_column}' not in train data")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load training data: {str(e)}")
            raise CustomException(e, sys)

    def load_test_data(self) -> pd.DataFrame:
        """
        Load preprocessed test data from CSV.
        
        Returns:
            DataFrame with preprocessed features and target
        """
        logger.info(f"Loading test data from {self.config.test_data_path}...")
        
        try:
            if not os.path.exists(self.config.test_data_path):
                raise FileNotFoundError(f"Test data not found: {self.config.test_data_path}")
            
            df = pd.read_csv(self.config.test_data_path)
            logger.info(f"✓ Test data loaded. Shape: {df.shape}")
            
            if self.config.target_column not in df.columns:
                raise ValueError(f"Target column '{self.config.target_column}' not in test data")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load test data: {str(e)}")
            raise CustomException(e, sys)

    def validate_schema(self, df: pd.DataFrame, schema_name: str) -> bool:
        """
        Validate DataFrame schema against schema.yaml.
        
        Args:
            df: DataFrame to validate
            schema_name: Name of the schema in schema.yaml
            
        Returns:
            True if schema is valid, False otherwise
        """
        logger.info(f"Validating schema against '{schema_name}'...")
        
        try:
            result = compare_schema_for_model_training(
                df=df,
                schema_name=schema_name,
                schema_yaml_filepath=self.config.schema_yaml_path,
                strict=self.config.strict_schema_validation
            )
            
            if result['match']:
                logger.info(f"✓ Schema validation passed for '{schema_name}'")
                return True
            else:
                logger.warning(f"⚠ Schema differences for '{schema_name}':")
                if result['missing_columns']:
                    logger.warning(f"  Missing columns: {len(result['missing_columns'])}")
                if result['extra_columns']:
                    logger.warning(f"  Extra columns: {len(result['extra_columns'])}")
                if result['dtype_mismatches']:
                    logger.warning(f"  Dtype mismatches: {len(result['dtype_mismatches'])}")
                return not self.config.strict_schema_validation
                
        except FileNotFoundError:
            logger.warning("Schema file not found - skipping validation")
            return True
        except ValueError as e:
            logger.warning(f"Schema not found in YAML - skipping: {str(e)}")
            return True
        except Exception as e:
            logger.error(f"Schema validation error: {str(e)}")
            if self.config.strict_schema_validation:
                raise CustomException(e, sys)
            return True

    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Separate features and target from DataFrame.
        
        Args:
            df: DataFrame with features and target
            
        Returns:
            Tuple of (X, y)
        """
        y = df[self.config.target_column]
        X = df.drop(columns=[self.config.target_column])
        
        # Keep only numeric columns (XGBoost requirement)
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        non_numeric_cols = [col for col in X.columns if col not in numeric_cols]
        
        if non_numeric_cols:
            logger.warning(f"Dropping {len(non_numeric_cols)} non-numeric columns")
            X = X[numeric_cols]
        
        return X, y

    def calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
        """
        Calculate comprehensive classification metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_prob: Prediction probabilities
            
        Returns:
            Dictionary of metrics
        """
        metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_true, y_prob)),
            "average_precision": float(average_precision_score(y_true, y_prob))
        }
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics["true_negatives"] = int(cm[0, 0])
        metrics["false_positives"] = int(cm[0, 1])
        metrics["false_negatives"] = int(cm[1, 0])
        metrics["true_positives"] = int(cm[1, 1])
        
        return metrics

    def save_confusion_matrix(self, y_true: pd.Series, y_pred: np.ndarray, 
                              filename: str = "confusion_matrix.png") -> str:
        """
        Save confusion matrix as a PNG plot.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=['Not Fraud', 'Fraud'],
                    yticklabels=['Not Fraud', 'Fraud'])
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix (Test Set)')
        
        filepath = os.path.join(self.config.model_save_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✓ Confusion matrix saved to: {filepath}")
        return filepath

    def save_metrics_json(self, metrics: Dict, filename: str = "metrics.json") -> str:
        """
        Save metrics to JSON file for DVC tracking.
        
        Args:
            metrics: Dictionary of metrics
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = os.path.join(self.config.model_save_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"✓ Metrics saved to: {filepath}")
        return filepath

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_test: pd.DataFrame, y_test: pd.Series) -> XGBClassifier:
        """
        Train XGBClassifier with MLflow tracking.
        
        Args:
            X_train, y_train: Training data
            X_test, y_test: Test data (for evaluation set during training)
            
        Returns:
            Trained XGBClassifier model
        """
        logger.info("=" * 60)
        logger.info("STARTING MODEL TRAINING")
        logger.info("=" * 60)
        
        try:
            # DagsHub MLflow tracking is already initialized at module level
            
            # Create or get experiment
            mlflow.set_experiment(self.config.experiment_name)
            
            # Enable autologging for XGBoost
            mlflow.xgboost.autolog(
                log_input_examples=True,
                log_model_signatures=True,
                log_models=True
            )
            
            logger.info(f"MLflow experiment: {self.config.experiment_name}")
            logger.info(f"Model parameters: {self.model_params}")
            
            with mlflow.start_run(run_name=self.config.run_name) as run:
                self.run_id = run.info.run_id
                logger.info(f"MLflow run ID: {self.run_id}")
                
                # Log additional parameters
                mlflow.log_param("train_samples", len(X_train))
                mlflow.log_param("test_samples", len(X_test))
                mlflow.log_param("n_features", X_train.shape[1])
                mlflow.log_param("fraud_rate_train", float(y_train.mean()))
                mlflow.log_param("fraud_rate_test", float(y_test.mean()))
                
                # Initialize and train model
                model = XGBClassifier(**self.model_params)
                
                logger.info(f"Training XGBClassifier on {len(X_train)} samples...")
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_train, y_train), (X_test, y_test)],
                    verbose=100
                )
                logger.info("✓ Model training completed")
                
                # === EVALUATION ON TRAIN SET ===
                logger.info("\n" + "=" * 40)
                logger.info("TRAIN SET EVALUATION")
                logger.info("=" * 40)
                
                y_pred_train = model.predict(X_train)
                y_prob_train = model.predict_proba(X_train)[:, 1]
                train_metrics = self.calculate_metrics(y_train, y_pred_train, y_prob_train)
                
                for name, value in train_metrics.items():
                    if isinstance(value, float):
                        logger.info(f"  {name}: {value:.4f}")
                        mlflow.log_metric(f"train_{name}", value)
                
                # === EVALUATION ON TEST SET ===
                logger.info("\n" + "=" * 40)
                logger.info("TEST SET EVALUATION")
                logger.info("=" * 40)
                
                y_pred_test = model.predict(X_test)
                y_prob_test = model.predict_proba(X_test)[:, 1]
                test_metrics = self.calculate_metrics(y_test, y_pred_test, y_prob_test)
                
                for name, value in test_metrics.items():
                    if isinstance(value, float):
                        logger.info(f"  {name}: {value:.4f}")
                        mlflow.log_metric(f"test_{name}", value)
                
                logger.info("\nClassification Report (Test Set):")
                logger.info("\n" + classification_report(y_test, y_pred_test))
                
                # Store all metrics
                self.metrics = {
                    "train": train_metrics,
                    "test": test_metrics
                }
                
                # Save confusion matrix
                cm_path = self.save_confusion_matrix(y_test, y_pred_test)
                mlflow.log_artifact(cm_path)
                
                # Save metrics JSON for DVC
                metrics_for_dvc = {
                    "train_roc_auc": train_metrics["roc_auc"],
                    "train_f1_score": train_metrics["f1_score"],
                    "train_precision": train_metrics["precision"],
                    "train_recall": train_metrics["recall"],
                    "test_roc_auc": test_metrics["roc_auc"],
                    "test_f1_score": test_metrics["f1_score"],
                    "test_precision": test_metrics["precision"],
                    "test_recall": test_metrics["recall"],
                    "test_accuracy": test_metrics["accuracy"],
                }
                self.save_metrics_json(metrics_for_dvc)
                
                self.model = model
                return model
                
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            raise CustomException(e, sys)

    def save_model(self, model: Optional[XGBClassifier] = None, 
                   model_name: str = "XGBClassifier") -> str:
        """
        Save trained model with version management.
        
        Args:
            model: Trained model (uses self.model if None)
            model_name: Base name for the model file
            
        Returns:
            Path to saved model file
        """
        logger.info("Saving trained model...")
        
        try:
            model_to_save = model or self.model
            if model_to_save is None:
                raise ValueError("No model to save. Train a model first.")
            
            # Version management - find next version number
            existing_models = [f for f in os.listdir(self.config.model_save_dir) 
                             if f.startswith(model_name) and f.endswith('.joblib') and '_v' in f]
            
            if existing_models:
                versions = []
                for fname in existing_models:
                    try:
                        version_str = fname.replace(model_name + "_v", "").replace(".joblib", "")
                        versions.append(int(version_str))
                    except ValueError:
                        continue
                next_version = max(versions) + 1 if versions else 1
            else:
                next_version = 1
            
            # Save versioned model
            model_filename = f"{model_name}_v{next_version}.joblib"
            model_path = os.path.join(self.config.model_save_dir, model_filename)
            joblib.dump(model_to_save, model_path)
            logger.info(f"✓ Model saved to: {model_path}")
            
            # Save 'latest' version for DVC tracking
            latest_path = os.path.join(self.config.model_save_dir, f"{model_name}_latest.joblib")
            joblib.dump(model_to_save, latest_path)
            logger.info(f"✓ Latest model: {latest_path}")
            
            # Save metadata
            import yaml
            metadata = {
                "model_name": model_name,
                "version": next_version,
                "run_id": self.run_id,
                "metrics": self.metrics,
                "params": self.model_params,
                "model_path": model_path
            }
            
            # Save ONNX model
            try:
                if hasattr(model_to_save, "n_features_in_"):
                    n_features = model_to_save.n_features_in_
                    onnx_filename = f"{model_name}_v{next_version}.onnx"
                    onnx_path = os.path.join(self.config.model_save_dir, onnx_filename)
                    convert_xgboost_to_onnx(model_to_save, onnx_path, n_features)
                    
                    # Save latest ONNX symlink
                    latest_onnx_path = os.path.join(self.config.model_save_dir, f"{model_name}_latest.onnx")
                    import shutil
                    shutil.copy2(onnx_path, latest_onnx_path)
                    logger.info(f"✓ Latest ONNX model: {latest_onnx_path}")
            except Exception as e:
                logger.warning(f"Failed to save ONNX model (non-critical): {e}")
            
            metadata_path = os.path.join(self.config.model_save_dir, f"{model_name}_v{next_version}_metadata.yaml")
            with open(metadata_path, 'w') as f:
                yaml.dump(metadata, f, default_flow_style=False)
            logger.info(f"✓ Metadata saved to: {metadata_path}")
            
            # Cleanup old artifacts (models, metadata, confusion matrices, metrics, onnx)
            # Keep only the latest version just saved
            self.cleanup_old_artifacts(model_name, next_version)
            
            return model_path
            
        except Exception as e:
            logger.error(f"Model save failed: {str(e)}")
            raise CustomException(e, sys)

    def cleanup_old_artifacts(self, model_name: str, current_version: int) -> None:
        """
        Clean up old model artifacts, keeping only the latest version.
        
        Since older models are pushed to S3 via DVC, we only keep the latest
        version locally to save disk space.
        
        Args:
            model_name: Base name for the model (e.g., "XGBClassifier")
            current_version: The version number of the model just saved (to keep)
        """
        logger.info(f"Cleaning up old artifacts (keeping only v{current_version})...")
        
        try:
            files_deleted = 0
            files_to_keep = {
                f"{model_name}_v{current_version}.joblib",
                f"{model_name}_v{current_version}_metadata.yaml",
                f"{model_name}_latest.joblib",
                f"{model_name}_v{current_version}.onnx",
                f"{model_name}_latest.onnx",
                "metrics.json",
                "confusion_matrix.png",
                ".gitkeep",
                ".gitignore"
            }
            
            for filename in os.listdir(self.config.model_save_dir):
                filepath = os.path.join(self.config.model_save_dir, filename)
                
                # Skip directories
                if os.path.isdir(filepath):
                    continue
                
                # Skip files we want to keep
                if filename in files_to_keep:
                    continue
                
                # Delete old versioned models (e.g., XGBClassifier_v1.joblib, XGBClassifier_v2.joblib)
                if filename.startswith(model_name) and '_v' in filename:
                    # Extract version number to check if it's an older version
                    try:
                        if filename.endswith('.joblib'):
                            version_str = filename.replace(model_name + "_v", "").replace(".joblib", "")
                            version = int(version_str)
                            if version < current_version:
                                os.remove(filepath)
                                logger.info(f"  Deleted old model: {filename}")
                                files_deleted += 1
                        elif filename.endswith('.onnx'):
                            version_str = filename.replace(model_name + "_v", "").replace(".onnx", "")
                            version = int(version_str)
                            if version < current_version:
                                os.remove(filepath)
                                logger.info(f"  Deleted old ONNX model: {filename}")
                                files_deleted += 1
                        elif filename.endswith('_metadata.yaml'):
                            # Extract version from metadata filename
                            version_str = filename.replace(model_name + "_v", "").replace("_metadata.yaml", "")
                            version = int(version_str)
                            if version < current_version:
                                os.remove(filepath)
                                logger.info(f"  Deleted old metadata: {filename}")
                                files_deleted += 1
                    except ValueError:
                        # Could not parse version, skip
                        continue
                
                # Delete old confusion matrix files (if any with different naming)
                elif filename.startswith("confusion_matrix") and filename.endswith(".png"):
                    if filename != "confusion_matrix.png":
                        os.remove(filepath)
                        logger.info(f"  Deleted old confusion matrix: {filename}")
                        files_deleted += 1
                
                # Delete old metrics files (if any with different naming)
                elif filename.startswith("metrics") and filename.endswith(".json"):
                    if filename != "metrics.json":
                        os.remove(filepath)
                        logger.info(f"  Deleted old metrics file: {filename}")
                        files_deleted += 1
            
            if files_deleted > 0:
                logger.info(f"✓ Cleaned up {files_deleted} old artifact(s)")
            else:
                logger.info("✓ No old artifacts to clean up")
                
        except Exception as e:
            # Don't fail the pipeline if cleanup fails, just log warning
            logger.warning(f"⚠ Cleanup failed (non-critical): {str(e)}")

    def run(self) -> Tuple[XGBClassifier, str]:
        """
        Execute the complete model training pipeline.
        
        Steps:
        1. Load Train_transformed.csv and Test_transformed.csv
        2. Validate schemas
        3. Train model on training data
        4. Evaluate on both train and test data
        5. Save model, metrics, and plots
        
        Returns:
            Tuple of (trained_model, model_save_path)
        """
        logger.info("=" * 60)
        logger.info("STARTING MODEL TRAINING PIPELINE")
        logger.info("=" * 60)
        
        try:
            # Step 1: Load training data
            logger.info("\nStep 1: Loading training data...")
            train_df = self.load_train_data()
            
            # Step 2: Load test data
            logger.info("\nStep 2: Loading test data...")
            test_df = self.load_test_data()
            
            # Step 3: Validate schemas
            logger.info("\nStep 3: Validating data schemas...")
            self.validate_schema(train_df, "preprocessed_train")
            self.validate_schema(test_df, "preprocessed_test")
            
            # Step 4: Prepare features
            logger.info("\nStep 4: Preparing features...")
            X_train, y_train = self.prepare_features(train_df)
            X_test, y_test = self.prepare_features(test_df)
            
            logger.info(f"Train set: {X_train.shape}, Fraud rate: {y_train.mean():.4f}")
            logger.info(f"Test set: {X_test.shape}, Fraud rate: {y_test.mean():.4f}")
            
            # Step 5: Train model
            logger.info("\nStep 5: Training model...")
            model = self.train(X_train, y_train, X_test, y_test)
            
            # Step 6: Save model locally
            logger.info("\nStep 6: Saving model locally...")
            model_path = self.save_model(model)
            
            # Step 7: Upload model to S3
            logger.info("\nStep 7: Uploading model to S3...")
            s3_result = S3ModelUploader.upload_latest_model(
                model_dir=self.config.model_save_dir,
                model_name="XGBClassifier",
                s3_uri=PredictionConfig.s3_model_uri,
                upload_metadata=True,
                upload_metrics=True
            )
            
            if s3_result['success']:
                logger.info(f"✓ Model uploaded to S3: {s3_result['s3_paths']}")
            else:
                logger.warning(f"⚠ S3 upload failed: {s3_result['error']}")
            
            logger.info("=" * 60)
            logger.info("MODEL TRAINING PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info(f"Model saved locally to: {model_path}")
            logger.info(f"Model uploaded to S3: {PredictionConfig.s3_model_uri}")
            logger.info(f"Metrics saved to: {self.config.model_save_dir}/metrics.json")
            logger.info(f"MLflow run ID: {self.run_id}")
            logger.info("=" * 60)
            
            return model, model_path
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"Model training pipeline failed: {str(e)}")
            raise CustomException(e, sys)


# ============================================================================
# MAIN ENTRY POINT (for DVC pipeline)
# ============================================================================

def main():
    """Main entry point for DVC pipeline."""
    import argparse
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Model Training Pipeline")
    parser.add_argument("--experiment-name", type=str, default="exp_1",
                        help="MLflow experiment name")
    parser.add_argument("--run-name", type=str, default="XGBClassifier_run",
                        help="MLflow run name")
    parser.add_argument("--strict-schema", action="store_true",
                        help="Enable strict schema validation")
    
    args = parser.parse_args()
    
    # Create config with CLI overrides
    config = ModelTrainingConfig(
        experiment_name=args.experiment_name,
        run_name=args.run_name,
        strict_schema_validation=args.strict_schema
    )
    
    # Run pipeline
    trainer = ModelTraining(config)
    model, model_path = trainer.run()
    
    logger.info(f"Training complete! Model saved to: {model_path}")


if __name__ == "__main__":
    main()
