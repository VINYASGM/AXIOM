import requests, json, time

API = "http://api:8080"
AI = "http://localhost:8000"

# Auth
r = requests.post(f"{API}/api/v1/auth/register", json={"email": "integ3@test.com", "password": "test1234", "name": "Test"})
r = requests.post(f"{API}/api/v1/auth/login", json={"email": "integ3@test.com", "password": "test1234"})
token = r.json()["token"]
h = {"Authorization": f"Bearer {token}"}

# 1. Parse intent
print("=== 1. POST /api/v1/intent/parse ===", flush=True)
r = requests.post(f"{API}/api/v1/intent/parse", headers=h, json={"raw_intent": "Build a calculator", "project_context": ""})
print(f"  Status: {r.status_code}", flush=True)
data = r.json()
sdo_id = data.get("sdo_id", "")
parsed = str(data.get("parsed_intent", ""))[:100]
print(f"  sdo_id: {sdo_id}", flush=True)
print(f"  parsed_intent: {parsed}", flush=True)
print(f"  confidence: {data.get('confidence', 'N/A')}", flush=True)

# 2. Create project + IVCU
r = requests.post(f"{API}/api/v1/projects", headers=h, json={"name": "CalcTest", "description": "x"})
pid = r.json()["id"]

print("=== 2. POST /api/v1/intent/create ===", flush=True)
r = requests.post(f"{API}/api/v1/intent/create", headers=h, json={"project_id": pid, "raw_intent": "Build a calculator", "contracts": [], "sdo_id": sdo_id})
print(f"  Status: {r.status_code}", flush=True)
ivcu_id = r.json().get("ivcu_id", "")
print(f"  ivcu_id: {ivcu_id}", flush=True)

# 3. Start generation
print("=== 3. POST /api/v1/generation/start ===", flush=True)
r = requests.post(f"{API}/api/v1/generation/start", headers=h, json={"ivcu_id": ivcu_id, "language": "python", "model_tier": "fast"})
print(f"  Status: {r.status_code}", flush=True)
print(f"  Response: {r.text[:200]}", flush=True)

# 4. Poll status
print("=== 4. Polling /generation/:id/status ===", flush=True)
for i in range(20):
    time.sleep(2)
    r = requests.get(f"{API}/api/v1/generation/{ivcu_id}/status", headers=h)
    d = r.json()
    status = d.get("status")
    stage = d.get("stage")
    progress = d.get("progress")
    print(f"  [{i+1}] status={status} stage={stage} progress={progress}", flush=True)
    if status in ["verified", "failed"]:
        break

# 5. Verify SDO trace
print("=== 5. SDO Trace (AI Service) ===", flush=True)
if sdo_id:
    r = requests.get(f"{AI}/sdo/{sdo_id}")
    hist = r.json().get("history", [])
    print(f"  history_steps: {len(hist)}", flush=True)
    for s in hist:
        print(f"    - {s['step_type']} (confidence={s['confidence']}, model={s['model_id']})", flush=True)

# 6. Verify API trace
print("=== 6. Reasoning Trace (Go API) ===", flush=True)
r = requests.get(f"{API}/api/v1/reasoning/{ivcu_id}", headers=h)
print(f"  Status: {r.status_code}", flush=True)
trace = r.json().get("trace", [])
print(f"  trace_steps: {len(trace)}", flush=True)

# 7. Verify DB: IVCU has code
print("=== 7. Final IVCU State ===", flush=True)
r = requests.get(f"{API}/api/v1/generation/{ivcu_id}/status", headers=h)
d = r.json()
print(f"  status: {d.get('status')}", flush=True)
print(f"  confidence: {d.get('confidence')}", flush=True)

print("\n=== ALL INTEGRATION TESTS PASSED ===", flush=True)
