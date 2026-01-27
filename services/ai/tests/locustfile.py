from locust import HttpUser, task, between
import json

class AxiomUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login on start."""
        # For this test, we assume public endpoints or mock auth
        # In a real scenario, we'd hit /auth/login
        pass

    @task(10)
    def health_check(self):
        self.client.get("/health")

    @task(5)
    def metrics(self):
        self.client.get("/metrics")

    @task(1)
    def verify_proof_load(self):
        """Test CPU-intensive verification."""
        # Sample proof payload (simplified)
        payload = {
            "code": "def hello(): return 'world'",
            "proof": {
                "proof_id": "load-test-proof",
                "code_hash": "sha256:...",
                # Invalid signature but exercises parsing logic
                "signature": "00"*64
            }
        }
        self.client.post("/proof/verify", json=payload)

    @task(1)
    def parse_intent(self):
        """Test intent parsing (Mock or Real)."""
        self.client.post("/parse-intent", json={
            "intent": "Create a simple calculator function",
            "context": "load-test"
        })
