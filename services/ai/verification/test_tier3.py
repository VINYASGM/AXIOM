import asyncio
import os
import sys

# Add services/ai to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from verification.orchestra import VerificationOrchestra

async def test_tier3():
    print("Initializing Orchestra...")
    orchestra = VerificationOrchestra()
    
    # 1. Test Secure Code
    print("\n--- Testing SECURE Code ---")
    secure_code = """
def calculate_sum(a: int, b: int) -> int:
    "Returns the sum of two integers."
    return a + b
"""
    result = await orchestra.verify(
        code=secure_code, 
        sdo_id="test_secure", 
        run_tier3=True
    )
    print(f"Passed: {result.passed}")
    print(f"Confidence: {result.confidence}")
    for r in result.verifier_results:
        if r.tier.name == "TIER_3":
            print(f"Tier 3 [{r.name}]: {r.passed} - {r.messages or r.errors or r.warnings}")

    # 2. Test Insecure Code (Bandit should catch this)
    print("\n--- Testing INSECURE Code ---")
    insecure_code = """
import subprocess

def run_cmd(cmd: str):
    # Security flaw: shell=True
    subprocess.call(cmd, shell=True)
"""
    result = await orchestra.verify(
        code=insecure_code, 
        sdo_id="test_insecure", 
        run_tier3=True
    )
    print(f"Passed: {result.passed}")
    for r in result.verifier_results:
        if r.tier.name == "TIER_3":
            print(f"Tier 3 [{r.name}]: {r.passed}")
            if r.errors:
                print(f"Errors: {r.errors}")
            if r.warnings:
                print(f"Warnings: {r.warnings}")

if __name__ == "__main__":
    asyncio.run(test_tier3())
