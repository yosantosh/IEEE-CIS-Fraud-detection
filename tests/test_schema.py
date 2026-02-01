
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_predict_invalid_schema():
    # Sending string instead of float for Amount
    bad_input = {"transactions": [{"TransactionID": 1, "TransactionAmt": "invalid_amount"}]}
    
    response = client.post("/predict", json=bad_input)
    assert response.status_code == 422 # Unprocessable Entity
