import requests
import json

# Correct URL
url = "http://0.0.0.0:8000/predict"

# Payload with mixed case (should work now!)
payload = {
    "transactions": [
        {
            "transactionid": 12345,  # Lowercase
            "TRANSACTIONDT": 1000,   # Uppercase
            "transactionamt": 50.0,  # Lowercase
            "ProductCD": "C",        # Correct
            "card1": 1000,
            "card2": 150
            # Missing many fields, but 'extra=allow'/flexible dict should accept it
            # and pipeline will handle missing values (fill with nan/-999)
        }
    ]
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload, timeout=20)
    
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 200:
        print("\n✅ SUCCESS! API handled case-insensitive inputs correctly.")
    else:
        print("\n❌ FAILED. Check server logs.")

except Exception as e:
    print(f"\n❌ Prediction Request Failed: {e}")
