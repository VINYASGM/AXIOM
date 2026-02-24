import requests
import json
import time

API_URL = "http://localhost:8080"
AI_URL = "http://localhost:8000"

def test_ai_learner_event():
    print("Testing AI Service /learner/event directly...")
    payload = {
        "user_id": "test-user-123", # Mock user ID for direct AI service test
        "event_type": "manual_skill_update",
        "details": {
            "domain": "debugging",
            "delta": 1
        }
    }
    try:
        res = requests.post(f"{AI_URL}/learner/event", json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        if res.status_code == 200:
            print("AI Service Test PASSED")
            return True
        else:
            print("AI Service Test FAILED")
            return False
    except Exception as e:
        print(f"AI Service Connection Error: {e}")
        return False

def test_api_learner_endpoints():
    print("\nTesting Go API /api/v1/user/learner/event...")
    
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
        # We expect this to call AI service, get updated skill, and update local DB
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
        # Wait a moment for async propagation if any (though Go handler updates locally immediately after optimization)
        time.sleep(1) 
        
        print("Fetching Learner Profile...")
        res = sess.get(f"{API_URL}/api/v1/user/learner", headers=headers)
        print(f"Profile Status: {res.status_code}")
        profile = res.json()
        print(f"Profile: {json.dumps(profile, indent=2)}")
        
        skills = profile.get("Skills", {}) or profile.get("skills", {}) # Handle capitalization if any
        
        if "debugging" in skills or "Debugging" in skills:
            print("API Verification PASSED: 'debugging' skill found in profile")
            return True
        else:
             print("API Verification WARNING: 'debugging' skill not found in profile")
             # It might be that the initial skill was 0 and delta was 1, so it should be > 0.
             return False
             
    except Exception as e:
        print(f"API Connection Error: {e}")
        return False

if __name__ == "__main__":
    ai_passed = test_ai_learner_event()
    if ai_passed:
        test_api_learner_endpoints()
