import asyncio
import sys
import os

# Ensure we can import from services/ai
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # services/ai
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from verification.tier2 import Tier2Verifier

async def main():
    print("Testing Rust Tier 2 Verifier Integration...")
    verifier = Tier2Verifier() # Defaults to localhost:50051
    
    # Test 1: Docstrings
    code_docs = '''
def documented():
    "I have a docstring"
    pass

def undocumented():
    pass
'''
    print(f"\nVerifying docstrings:\n{code_docs}")
    result = await verifier.verify_docstrings(code_docs)
    print(f"Passed: {result.passed}")
    print(f"Messages: {result.messages}")
    print(f"Warnings: {result.warnings}")
    
    # Test 2: Execution (Valid)
    code_exec = "print('Hello check')"
    print(f"\nVerifying execution (Valid):\n{code_exec}")
    result = await verifier.verify_execution(code_exec)
    print(f"Passed: {result.passed}")
    print(f"Messages: {result.messages}")
    
    # Test 3: Execution (Error)
    code_fail = "raise ValueError('Kaboom')"
    print(f"\nVerifying execution (Error):\n{code_fail}")
    result = await verifier.verify_execution(code_fail)
    print(f"Passed: {result.passed}")
    print(f"Errors: {result.errors}")

if __name__ == "__main__":
    asyncio.run(main())
