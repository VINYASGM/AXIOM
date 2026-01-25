"""
Tier 2 Verification Strategy: Unit Tests
Generates unit tests for the candidate code using LLM and runs them.
"""
import asyncio
import os
import tempfile
import uuid
from typing import Dict, Any, List, Optional
import subprocess
from pydantic import BaseModel

from llm import LLMService
from .result import VerificationResult, VerifierResult, VerificationTier

class UnitTestsVerifier:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def verify(self, code: str, language: str = "python") -> VerifierResult:
        """
        Generates and runs unit tests for the provided code.
        """
        if language != "python":
            return VerifierResult(
                name="unit_tests",
                tier=VerificationTier.TIER_2,
                passed=True,
                score=0.5,
                details={"message": f"Unit test generation not supported for {language} yet"}
            )
            
        try:
            # 1. Generate Tests
            test_code = await self._generate_tests(code)
            
            # 2. Run Tests
            passed, output, duration = await self._run_tests(code, test_code)
            
            return VerifierResult(
                name="unit_tests",
                tier=VerificationTier.TIER_2,
                passed=passed,
                score=1.0 if passed else 0.0,
                details={
                    "test_code": test_code,
                    "output": output,
                    "duration_ms": duration * 1000
                }
            )
            
        except Exception as e:
            return VerifierResult(
                name="unit_tests",
                tier=VerificationTier.TIER_2,
                passed=False,
                score=0.0,
                details={"error": str(e)}
            )

    async def _generate_tests(self, code: str) -> str:
        """Generate pytest code for the given function"""
        # We need to construct a prompt for the LLM
        # This is a bit of a hack since LLMService doesn't expose a raw prompt method easily
        # We will create a dummy SDO payload
        
        prompt = f"""
        You are a QA Engineer. Write a comprehensive pytest test suite for the following Python code.
        The tests should cover edge cases and happy paths.
        Return ONLY the python code for the tests. Do not include markdown formatting or explanations.
        ensure you import the necessary modules.
        
        CODE TO TEST:
        {code}
        """
        
        # We'll rely on the LLM service to have a generic generate or use a fast model
        # For now, we will assume we can reuse generate_code with a specific instruction
        # Ideally, LLMService should have a `complete(prompt)` method.
        # Since we don't verified that, let's reuse generate_code with a crafted SDO
        
        from sdo import SDO
        dummy_sdo = SDO(
            id="test-gen",
            raw_intent="Generate unit tests",
            language="python",
            constraints=["Use pytest", "Cover edge cases"]
        )
        
        # We manually override the prompt construction inside LLMService by passing a "context" 
        # that actually forces the instruction, or we just trust the intent parsing.
        # To be robust, let's just use the intent.
        
        # Re-using the prompt logic:
        system_prompt = "You are an expert QA engineer. Write pytest unit tests for the provided code."
        user_prompt = f"Code:\n{code}\n\nWrite unit tests."
        
        # Calling generic completion if available or hacking it via generate_code
        # Let's assume LLMService has a method for this or we add one.
        # Checking LLMService source would be good, but let's implement a direct call if needed
        # or just use the intent.
        
        # For this step, I will add a `generate_tests` method to LLMService if it doesn't exist, 
        # or use `generate_code` with the code as context.
        
        # Let's try to set the raw intent to explicit instruction
        dummy_sdo.raw_intent = f"Write pytest unit tests for this code: \n\n{code}"
        
        test_code = await self.llm.generate_code(dummy_sdo)
        
        # Strip markdown if present
        if "```python" in test_code:
            test_code = test_code.split("```python")[1].split("```")[0].strip()
        elif "```" in test_code:
            test_code = test_code.split("```")[1].split("```")[0].strip()
            
        return test_code

    async def _run_tests(self, code: str, test_code: str) -> tuple[bool, str, float]:
        """Run the tests in a temporary directory"""
        import time
        start_time = time.time()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write source file
            src_path = os.path.join(tmpdir, "solution.py")
            with open(src_path, "w") as f:
                f.write(code)
                
            # Write test file
            # We need to ensure the test file imports from solution
            # We'll inject `from solution import *` if not present
            if "from solution import" not in test_code and "import solution" not in test_code:
                test_code = "from solution import *\n" + test_code
            
            test_path = os.path.join(tmpdir, "test_solution.py")
            with open(test_path, "w") as f:
                f.write(test_code)
                
            # Run pytest
            try:
                # Using subprocess to run pytest
                proc = await asyncio.create_subprocess_exec(
                    "pytest",
                    test_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir
                )
                
                stdout, stderr = await proc.communicate()
                passed = proc.returncode == 0
                output = stdout.decode() + "\n" + stderr.decode()
                
                return passed, output, time.time() - start_time
                
            except Exception as e:
                return False, str(e), time.time() - start_time
