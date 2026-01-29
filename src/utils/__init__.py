
## TO read .yamle file -------------------------------------------------------------------

import yaml
from box import ConfigBox # Optional: Makes dict access much cleaner
import pandas as pd
import os
import numpy as np


class Read_write_yaml_schema:

    @staticmethod
    def read_yaml(path_to_yaml: str):
        "Reads a yaml file and returns a ConfigBox for easy access."
        with open(path_to_yaml) as yaml_file:
            content = yaml.safe_load(yaml_file)
            # Using ConfigBox allows you to use config.key instead of config['key']
            return ConfigBox(content)

        # # Usage in your script
        # config = read_yaml("params.yaml")

        # # Standard way
        # n_estimators = config['model_params']['XGBClassifier']['n_estimators']

        # # ConfigBox way (much cleaner for MLOps)
        # test_size = config.data_ingestion.test_size
        # max_depth = config.model_params.RandomForest.max_depth

        #-------------------------------------------------------
    @staticmethod
    def write_schema_in_yaml(csv_filepath, schema_yaml_filepath):
        "write your incoming csv file schema in schema.yaml file"
            
        df = pd.read_csv(csv_filepath, nrows=2)
        schema_name = os.path.basename(csv_filepath).split('.')[0]
        new_schema = {
            schema_name: {col: str(dtype) for col, dtype in df.dtypes.items()}
        }

        content = {}
        if os.path.exists(schema_yaml_filepath):
            with open(schema_yaml_filepath, 'r') as file:
                content = yaml.safe_load(file) or {}
        
        content.update(new_schema)

        with open(schema_yaml_filepath, 'w') as file:
            yaml.dump(
                content, file, 
                default_flow_style=False,
                sort_keys=False
            )
        print("Your csv schema has been appended in your schema.yaml file")

    @staticmethod
    def save_dataframe_schema(df: pd.DataFrame, schema_name: str, schema_yaml_filepath: str):
        """
        Save DataFrame schema directly to schema.yaml file (appends to existing schemas).
        
        Args:
            df: DataFrame whose schema to save
            schema_name: Name/key for this schema in the YAML file (e.g., 'raw_data', 'preprocessed_train')
            schema_yaml_filepath: Path to schema.yaml file
        """
        new_schema = {
            schema_name: {col: str(dtype) for col, dtype in df.dtypes.items()}
        }

        content = {}
        if os.path.exists(schema_yaml_filepath):
            with open(schema_yaml_filepath, 'r') as file:
                content = yaml.safe_load(file) or {}
        
        content.update(new_schema)

        with open(schema_yaml_filepath, 'w') as file:
            yaml.dump(
                content, file, 
                default_flow_style=False,
                sort_keys=False
            )
        print(f"Schema '{schema_name}' has been saved/updated in {schema_yaml_filepath}")

    @staticmethod
    def compare_schema(df: pd.DataFrame, schema_name: str, schema_yaml_filepath: str, strict: bool = True):
        """
        Compare DataFrame schema against schema stored in schema.yaml.
        
        Args:
            df: DataFrame to compare
            schema_name: Name/key of schema in YAML file to compare against
            schema_yaml_filepath: Path to schema.yaml file
            strict: If True, raises exception on mismatch. If False, just logs warnings.
            
        Returns:
            dict: Comparison result with keys:
                - 'match': bool - True if schemas match
                - 'missing_columns': list - Columns in schema.yaml but not in df
                - 'extra_columns': list - Columns in df but not in schema.yaml  
                - 'dtype_mismatches': dict - Columns with different dtypes {col: (expected, actual)}
                
        Raises:
            ValueError: If schema_name not found in schema.yaml
            SchemaValidationError: If strict=True and schemas don't match
        """
        # Read existing schema
        if not os.path.exists(schema_yaml_filepath):
            raise FileNotFoundError(f"Schema file not found: {schema_yaml_filepath}")
        
        with open(schema_yaml_filepath, 'r') as file:
            all_schemas = yaml.safe_load(file) or {}
        
        if schema_name not in all_schemas:
            raise ValueError(f"Schema '{schema_name}' not found in {schema_yaml_filepath}. "
                           f"Available schemas: {list(all_schemas.keys())}")
        
        expected_schema = all_schemas[schema_name]
        actual_schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Compare columns
        expected_cols = set(expected_schema.keys())
        actual_cols = set(actual_schema.keys())
        
        missing_columns = list(expected_cols - actual_cols)
        extra_columns = list(actual_cols - expected_cols)
        
        # Compare dtypes for common columns
        common_cols = expected_cols & actual_cols
        dtype_mismatches = {}
        for col in common_cols:
            expected_dtype = expected_schema[col]
            actual_dtype = actual_schema[col]
            # Normalize dtype strings for comparison
            if not _dtypes_compatible(expected_dtype, actual_dtype):
                dtype_mismatches[col] = (expected_dtype, actual_dtype)
        
        result = {
            'match': len(missing_columns) == 0 and len(extra_columns) == 0 and len(dtype_mismatches) == 0,
            'missing_columns': missing_columns,
            'extra_columns': extra_columns,
            'dtype_mismatches': dtype_mismatches
        }
        
        # Log results
        if result['match']:
            print(f"✓ Schema validation passed for '{schema_name}'")
        else:
            print(f"⚠ Schema validation WARNING for '{schema_name}':")
            if missing_columns:
                print(f"  Missing columns ({len(missing_columns)}): {missing_columns[:10]}{'...' if len(missing_columns) > 10 else ''}")
            if extra_columns:
                print(f"  Extra columns ({len(extra_columns)}): {extra_columns[:10]}{'...' if len(extra_columns) > 10 else ''}")
            if dtype_mismatches:
                print(f"  Dtype mismatches ({len(dtype_mismatches)}):")
                for col, (exp, act) in list(dtype_mismatches.items())[:5]:
                    print(f"    - {col}: expected {exp}, got {act}")
                if len(dtype_mismatches) > 5:
                    print(f"    ... and {len(dtype_mismatches) - 5} more")
            
            if strict:
                raise SchemaValidationError(
                    f"Schema validation failed for '{schema_name}'. "
                    f"Missing: {len(missing_columns)}, Extra: {len(extra_columns)}, "
                    f"Dtype mismatches: {len(dtype_mismatches)}"
                )
        
        return result


