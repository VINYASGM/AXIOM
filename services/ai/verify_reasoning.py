import requests
import json
import uuid
import time

# Use service name for internal docker communication
API_URL = "http://api:8080"
AI_URL = "http://localhost:8000"

def main():
    print("=== Reasoning Trace Verification ===", flush=True)
    
    # 1. Register + Login
    email = f"verifier_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    print(f"1. Registering {email}...", flush=True)
    
    reg = requests.post(f"{API_URL}/api/v1/auth/register", json={
        "email": email, "password": password, "name": "Verifier"
    })
    if reg.status_code not in [200, 201]:
        print(f"   FAIL: {reg.status_code} {reg.text}", flush=True)
        return
    
    auth = requests.post(f"{API_URL}/api/v1/auth/login", json={
        "email": email, "password": password
    })
    token = auth.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   OK: Logged in", flush=True)
    
    # 2. Create Project
    print("2. Creating project...", flush=True)
    proj = requests.post(f"{API_URL}/api/v1/projects", headers=headers, json={
        "name": "Trace Verify", "description": "test"
    })
    project_id = proj.json()["id"]
    print(f"   OK: {project_id}", flush=True)
    
    # 3. Parse Intent (creates SDO)
    print("3. Parsing intent...", flush=True)
    parse = requests.post(f"{API_URL}/api/v1/intent/parse", headers=headers, json={
        "raw_intent": "Create a hello world python function",
        "project_context": ""
    })
    if parse.status_code != 200:
        print(f"   FAIL: {parse.status_code} {parse.text}", flush=True)
        return
    
    parse_data = parse.json()
    sdo_id = parse_data.get("sdo_id", "")
    print(f"   OK: SDO ID = {sdo_id}", flush=True)
    
    # 4. Create IVCU (with SDO ID)
    print("4. Creating IVCU with SDO ID...", flush=True)
    ivcu = requests.post(f"{API_URL}/api/v1/intent/create", headers=headers, json={
        "project_id": project_id,
        "raw_intent": "Create a hello world python function",
        "contracts": [],
        "sdo_id": sdo_id
    })
    ivcu_id = ivcu.json()["ivcu_id"]
    print(f"   OK: IVCU ID = {ivcu_id}", flush=True)
    
    # 5. Start Generation
    print("5. Starting generation...", flush=True)
    gen = requests.post(f"{API_URL}/api/v1/generation/start", headers=headers, json={
        "ivcu_id": ivcu_id, "language": "python", "model_tier": "fast"
    })
    print(f"   Response: {gen.status_code}", flush=True)
    
    # 6. Poll for completion
    print("6. Polling for completion...", flush=True)
    for i in range(60):
        time.sleep(3)
        status_resp = requests.get(f"{API_URL}/api/v1/generation/{ivcu_id}/status", headers=headers)
        status = status_resp.json().get("status", "unknown")
        stage = status_resp.json().get("stage", "")
        print(f"   [{i+1}] Status: {status} Stage: {stage}", flush=True)
        if status in ["verified", "failed", "completed"]:
            break
    
    # 7. Verify SDO trace directly from AI service
    print(f"7. Fetching SDO {sdo_id} from AI service...", flush=True)
    if sdo_id:
        sdo_resp = requests.get(f"{AI_URL}/sdo/{sdo_id}")
        if sdo_resp.status_code == 200:
            sdo = sdo_resp.json()
            history = sdo.get("history", [])
            print(f"   OK: {len(history)} history steps", flush=True)
            with open("/app/trace_sdo.json", "w") as f:
                json.dump({"sdo_history": history, "sdo_id": sdo_id}, f, indent=2)
            print("   Written to /app/trace_sdo.json", flush=True)
        else:
            print(f"   FAIL: {sdo_resp.status_code}", flush=True)
    else:
        print("   SKIP: No SDO ID", flush=True)
    
    # 8. Test the API reasoning endpoint
    print(f"8. Fetching reasoning trace from API /reasoning/{ivcu_id}...", flush=True)
    trace_resp = requests.get(f"{API_URL}/api/v1/reasoning/{ivcu_id}", headers=headers)
    print(f"   Status: {trace_resp.status_code}", flush=True)
    with open("/app/trace_api.json", "w") as f:
        f.write(trace_resp.text)
    print("   Written to /app/trace_api.json", flush=True)
    
    print("\n=== DONE ===", flush=True)

if __name__ == "__main__":
    main()
