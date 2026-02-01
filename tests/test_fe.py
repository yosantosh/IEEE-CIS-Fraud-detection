
import pandas as pd
import pytest
from src.components.data_FE_transformation import Data_FE_Transformation

def test_email_feature_logic():
    # Setup Data
    df = pd.DataFrame({
        "P_emaildomain": ["gmail.com", "yahoo.co.uk", None],
        "R_emaildomain": ["hotmail.com", "gmail.com", "unknown.net"],
        "TransactionDT": [86400, 86500, 90000] # Dummy DT
    })
    
    transformer = Data_FE_Transformation()
    
    # Run creation
    df_result = transformer.create_email_features(df)
    
    # Assert specific logic we relied on
    # 1. Vendor mapping
    assert df_result.iloc[0]['P_email_vendor'] == 'google'
    # 2. Null handling
    assert df_result.iloc[2]['P_emaildomain'] == 'missing'
    # 3. Domain Interaction
    assert df_result.iloc[0]['email_domain_match'] == 0 # gmail != hotmail
