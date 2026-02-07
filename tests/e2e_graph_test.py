import requests
import uuid
import time
import sys

AI_SERVICE_URL = "http://localhost:8000"
API_URL = "http://localhost:8080"

def test_e2e_flow():
    print(f"Testing E2E Flow: AI Service @ {AI_SERVICE_URL}, API @ {API_URL}...")
    
    # 1. Create a Unique Intent
    unique_id = str(uuid.uuid4())[:8]
    intent_text = f"Create a secure payment processor for transaction {unique_id}"
    print(f"\n[Step 1] Sending Intent: '{intent_text}'")
    
    try:
        response = requests.post(f"{AI_SERVICE_URL}/parse-intent", json={"intent": intent_text})
        response.raise_for_status()
        data = response.json()
        sdo_id = data['sdo_id']
        print(f"✅ Success: SDO Created with ID: {sdo_id}")
        
    except Exception as e:
        print(f"❌ Failed to create intent: {e}")
        if 'response' in locals():
            print(f"Server Response: {response.text}")
        sys.exit(1)

    # 2. Verify in Graph API (Simulating Frontend Fetch)
    print(f"\n[Step 2] Fetching Graph API to verify existence...")
    
    # Allow small consistency window if any (though DB is immediate usually)
    time.sleep(1)
    
    try:
        response = requests.get(f"{API_URL}/api/v1/graph")
        response.raise_for_status()
        graph_data = response.json()
        
        nodes = graph_data.get('nodes', [])
        found_node = next((n for n in nodes if n['id'] == sdo_id), None)
        
        if found_node:
            print(f"✅ Success: Node found in Graph API!")
            print(f"   Label: {found_node['label']}")
            print(f"   Status: {found_node['status']}")
            print(f"   Confidence: {found_node['confidence']}")
        else:
            print(f"❌ Failure: SDO {sdo_id} NOT found in Graph API.")
            print(f"   Total Nodes returned: {len(nodes)}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Failed to fetch graph: {e}")
        sys.exit(1)

    print("\n✅✅ E2E VALIDATION PASSED: Data flows from Intent -> DB -> API -> Frontend Graph Structure")

if __name__ == "__main__":
    test_e2e_flow()
