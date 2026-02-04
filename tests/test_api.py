
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pandas as pd
from src.api.main import app

# Create a test client
client = TestClient(app)

def test_health_check_no_model():
    """Test health check when model is not loaded."""
    # Mock the prediction pipeline to be None (simulate startup failure or before load)
    with patch('src.api.main.prediction_pipeline', None):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is False

def test_health_check_with_model():
    """Test health check when model is loaded."""
    # Mock the prediction pipeline and its model
    mock_pipeline = MagicMock()
    mock_pipeline.model = "loaded"
    
    with patch('src.api.main.prediction_pipeline', mock_pipeline):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True

def test_predict_batch_success():
    """Test batch prediction with mocked pipeline."""
    # Mock data
    mock_input = {
        "transactions": [
            {"TransactionID": 1001, "TransactionAmt": 50.0},
            {"TransactionID": 1002, "TransactionAmt": 100.0}
        ]
    }
    
    # Mock result DataFrame
    mock_result_df = pd.DataFrame({
        "TransactionID": [1001, 1002],
        "prediction_isFraud": [0, 1],
        "fraud_probability": [0.1, 0.9]  # Added for new logic
    })
    
    # Create mock pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.model = "loaded"
    mock_pipeline.predict_proba.return_value = mock_result_df  # Changed from predict to predict_proba
    
    with patch('src.api.main.prediction_pipeline', mock_pipeline):
        response = client.post("/predict", json=mock_input)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["predictions"]) == 2
        assert data["predictions"][0]["TransactionID"] == 1001
        assert data["predictions"][0]["isFraud"] == 0
        assert data["predictions"][1]["TransactionID"] == 1002
        assert data["predictions"][1]["isFraud"] == 1
        assert data["fraud_count"] == 1
        assert data["fraud_rate"] == 50.0

def test_predict_no_model_error():
    """Test prediction fails when model is not loaded."""
    with patch('src.api.main.prediction_pipeline', None):
        response = client.post("/predict", json={"transactions": []})
        assert response.status_code == 503
