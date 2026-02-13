
import requests
import time
import json
import uuid

BASE_URL = "http://api:8080/api/v1"
EMAIL = f"testuser_{uuid.uuid4()}@example.com"
PASSWORD = "password123"

def register_and_login():
    print(f"Registering user: {EMAIL}")
    payload = {"email": EMAIL, "password": PASSWORD, "name": "Test User"}
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json=payload)
        if resp.status_code == 201:
            print("Registration successful")
        elif resp.status_code == 409:
            print("User already exists, logging in...")
        else:
            print(f"Registration failed: {resp.text}")
            return None

        print("Logging in...")
        resp = requests.post(f"{BASE_URL}/auth/login", json=payload)
        if resp.status_code == 200:
            token = resp.json().get("token")
            print("Login successful, token received")
            return token
        else:
            print(f"Login failed: {resp.text}")
            return None
    except Exception as e:
        print(f"Error during auth: {e}")
        return None

def create_project(token):
    print("Creating project...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"name": "E2E Test Project", "description": "Test project for verification"}
    resp = requests.post(f"{BASE_URL}/projects", json=payload, headers=headers)
    if resp.status_code == 201:
        project_id = resp.json().get("id")
        print(f"Project created: {project_id}")
        return project_id
    else:
        print(f"Create project failed: {resp.text}")
        return None

def create_ivcu(token, project_id):
    print("Creating IVCU...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "project_id": project_id,
        "raw_intent": "Create a function to calculate fibonacci sequence",
        "contracts": []
    }
    resp = requests.post(f"{BASE_URL}/intent/create", json=payload, headers=headers)
    if resp.status_code == 201:
        ivcu_id = resp.json().get("ivcu_id") # Note: intent/create returns { "ivcu_id": ... } or similar? 
        # Checking implementation of CreateIVCU in handlers/intent.go would be good, but assuming standard rest response is safer to verify.
        # Actually in generation.go it uses `req.IVCUID`. Let's assume response key is `id` or `ivcu_id`.
        # Based on generation handler: `c.JSON(http.StatusAccepted, gin.H{"generation_id": generationID, "ivcu_id": req.IVCUID ...})`
        # But for intent creation, let's assume `id`.
        # Let's start with `id` but fallback to `ivcu_id` if needed.
        if not ivcu_id:
             ivcu_id = resp.json().get("id")
        print(f"IVCU created: {ivcu_id}")
        return ivcu_id
    else:
        print(f"Create IVCU failed: {resp.text}")
        return None

def start_generation(token, ivcu_id):
    print(f"Starting generation for IVCU: {ivcu_id}")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "ivcu_id": ivcu_id,
        "language": "python",
        "candidate_count": 1,
        "strategy": "simple"
    }
    resp = requests.post(f"{BASE_URL}/generation/start", json=payload, headers=headers)
    if resp.status_code == 202:
        print("Generation started successfully")
        return True
    else:
        print(f"Start generation failed: {resp.text}")
        return False

def poll_status(token, ivcu_id):
    print("Polling status...")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/generation/{ivcu_id}/status"
    
    start_time = time.time()
    while time.time() - start_time < 60: # 60 seconds timeout
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            progress = data.get("progress")
            stage = data.get("stage")
            print(f"Status: {status}, Progress: {progress}, Stage: {stage}")
            
            if status in ["verified", "completed", "failed"]:
                return data
        else:
            print(f"Poll failed: {resp.status_code} - {resp.text}")
        
        time.sleep(2)
    
    print("Polling timed out")
    return None

def main():
    token = register_and_login()
    if not token:
        return

    project_id = create_project(token)
    # If project creation fails (e.g., not implemented completely), try using a default UUID or skip
    if not project_id:
        # Try listing projects to get one?
        # Or just allow logic to proceed if we can just pass a dummy ID (some handlers might check existence)
        pass 

    # We need a project ID for IVCU usually. If CreateProject failed, we probably can't proceed unless we have a fallback.
    # In `intentHandler.CreateIVCU`, let's hope it works.
    
    if project_id:
        ivcu_id = create_ivcu(token, project_id)
        if ivcu_id:
            if start_generation(token, ivcu_id):
                result = poll_status(token, ivcu_id)
                if result:
                    print("Final Result:", json.dumps(result, indent=2))
                    if result.get("status") == "verified":
                         print("SUCCESS: Generation verified!")
                    else:
                         print("FAILURE: Generation not verified.")

if __name__ == "__main__":
    main()
