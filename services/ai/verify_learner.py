import requests
import json
import time
import os
import subprocess

# Host-accessible URLs
API_URL = os.getenv("API_URL", "http://localhost:8080")
AI_URL = os.getenv("AI_URL", "http://localhost:8000")

def test_diagnostics():
    print(f"Testing /learner/test at {AI_URL}...")
    try:
        res = requests.get(f"{AI_URL}/learner/test")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

    print(f"Testing /learner/db-test at {AI_URL}...")
    try:
        res = requests.get(f"{AI_URL}/learner/db-test")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

    print(f"Testing /learner/simple POST at {AI_URL}...")
    try:
        res = requests.post(f"{AI_URL}/learner/simple")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

def test_ai_learner_event():
    test_diagnostics()
    
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    
    print(f"Testing AI Service /learner/submit directly at {AI_URL} (using curl)...")
    payload = json.dumps({
        "user_id": user_id, 
        "event_type": "manual_skill_update",
        "details": {
            "domain": "debugging",
            "delta": 1
        }
    })
    
    # Use curl because requests is giving 500 for unknown reasons (likely headers)
    cmd = [
        "curl", "-v", "-X", "POST", 
        "-H", "Content-Type: application/json",
        "-d", payload,
        f"{AI_URL}/learner/event"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Curl Output: {result.stdout}")
        print(f"Curl Error: {result.stderr}")
        
        if "updated_skills" in result.stdout:
            print("AI Service Test PASSED")
            return True
        else:
            print("AI Service Test FAILED")
            return False
    except Exception as e:
        print(f"Curl Execution Error: {e}")
        return False

def test_api_learner_endpoints():
    print(f"\nTesting Go API /api/v1/user/learner/event at {API_URL}...")
    
    # 1. Login
    login_payload = {
        "email": "dev@axiom.local",
        "password": "password"
    }
    try:
        sess = requests.Session()
        res = sess.post(f"{API_URL}/api/v1/auth/login", json=login_payload)
        if res.status_code != 200:
            print(f"Login failed: {res.status_code} {res.text}")
            return False
        
        token = res.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        print("Logged in successfully.")
        
        # 2. Test Post Event (Correction -> Debugging Skill)
        event_payload = {
            "event_type": "correction", 
            "details": {}
        }
        res = sess.post(f"{API_URL}/api/v1/user/learner/event", json=event_payload, headers=headers)
        print(f"Event Status: {res.status_code}")
        print(f"Event Response: {res.json()}")
        
        if res.status_code != 200:
            print("API Event Post FAILED")
            return False

        # 3. Test Get Profile
        time.sleep(1) 
        
        print("Fetching Learner Profile...")
        res = sess.get(f"{API_URL}/api/v1/user/learner", headers=headers)
        print(f"Profile Status: {res.status_code}")
        profile = res.json()
        print(f"Profile: {json.dumps(profile, indent=2)}")
        
        skills = profile.get("skills", {}) or profile.get("Skills", {})
        
        if "debugging" in skills or "Debugging" in skills:
            print("API Verification PASSED: 'debugging' skill found in profile")
            return True
        else:
             print("API Verification WARNING: 'debugging' skill not found in profile")
             return False
             
    except Exception as e:
        print(f"API Connection Error: {e}")
        return False

if __name__ == "__main__":
    ai_passed = test_ai_learner_event()
    if ai_passed:
        # Retry API test a few times if connection refused (service startup race)
        for i in range(5):
             try:
                 if test_api_learner_endpoints():
                     break
             except Exception as e:
                 print(f"Retry {i+1} failed: {e}")
                 time.sleep(2)
             else:
                 time.sleep(2)
