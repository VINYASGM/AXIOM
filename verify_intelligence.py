
import asyncio
import time
import requests
import json

API_URL = "http://localhost:8000/parse-intent"

async def test_intelligence_loop():
    print("🧠 Testing AXIOM Intelligence Loop...")
    
    intent = "Create a python function to calculate fibonacci sequence using recursion."
    
    # 1. First Run - Should trigger generation (and cache miss)
    print(f"\n[1] Intent: {intent}")
    start_t = time.time()
    
    payload = {"intent": intent, "project_id": "test_proj", "user_id": "test_user"}
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        duration = time.time() - start_t
        print(f"✅ First Run Completed in {duration:.2f}s")
        print(f"   SDO ID: {data['sdo_id']}")
        
        # Verify structure
        status = data.get("status")
        if status != "submitting": # Submitting -> Processing in background
             print(f"   Status: {status}")

    except Exception as e:
        print(f"❌ First Run Failed: {e}")
        return

    # Wait for background processing to complete and populate cache
    print("⏳ Waiting for background processing...")
    await asyncio.sleep(8) # Increased wait time 
    
    # 2. Second Run - Should trigger Cache Hit
    print(f"\n[2] Re-running same intent (Testing Cache)...")
    start_t_2 = time.time()
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data_2 = response.json()
        
        duration_2 = time.time() - start_t_2
        print(f"✅ Second Run Completed in {duration_2:.2f}s")
        
    except Exception as e:
        print(f"❌ Second Run Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_intelligence_loop())
