"""
AXIOM Platform Simulation Test

Simulates the full frontend-to-backend flow since browser tool is unavailable.
1. Verifies Frontend (Next.js) is serving at localhost:3000
2. Verifies Backend (FastAPI) is serving at localhost:8000
3. Simulates the user 'intent' submission exactly as the frontend does
4. Follows the SDO lifecycle through the API
"""
import requests
import time
import sys
import json

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8002"

def print_step(step, status):
    print(f"  → {step}: {status}")

def run_simulation():
    print("\n" + "=" * 60)
    print("  AXIOM Platform Simulation (Frontend → Backend)")
    print("=" * 60)
    
    # 1. Verify Frontend is Up
    try:
        print_step("Checking Frontend (Next.js)", "...")
        resp = requests.get(FRONTEND_URL, timeout=2)
        if resp.status_code == 200:
            print_step("Checking Frontend (Next.js)", f"✓ Found AXIOM UI ({len(resp.text)} bytes)")
        else:
            print_step("Checking Frontend (Next.js)", f"✗ Status {resp.status_code}")
            return False
    except Exception as e:
        print_step("Checking Frontend (Next.js)", f"✗ Failed: {e}")
        return False

    # 2. Verify Backend is Up
    try:
        print_step("Checking Backend (FastAPI)", "...")
        
        # Debug: Check OpenAPI schema to see registered routes
        try:
            schema_resp = requests.get(f"{BACKEND_URL}/openapi.json", timeout=2)
            if schema_resp.status_code == 200:
                schema = schema_resp.json()
                paths = schema.get("paths", {}).keys()
                if "/router/health" in paths:
                    print_step("Debug OpenAPI", "✓ /router/health found in schema")
                else:
                    print_step("Debug OpenAPI", f"✗ /router/health NOT in schema. Available: {list(paths)[:5]}...")
        except Exception as e:
            print_step("Debug OpenAPI", f"✗ Failed: {e}")

        # Check router health endpoint (Phase 3 feature)
        resp = requests.get(f"{BACKEND_URL}/router/health", timeout=2)
        if resp.status_code == 200:
            health = resp.json()
            print_step("Checking Backend (FastAPI)", f"✓ Online (Providers: {list(health.keys())})")
        else:
            print_step("Checking Backend (FastAPI)", f"✗ Status {resp.status_code}")
            return False
    except Exception as e:
        print_step("Checking Backend (FastAPI)", f"✗ Failed: {e}")
        return False

    # 3. Simulate "Generate" action
    print("\n[User Action] Entering intent: 'Create a recursive fibonacci function'")
    
    intent = "Create a recursive fibonacci function"
    simulation_id = f"sim-{int(time.time())}"
    
    # Payload matching frontend 'apps/web/src/components/ReviewPanel.tsx' call (conceptually)
    # The frontend calls POST /generate/adaptive (Phase 2)
    payload = {
        "intent": intent, 
        "language": "python",
        "model": "mock", # Force mock to avoid API key requirement
        "sdo_id": simulation_id
    }
    
    try:
        print_step("Submitting to /generate/adaptive", "...")
        start = time.time()
        resp = requests.post(f"{BACKEND_URL}/generate/adaptive", json=payload)
        
        if resp.status_code == 200:
            data = resp.json()
            duration = time.time() - start
            print_step("Submitting to /generate/adaptive", f"✓ Received SDO (took {duration:.2f}s)")
            
            sdo_id = data.get("sdo_id") or simulation_id
            print(f"     SDO ID: {sdo_id}")
            print(f"     Status: {data.get('status')}")
            
            # 4. Verify Content
            code = data.get("selected_code", "")
            if "def" in code and "fib" in code:
                print_step("Verifying Generated Code", "✓ Found valid python code")
                print("-" * 40)
                print(code.strip())
                print("-" * 40)
            else:
                print_step("Verifying Generated Code", "✗ No code or invalid code")
                return False
                
            # 5. Check Cache (Phase 3)
            # Should have hit cache or stored it
            try:
                cache_resp = requests.get(f"{BACKEND_URL}/cache/stats")
                stats = cache_resp.json()
                print_step("Checking Semantic Cache", f"✓ Stats: {stats}")
            except:
                print_step("Checking Semantic Cache", "⚠️ Failed to get stats")

            return True
            
        else:
            print_step("Submitting to /generate/adaptive", f"✗ Status {resp.status_code}")
            print(resp.text)
            return False
            
    except Exception as e:
        print_step("Submitting to /generate/adaptive", f"✗ Failed: {e}")
        return False

if __name__ == "__main__":
    success = run_simulation()
    sys.exit(0 if success else 1)
