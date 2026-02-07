
import asyncio
import json
import uuid
import requests
from nats.aio.client import Client as NATS

NATS_URL = "nats://localhost:4222"
API_URL = "http://localhost:8000"

async def test_event_emission():
    print("📡 Testing Event Bus Emission...")
    
    # Connect to NATS
    nc = NATS()
    try:
        await nc.connect(NATS_URL)
        print("   ✅ Connected to NATS")
    except Exception as e:
        print(f"   ❌ Failed to connect to NATS: {e}")
        return

    # Use a future to signal event receipt
    event_received = asyncio.Future()
    
    async def message_handler(msg):
        data = json.loads(msg.data.decode())
        subject = msg.subject
        print(f"   📨 Received event: {subject} -> {data.get('event')}")
        if data.get('event') == 'generation_completed':
            if not event_received.done():
                event_received.set_result(True)

    # Subscribe to relevant subjects
    await nc.subscribe("gen.>", cb=message_handler)
    print("   ✅ Subscribed to 'gen.>'")

    # Trigger Generation via API
    print("\n   🚀 Triggering generation...")
    payload = {
        "sdo_id": str(uuid.uuid4()),
        "intent": "Create a hello world python function",
        "candidate_count": 1
    }
    
    try:
        resp = requests.post(f"{API_URL}/generate/parallel", json=payload)
        resp.raise_for_status()
        data = resp.json()
        print(f"   ✅ Generation requested. Status: {data.get('status')}")
        if 'error' in data:
            print(f"   ⚠️ SDO Error: {data.get('error')}")
    except Exception as e:
        print(f"   ❌ API Request failed: {e}")
        await nc.close()
        return

    # Wait for event
    try:
        print("   ⏳ Waiting for 'generation_completed' event...")
        await asyncio.wait_for(event_received, timeout=10.0)
        print("   ✅ Event verified!")
    except asyncio.TimeoutError:
        print("   ❌ Timeout waiting for event.")
    finally:
        await nc.close()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_event_emission())
