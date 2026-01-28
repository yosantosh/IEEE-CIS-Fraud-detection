
## TO read .yamle file -------------------------------------------------------------------

import yaml
from box import ConfigBox # Optional: Makes dict access much cleaner
import pandas as pd
import os


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
    def write_schema_in_yaml(csv_filepath,schema_yaml_filepath):
        "write your incoming csv file schema in schema.yaml file"
            
        df = pd.read_csv(csv_filepath,nrows=2)
        schema_name = os.path.basename(csv_filepath).split('.')[0]
        new_schema = {
            schema_name: {col:str(dtype) for col,dtype in df.dtypes.items()}
        }

        content = {}
        if os.path.exists(schema_yaml_filepath):
            with open(schema_yaml_filepath, 'r') as file:
                content = yaml.safe_load(file) or {}
        
        content.update(new_schema)

        with open(schema_yaml_filepath,'w') as file:
            yaml.dump(
                content, file, 
                default_flow_style=False,
                sort_keys=False
            )
        print("Your csv schema has been appended in your schema.yaml file")




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



