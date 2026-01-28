
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



