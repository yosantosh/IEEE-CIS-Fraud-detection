import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

@patch("src.api.main.prediction_pipeline")
def test_predict_invalid_type(mock_pipeline):
    """Verifies that invalid data types trigger a 422 error."""
    mock_pipeline.model = MagicMock()
    
    # Garbage input: string for a float field
    bad_input = {"transactions": [{"TransactionID": 1, "TransactionAmt": "garbage"}]}
    
    response = client.post("/predict", json=bad_input)
    assert response.status_code == 422

@patch("src.api.main.prediction_pipeline")
def test_predict_smart_mapping(mock_pipeline):
    """Verifies that case-insensitive matching and missing cols return 200."""
    mock_pipeline.model = MagicMock()
    import pandas as pd
    mock_pipeline.predict.return_value = pd.DataFrame({
        'TransactionID': [123],
        'prediction_isFraud': [0]
    })
    
    # Smart input: lowercase keys, missing 90% of columns
    smart_input = {
        "transactions": [
            {
                "transactionid": 123,  # lowercase
                "productcd": "W",      # lowercase
                "transactionamt": 50.0 # lowercase
            }
        ]
    }
    
    response = client.post("/predict", json=smart_input)
    assert response.status_code == 200
    assert response.json()["predictions"][0]["TransactionID"] == 123
