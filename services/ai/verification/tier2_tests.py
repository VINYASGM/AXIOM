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

from agents.test_generator import TestGenerator

class UnitTestsVerifier:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.agent = TestGenerator(llm_service)

    async def verify(self, code: str, language: str = "python") -> VerifierResult:
        """
        Generates and runs unit tests for the provided code.
        """
        if language != "python":
            return VerifierResult(
                name="unit_tests",
                tier=VerificationTier.TIER_2,
                passed=True,
                confidence=0.5,
                details={"message": f"Unit test generation not supported for {language} yet"}
            )
            
        try:
            # 1. Generate Tests using Agent
            agent_result = await self.agent.run({
                "code": code, 
                "language": language
            })
            
            if not agent_result.success:
                raise Exception(f"Test generation failed: {agent_result.error}")
                
            test_code = agent_result.data.get("tests", "")
            
            # 2. Run Tests
            passed, output, duration = await self._run_tests(code, test_code)
            
            return VerifierResult(
                name="unit_tests",
                tier=VerificationTier.TIER_2,
                passed=passed,
                confidence=1.0 if passed else 0.0,
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
                confidence=0.0,
                details={"error": str(e)}
            )

    async def _generate_tests(self, code: str) -> str:
        # Deprecated in favor of self.agent.run()
        pass

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
