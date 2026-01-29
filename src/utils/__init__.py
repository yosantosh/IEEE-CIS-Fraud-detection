
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
    def compare_schema(df: pd.DataFrame, schema_name: str, schema_yaml_filepath: str, strict: bool = False):
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



