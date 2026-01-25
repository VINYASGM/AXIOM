import asyncio
import sys
import os

# Ensure we can import from services/ai
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # services/ai
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import via verification package to satisfy relative imports in tier1
from verification.tier1 import Tier1Verifier

async def main():
    print("Testing Rust Verifier Integration...")
    verifier = Tier1Verifier()
    
    # Test 1: Valid Python
    code_valid = "def foo():\n    return 'bar'"
    print(f"\nVerifying valid code:\n{code_valid}")
    result = await verifier.verify_syntax(code_valid)
    print(f"Result: {result.passed} (Source: {result.messages})")
    
    # Test 2: Invalid Python
    code_invalid = "def foo() return 'bar'" # Missing colon
    print(f"\nVerifying invalid code:\n{code_invalid}")
    result = await verifier.verify_syntax(code_invalid)
    print(f"Result: {result.passed}")
    if not result.passed:
        print(f"Errors: {result.errors}")

if __name__ == "__main__":
    asyncio.run(main())