def _dtypes_compatible(expected: str, actual: str) -> bool:
    """
    Check if two dtype strings are compatible.
    Handles cases like 'int64' vs 'int32', 'float64' vs 'float32', etc.
    """
    # Exact match
    if expected == actual:
        return True
    
    # Normalize dtypes
    expected_normalized = expected.lower().replace('numpy.', '').replace('np.', '')
    actual_normalized = actual.lower().replace('numpy.', '').replace('np.', '')
    
    # Same base type (e.g., int64 and int32 are both int)
    int_types = {'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64'}
    float_types = {'float16', 'float32', 'float64'}
    object_types = {'object', 'str', 'string'}
    
    if expected_normalized in int_types and actual_normalized in int_types:
        return True
    if expected_normalized in float_types and actual_normalized in float_types:
        return True
    if expected_normalized in object_types and actual_normalized in object_types:
        return True
    
    return False


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails in strict mode."""
    pass


# ============================================================================
# CONSTANT CODE FOR SCHEMA COMPARISON - USE IN MODEL_TRAINING PIPELINE
# ============================================================================
# Copy this function to your model_training.py file for standalone schema validation

def compare_schema_for_model_training(df: pd.DataFrame, schema_name: str, schema_yaml_filepath: str, strict: bool = True):
    """
    CONSTANT CODE: Compare DataFrame schema against schema stored in schema.yaml.
    
    This is a standalone function you can copy to your model_training pipeline.
    
    Args:
        df: DataFrame to compare (e.g., X_train, X_test)
        schema_name: Name/key of schema in YAML file to compare against
                     (e.g., 'preprocessed_train', 'preprocessed_test')
        schema_yaml_filepath: Path to schema.yaml file (e.g., 'src/constants/schema.yaml')
        strict: If True, raises exception on mismatch. If False, just logs warnings.
        
    Returns:
        dict: Comparison result with keys:
            - 'match': bool - True if schemas match
            - 'missing_columns': list - Columns in schema.yaml but not in df
            - 'extra_columns': list - Columns in df but not in schema.yaml  
            - 'dtype_mismatches': dict - Columns with different dtypes
            
    Usage in model_training.py:
        # After loading preprocessed data
        X_train = pd.read_csv('artifacts/data/transformed/Train_transformed.csv')
        
        result = compare_schema_for_model_training(
            df=X_train,
            schema_name='preprocessed_train',
            schema_yaml_filepath='src/constants/schema.yaml',
            strict=True  # Will raise exception if schema doesn't match
        )
        
        if result['match']:
            logger.info("Schema validation passed, proceeding with training...")
    """
    import yaml
    
    if not os.path.exists(schema_yaml_filepath):
        raise FileNotFoundError(f"Schema file not found: {schema_yaml_filepath}")
    
    with open(schema_yaml_filepath, 'r') as file:
        all_schemas = yaml.safe_load(file) or {}
    
    if schema_name not in all_schemas:
        raise ValueError(f"Schema '{schema_name}' not found in {schema_yaml_filepath}. "
                        f"Available schemas: {list(all_schemas.keys())}")
    
    expected_schema = all_schemas[schema_name]
    actual_schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
    
    expected_cols = set(expected_schema.keys())
    actual_cols = set(actual_schema.keys())
    
    missing_columns = list(expected_cols - actual_cols)
    extra_columns = list(actual_cols - expected_cols)
    
    # Compare dtypes
    common_cols = expected_cols & actual_cols
    dtype_mismatches = {}
    
    # Helper for dtype comparison
    def dtypes_compatible(exp, act):
        if exp == act:
            return True
        exp_norm = exp.lower().replace('numpy.', '').replace('np.', '')
        act_norm = act.lower().replace('numpy.', '').replace('np.', '')
        int_types = {'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64'}
        float_types = {'float16', 'float32', 'float64'}
        object_types = {'object', 'str', 'string'}
        if exp_norm in int_types and act_norm in int_types:
            return True
        if exp_norm in float_types and act_norm in float_types:
            return True
        if exp_norm in object_types and act_norm in object_types:
            return True
        return False
    
    for col in common_cols:
        expected_dtype = expected_schema[col]
        actual_dtype = actual_schema[col]
        if not dtypes_compatible(expected_dtype, actual_dtype):
            dtype_mismatches[col] = (expected_dtype, actual_dtype)
    
    result = {
        'match': len(missing_columns) == 0 and len(extra_columns) == 0 and len(dtype_mismatches) == 0,
        'missing_columns': missing_columns,
        'extra_columns': extra_columns,
        'dtype_mismatches': dtype_mismatches
    }
    
    if result['match']:
        print(f"✓ Schema validation passed for '{schema_name}'")
    else:
        print(f"⚠ Schema validation {'FAILED' if strict else 'WARNING'} for '{schema_name}':")
        if missing_columns:
            print(f"  Missing columns ({len(missing_columns)}): {missing_columns[:10]}")
        if extra_columns:
            print(f"  Extra columns ({len(extra_columns)}): {extra_columns[:10]}")
        if dtype_mismatches:
            print(f"  Dtype mismatches ({len(dtype_mismatches)}): {dict(list(dtype_mismatches.items())[:5])}")
        
        if strict:
            raise ValueError(
                f"Schema validation failed for '{schema_name}'. "
                f"Missing: {len(missing_columns)}, Extra: {len(extra_columns)}, "
                f"Dtype mismatches: {len(dtype_mismatches)}"
            )
    
    return result



# ============================================================================
# S3 MODEL UPLOADER - CUSTOM S3 UPLOAD FOR MODELS
# ============================================================================

class S3ModelUploader:
    """
    Custom S3 uploader for model artifacts.
    
    This replaces DVC tracking for models, allowing direct upload to S3
    with version tracking based on model filename (v1, v2, v3, etc.).
    
    Credentials are read from environment variables:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_DEFAULT_REGION (optional, defaults to 'us-east-1')
    """
    
    @staticmethod
    def upload_latest_model(
        model_dir: str = "models",
        model_name: str = "XGBClassifier",
        s3_uri: str = "s3://mlops-capstone-project-final/models/",
        upload_metadata: bool = True,
        upload_metrics: bool = True
    ) -> dict:
        """
        Upload the latest versioned model and its artifacts to S3.
        
        Args:
            model_dir: Local directory containing models (default: 'models')
            model_name: Base name of the model (default: 'XGBClassifier')
            s3_uri: S3 URI for model storage (default: 's3://mlops-capstone-project-final/models/')
            upload_metadata: Whether to upload metadata YAML file (default: True)
            upload_metrics: Whether to upload metrics.json (default: True)
            
        Returns:
            dict: Upload result with keys:
                - 'success': bool
                - 'uploaded_files': list of uploaded file paths
                - 's3_paths': list of S3 URIs for uploaded files
                - 'version': version number of uploaded model
                - 'error': error message if failed
                
        Raises:
            ValueError: If no versioned models found
            Exception: If S3 upload fails
        """
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        result = {
            'success': False,
            'uploaded_files': [],
            's3_paths': [],
            'version': None,
            'error': None
        }
        
        try:
            # Parse S3 URI
            if not s3_uri.startswith('s3://'):
                raise ValueError(f"Invalid S3 URI: {s3_uri}. Must start with 's3://'")
            
            # Remove 's3://' and split into bucket and prefix
            s3_path = s3_uri[5:]  # Remove 's3://'
            if '/' in s3_path:
                bucket_name = s3_path.split('/')[0]
                s3_prefix = '/'.join(s3_path.split('/')[1:])
                if not s3_prefix.endswith('/'):
                    s3_prefix += '/'
            else:
                bucket_name = s3_path
                s3_prefix = ''
            
            print(f"S3 Bucket: {bucket_name}")
            print(f"S3 Prefix: {s3_prefix}")
            
            # Find latest version
            existing_models = [f for f in os.listdir(model_dir) 
                             if f.startswith(model_name) and f.endswith('.joblib') 
                             and '_v' in f and '_latest' not in f]
            
            if not existing_models:
                raise ValueError(f"No versioned models found in {model_dir}")
            
            versions = []
            for fname in existing_models:
                try:
                    version_str = fname.replace(model_name + "_v", "").replace(".joblib", "")
                    versions.append(int(version_str))
                except ValueError:
                    continue
            
            if not versions:
                raise ValueError(f"Could not parse version from model filenames")
            
            latest_version = max(versions)
            result['version'] = latest_version
            print(f"Latest model version: v{latest_version}")
            
            # Initialize S3 client (credentials from environment variables)
            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            
            # Files to upload
            files_to_upload = []
            
            # Latest versioned model
            model_filename = f"{model_name}_v{latest_version}.joblib"
            model_path = os.path.join(model_dir, model_filename)
            if os.path.exists(model_path):
                files_to_upload.append((model_path, model_filename))
            
            # Latest symlink model
            latest_filename = f"{model_name}_latest.joblib"
            latest_path = os.path.join(model_dir, latest_filename)
            if os.path.exists(latest_path):
                files_to_upload.append((latest_path, latest_filename))
            
            # Metadata YAML
            if upload_metadata:
                metadata_filename = f"{model_name}_v{latest_version}_metadata.yaml"
                metadata_path = os.path.join(model_dir, metadata_filename)
                if os.path.exists(metadata_path):
                    files_to_upload.append((metadata_path, metadata_filename))
            
            # Metrics JSON
            if upload_metrics:
                metrics_path = os.path.join(model_dir, "metrics.json")
                if os.path.exists(metrics_path):
                    files_to_upload.append((metrics_path, "metrics.json"))
                
                # Confusion matrix
                cm_path = os.path.join(model_dir, "confusion_matrix.png")
                if os.path.exists(cm_path):
                    files_to_upload.append((cm_path, "confusion_matrix.png"))
            
            # Upload each file
            for local_path, filename in files_to_upload:
                s3_key = f"{s3_prefix}{filename}"
                print(f"Uploading {filename} to s3://{bucket_name}/{s3_key}...")
                
                s3_client.upload_file(local_path, bucket_name, s3_key)
                
                result['uploaded_files'].append(local_path)
                result['s3_paths'].append(f"s3://{bucket_name}/{s3_key}")
                print(f"  ✓ Uploaded: {filename}")
            
            result['success'] = True
            print(f"\n✓ Successfully uploaded {len(files_to_upload)} file(s) to S3")
            
        except NoCredentialsError:
            result['error'] = "AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
            print(f"✗ Error: {result['error']}")
        except ClientError as e:
            result['error'] = f"S3 client error: {str(e)}"
            print(f"✗ Error: {result['error']}")
        except Exception as e:
            result['error'] = str(e)
            print(f"✗ Error: {result['error']}")
        
        return result

    @staticmethod
    def download_model_from_s3(
        s3_uri: str,
        model_name: str = "XGBClassifier",
        version: str = "latest",
        local_dir: str = "models"
    ) -> str:
        """
        Download a model from S3.
        
        Args:
            s3_uri: Base S3 URI for models (e.g., 's3://mlops-capstone-project-final/models/')
            model_name: Base name of the model (default: 'XGBClassifier')
            version: Version to download ('latest' or 'v1', 'v2', etc.)
            local_dir: Local directory to save the model (default: 'models')
            
        Returns:
            str: Local path to downloaded model
        """
        import boto3
        
        # Parse S3 URI
        s3_path = s3_uri[5:]  # Remove 's3://'
        if '/' in s3_path:
            bucket_name = s3_path.split('/')[0]
            s3_prefix = '/'.join(s3_path.split('/')[1:])
            if not s3_prefix.endswith('/'):
                s3_prefix += '/'
        else:
            bucket_name = s3_path
            s3_prefix = ''
        
        # Determine filename
        if version == "latest":
            filename = f"{model_name}_latest.joblib"
        else:
            # version can be 'v1', 'v2' or just '1', '2'
            v = version.replace('v', '')
            filename = f"{model_name}_v{v}.joblib"
        
        s3_key = f"{s3_prefix}{filename}"
        local_path = os.path.join(local_dir, filename)
        
        # Create local directory if needed
        os.makedirs(local_dir, exist_ok=True)
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
        
        print(f"Downloading s3://{bucket_name}/{s3_key} to {local_path}...")
        s3_client.download_file(bucket_name, s3_key, local_path)
        print(f"✓ Downloaded: {local_path}")
        
        return local_path


def reduce_memory(df, verbose=True):
    start_memory = df.memory_usage().sum() / 1024**2
    for col in df.columns:
        col_type = df[col].dtype
        if col_type != object:
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                else:
                    df[col] = df[col].astype(np.int32)
            else:
                # Skip float16 due to compatibility issues, use float32 as minimum
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)
    end_mem = df.memory_usage().sum() / 1024**2
    if verbose:
        print(f'Memory usage: {start_memory:.2f} MB -> {end_mem:.2f} MB ({100 * (start_memory - end_mem) / start_memory:.1f}% reduction)')
    return df



