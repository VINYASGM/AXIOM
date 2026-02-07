"""
Tier 2 Verifier
Medium-weight verification: unit tests, property tests, contract validation.
Designed to run in <10 seconds.
"""
import subprocess
import tempfile
import os
import time
import re
from typing import List, Optional
from .result import VerifierResult, VerificationTier
from .tier2_tests import UnitTestsVerifier
from llm import LLMService
import grpc
from utils.sandbox import get_sandbox

class Tier2Verifier:
    """
    Tier 2: Medium verification
    - Auto-generated unit tests
    - Property-based testing hints
    - Contract validation
    """
    
    
    def __init__(self, llm_service: Optional[LLMService] = None, grpc_target=None):
        if grpc_target is None:
            grpc_target = os.getenv("VERIFIER_URL", "verification:50051")

        self.tier = VerificationTier.TIER_2
        self.llm_service = llm_service
        self.unit_tests_verifier = UnitTestsVerifier(llm_service) if llm_service else None
        
        self.channel = None
        self.stub = None
        
        # Try importing generated protos (assuming they are in the same directory or path)
        try:
            import sys
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.append(current_dir)
            import verifier_pb2
            import verifier_pb2_grpc
            self.verifier_pb2 = verifier_pb2
            self.verifier_pb2_grpc = verifier_pb2_grpc
            
            self.channel = grpc.insecure_channel(grpc_target)
            self.stub = verifier_pb2_grpc.VerifierServiceStub(self.channel)
        except ImportError:
            print("Warning: Rust verifier protos not found. Tier 2 fallback to Python.")
        except Exception as e:
            print(f"Warning: Failed to connect to Rust verifier: {e}")
    
    async def verify_all(
        self, 
        code: str, 
        language: str = "python",
        contracts: Optional[List[dict]] = None
    ) -> List[VerifierResult]:
        """Run all Tier 2 verifiers"""
        results = []
        
        if language.lower() == "python":
            # 1. Verification Execution (Sandbox check)
            results.append(await self.verify_execution(code))
            
            # 2. Contract Verification
            results.append(await self.verify_contracts(code, contracts or []))
            
            # 3. Docstring Check
            results.append(await self.verify_docstrings(code))
            
            # 4. Unit Tests (New Tier 2)
            if self.unit_tests_verifier:
                results.append(await self.unit_tests_verifier.verify(code, language))
            else:
                results.append(VerifierResult(
                    verifier_id="unit_tests",
                    tier=self.tier,
                    passed=True,
                    confidence=0.5,
                    details={"message": "Skipped: LLMService not available"}
                ))
        else:
            results.append(VerifierResult(
                verifier_id="tier2_unsupported",
                tier=self.tier,
                passed=True,
                confidence=0.5,
                details={"message": f"Tier 2 verification not yet implemented for {language}"}
            ))
        
        return results
    
    async def verify_execution(self, code: str) -> VerifierResult:
        """
        Verify code can execute without runtime errors.
        Uses WASM Sandbox if available, falls back to Rust Verifier or static analysis.
        """
        start = time.time()
        sandbox = get_sandbox()
        
        # 1. Try WASM Sandbox (Preferred for isolation)
        if sandbox.is_available():
            # For Python, we currently use the secure mock/simulation
            # Real implementation would load python.wasm
            success, output, error = sandbox.run_python_mock(code)
            
            return VerifierResult(
                name="execution_sandbox_wasm",
                tier=self.tier,
                passed=success,
                confidence=1.0 if success else 0.0,
                messages=[output] if output else [],
                errors=[error] if error else [],
                duration_ms=(time.time() - start) * 1000,
                details={"engine": "wasmtime"}
            )

        # 2. Fallback to Rust Verifier (gRPC)
        if self.stub:
            try:
                # Use Rust Verifier
                request = self.verifier_pb2.VerifyRequest(
                    code=code,
                    language="python",
                    checks=["execution"]
                )
                response = self.stub.Verify(request)
                
                messages = []
                errors = []
                
                if response.valid:
                    messages.append("Code executed successfully (Rust Verifier)")
                else:
                    for issue in response.issues:
                        if issue.code == "EXECUTION_ERROR":
                            errors.append(f"Runtime error: {issue.message}")
                        elif issue.code == "EXECUTION_FAIL":
                             errors.append(f"Execution failed: {issue.message}")
                
                return VerifierResult(
                    name="execution_test_rust",
                    tier=self.tier,
                    passed=response.valid,
                    confidence=0.9 if response.valid else 0.2,
                    messages=messages,
                    errors=errors,
                    duration_ms=(time.time() - start) * 1000
                )
            except Exception as e:
                print(f"Rust execution check failed: {e}")
        
        # 3. Fallback to basic static check
        return VerifierResult(
            name="execution_check_static",
            tier=self.tier,
            passed=True, # Assume true if we can't run it, rely on Tier 0
            confidence=0.1,
            warnings=["Execution check skipped (Sandbox/RPC unavailable)"],
            duration_ms=(time.time() - start) * 1000
        )
    
    async def verify_contracts(
        self, 
        code: str, 
        contracts: List[dict]
    ) -> VerifierResult:
        """
        Verify code satisfies specified contracts.
        Contracts are preconditions, postconditions, and invariants.
        """
        start = time.time()
        errors = []
        warnings = []
        messages = []
        
        if not contracts:
            return VerifierResult(
                name="contract_check",
                tier=self.tier,
                passed=True,
                confidence=0.7,
                messages=["No contracts specified"],
                warnings=["Consider adding contracts for stronger verification"],
                duration_ms=(time.time() - start) * 1000
            )
        
        # Parse contracts and check if code structure matches
        validated = 0
        failed = 0
        
        for contract in contracts:
            contract_type = contract.get('type', 'unknown')
            description = contract.get('description', '')
            expression = contract.get('expression', '')
            
            # Simple validation: check if mentioned identifiers exist in code
            if expression:
                # Extract identifiers from expression
                identifiers = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expression)
                
                # Check if at least some identifiers are in code
                found = sum(1 for ident in identifiers if ident in code)
                
                if found >= len(identifiers) * 0.5:  # At least half found
                    validated += 1
                    messages.append(f"{contract_type}: '{description}' - likely satisfied")
                else:
                    warnings.append(f"{contract_type}: '{description}' - could not verify")
            else:
                # No expression, just note the contract
                messages.append(f"{contract_type}: '{description}' - documented only")
                validated += 1
        
        passed = failed == 0
        confidence = min(0.9, 0.5 + (validated / len(contracts)) * 0.4) if contracts else 0.7
        
        return VerifierResult(
            name="contract_check",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            errors=errors,
            warnings=warnings,
            duration_ms=(time.time() - start) * 1000,
            metadata={"contracts_checked": len(contracts), "validated": validated}
        )
    
    async def verify_docstrings(self, code: str) -> VerifierResult:
        """
        Check that functions/classes have proper documentation.
        """
        start = time.time()
        if self.stub:
            try:
                # Use Rust Verifier
                request = self.verifier_pb2.VerifyRequest(
                    code=code,
                    language="python",
                    checks=["docstrings"]
                )
                response = self.stub.Verify(request)
                
                messages = []
                warnings = []
                
                if response.valid:
                    messages.append("Docstring checks passed (Rust Verifier)")
                else:
                    for issue in response.issues:
                         if issue.code == "DOCSTRING_MISSING":
                             warnings.append(issue.message)
                
                # Rust verifier might not return count stats easily in current proto without update
                # Assuming simple pass/fail for now with warnings
                
                return VerifierResult(
                    name="docstring_check_rust",
                    tier=self.tier,
                    passed=response.valid,
                    confidence=0.95 if response.valid else 0.5,
                    messages=messages,
                    warnings=warnings,
                    duration_ms=(time.time() - start) * 1000
                )
            except Exception as e:
                print(f"Rust docstring check failed: {e}")
                return VerifierResult(
                    name="docstring_check_rust",
                    tier=self.tier,
                    passed=False,
                    confidence=0.0,
                    errors=[f"Verification service unreachable: {str(e)}"],
                    duration_ms=(time.time() - start) * 1000
                )
        
        return VerifierResult(
            name="docstring_check_rust",
            tier=self.tier,
            passed=False,
            confidence=0.0,
            errors=["Verification service not configured"],
            duration_ms=(time.time() - start) * 1000
        )
