import requests
import concurrent.futures
import time
import json
import random

# CONFIGURATION
AKS_IP = "48.194.37.121"  # Replace with current External IP if it changes
URL = f"http://{AKS_IP}/batch_predict"  # Using batch_predict as it's the main endpoint
TOTAL_REQUESTS = 1000
CONCURRENT_THREADS = 20

# Dummy Data Payload (Single transaction in a batch)
def get_dummy_payload():
    return {
        "transactions": [
            {
                "TransactionID": 3000000 + random.randint(1, 10000),
                "TransactionDT": 100000,
                "TransactionAmt": 100.0,
                "ProductCD": "W",
                "card1": 10000,
                "card2": 111,
                "card3": 150,
                "card4": "visa",
                "card5": 226,
                "card6": "debit",
                "addr1": 300,
                "addr2": 87,
                "dist1": 15.0,
                "dist2": None,
                "P_emaildomain": "gmail.com",
                "R_emaildomain": None,
                # Add a few V columns to pass basic schema validation if needed
                "V1": 1.0, "V2": 1.0, "V3": 1.0,
                # Add ID columns
                "id_01": None, "id_12": "Found",
                "DeviceType": "mobile", "DeviceInfo": "SAMSUNG"
            }
        ]
    }

def send_request(request_id):
    try:
        start_time = time.time()
        payload = get_dummy_payload()
        
        # Determine if we should hit health or predict
        # Let's mix it up: 90% predict, 10% health
        if random.random() < 0.1:
            target_url = f"http://{AKS_IP}/health"
            response = requests.get(target_url, timeout=5)
        else:
            target_url = URL
            # The API expects a JSON with list of records. 
            # If the API expects a dataframe-like dict (columns as keys, lists as values)
            response = requests.post(target_url, json=payload, timeout=10)
            
        latency = time.time() - start_time
        return {
            "id": request_id,
            "status": response.status_code,
            "latency": latency,
            "success": 200 <= response.status_code < 300
        }
    except Exception as e:
        return {
            "id": request_id,
            "status": "ERROR",
            "latency": 0,
            "success": False,
            "error": str(e)
        }

def run_stress_test():
    print(f"🚀 Starting Stress Test on {URL}")
    print(f"Requests: {TOTAL_REQUESTS}, Threads: {CONCURRENT_THREADS}")
    
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        future_to_req = {executor.submit(send_request, i): i for i in range(TOTAL_REQUESTS)}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_req):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 50 == 0:
                print(f"Progress: {completed}/{TOTAL_REQUESTS} requests completed...")

    total_time = time.time() - start_time
    
    # Analysis
    success_count = sum(1 for r in results if r['success'])
    fail_count = TOTAL_REQUESTS - success_count
    avg_latency = sum(r['latency'] for r in results) / TOTAL_REQUESTS if TOTAL_REQUESTS > 0 else 0
    max_latency = max(r['latency'] for r in results) if results else 0
    
    print("\n" + "="*40)
    print("📊 STRESS TEST RESULTS")
    print("="*40)
    print(f"Total Time:     {total_time:.2f} seconds")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Successful:     {success_count} ✅")
    print(f"Failed:         {fail_count} ❌")
    print(f"Avg Latency:    {avg_latency:.3f} s")
    print(f"Max Latency:    {max_latency:.3f} s")
    print(f"RPS (Approx):   {TOTAL_REQUESTS / total_time:.2f} req/s")
    print("="*40)

if __name__ == "__main__":
    run_stress_test()
