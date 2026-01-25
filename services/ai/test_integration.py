import requests
import json
import time

API_URL = "http://localhost:8000"

def test_generate_flow():
    print("Testing Generation Flow...")
    
    # 1. Parse Intent
    intent_payload = {
        "intent": "Create a python function that calculates fibonacci series with unit tests",
        "project_context": "test_project"
    }
    
    print(f"1. Parsing intent: {intent_payload['intent']}")
    parse_res = requests.post(f"{API_URL}/parse-intent", json=intent_payload)
    
    if parse_res.status_code != 200:
        print(f"Parse Error: {parse_res.status_code} - {parse_res.text}")
        return
        
    parse_data = parse_res.json()
    sdo_id = parse_data["sdo_id"]
    print(f"   SDO Created: {sdo_id}")
    
    # 2. Generate Parallel
    gen_payload = {
        "sdo_id": sdo_id,
        "intent": intent_payload["intent"],
        "language": "python",
        "candidate_count": 1 # Keep it fast
    }
    
    print(f"2. Generating candidates for SDO {sdo_id}...")
    # Increase timeout for generation
    response = requests.post(f"{API_URL}/generate/parallel", json=gen_payload, timeout=60)
    
    if response.status_code != 200:
        print(f"Generate Error: {response.status_code} - {response.text}")
        return
        
    sdo = response.json()
    print("   Generation complete.")
    
    # 3. Verify Result Structure (Retrieved Context)
    print(f"   SDO Status: {sdo.get('status')}")
    if "retrieved_context" in sdo and sdo["retrieved_context"]:
        print("[Pass] 'retrieved_context' field exists and is populated.")
        print(f"       Chunks: {len(sdo['retrieved_context'].get('code_chunks', []))}")
    else:
        # It's possible no context was found, but field should exist if model is correct
        if "retrieved_context" in sdo:
             print("[Pass] 'retrieved_context' field exists (but might be empty/null).")
        else:
             print("[Fail] 'retrieved_context' field MISSING in response.")
        
    # 4. Check Verification Results
    candidates = sdo.get("candidates", [])
    if candidates:
        print(f"[Pass] Generated {len(candidates)} candidates.")
        
        cand = candidates[0]
        print(f"   Candidate ID: {cand.get('id')}")
        print(f"   Verification Passed: {cand.get('verification_passed')}")
        print(f"   Pruned: {cand.get('pruned')}")
        
        # Check candidate-level verification result
        if "verification_result" in cand:
             vr = cand["verification_result"]
             if vr:
                 print("[Pass] Candidate has 'verification_result'.")
                 # Check for unit tests
                 verifier_results = vr.get("verifier_results", [])
                 unit_tests = next((v for v in verifier_results if v.get("name") == "unit_tests"), None)
                 
                 if unit_tests:
                     print("[Pass] Found 'unit_tests' verifier.")
                     if unit_tests.get("details"):
                         print(f"       Log length: {len(str(unit_tests['details']))}")
                     else:
                         print("[Warn] 'unit_tests' details empty.")
                 else:
                     print("[Warn] 'unit_tests' verifier not ran.")
                     print(f"       Run verifiers: {[v.get('name') for v in verifier_results]}")
                     if vr.get('limitations'):
                         print(f"       Limitations: {vr.get('limitations')}")
             else:
                 print("[Fail] Candidate 'verification_result' is None/Empty.")
        else:
             print("[Fail] Candidate MISSING 'verification_result' key.")
             
    else:
        print("[Fail] No candidates generated.")
    
    pass

if __name__ == "__main__":
    try:
        test_generate_flow()
    except Exception as e:
        print(f"Test failed: {e}")
