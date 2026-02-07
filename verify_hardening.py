
import asyncio
import os
import sys

# Add services/ai to path
sys.path.append(os.path.abspath("services/ai"))

from verification.tier2 import Tier2Verifier

async def test_execution_failure():
    print("Testing Tier 2 Execution (expecting failure due to missing gRPC)...")
    
    # Initialize without LLM service as we only test execution
    verifier = Tier2Verifier(grpc_target="localhost:9999") # Invalid port
    
    code = "print('hello')"
    result = await verifier.verify_execution(code)
    
    print(f"Passed: {result.passed}")
    print(f"Errors: {result.errors}")
    
    # Assertions
    if result.passed:
        print("FAIL: Verification passed but should have failed!")
        sys.exit(1)
        
    if not any("Verification service" in e for e in result.errors):
        print("FAIL: Did not get expected connection error")
        sys.exit(1)
        
    print("SUCCESS: Configured fallback correctly removed.")

if __name__ == "__main__":
    asyncio.run(test_execution_failure())
