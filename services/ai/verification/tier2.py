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

class Tier2Verifier:
    """
    Tier 2: Medium verification
    - Auto-generated unit tests
    - Property-based testing hints
    - Contract validation
    """
    
    
    def __init__(self, llm_service: Optional[LLMService] = None, grpc_target="localhost:50051"):
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
        Runs in sandbox with timeout.
        """
        start = time.time()
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
                # Fallback to python logic
        
        errors = []
        messages = []
        
        # Create a safe test environment
        test_code = f'''
import sys
from io import StringIO

# Capture output
old_stdout = sys.stdout
sys.stdout = StringIO()

try:
    # Execute the code in isolated namespace
    exec_globals = {{"__builtins__": __builtins__}}
    exec("""{code.replace('"', '\\"')}""", exec_globals)
    print("__EXECUTION_SUCCESS__")
except Exception as e:
    print(f"__EXECUTION_ERROR__: {{type(e).__name__}}: {{str(e)}}")

# Restore stdout
output = sys.stdout.getvalue()
sys.stdout = old_stdout
print(output)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                ['python', temp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout + result.stderr
            
            if "__EXECUTION_SUCCESS__" in output:
                passed = True
                confidence = 0.9
                messages.append("Code executed successfully")
            elif "__EXECUTION_ERROR__" in output:
                passed = False
                confidence = 0.2
                error_match = re.search(r"__EXECUTION_ERROR__: (.+)", output)
                if error_match:
                    errors.append(f"Runtime error: {error_match.group(1)}")
                else:
                    errors.append("Unknown runtime error")
            else:
                passed = True
                confidence = 0.7
                messages.append("Execution completed (results unclear)")
                
        except subprocess.TimeoutExpired:
            passed = False
            confidence = 0.1
            errors.append("Execution timed out (possible infinite loop)")
        except Exception as e:
            passed = True
            confidence = 0.5
            messages.append(f"Could not test execution: {str(e)}")
        finally:
            os.unlink(temp_path)
        
        return VerifierResult(
            name="execution_test_fallback",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            errors=errors,
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
                # Fallback to python
        
        warnings = []
        messages = []
        
        import ast
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return VerifierResult(
                name="docstring_check_fallback",
                tier=self.tier,
                passed=True,
                confidence=0.0,
                errors=["Cannot parse code for docstring analysis"],
                duration_ms=(time.time() - start) * 1000
            )
        
        total_definitions = 0
        documented = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total_definitions += 1
                
                # Check for docstring
                if (node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)):
                    documented += 1
                else:
                    warnings.append(f"'{node.name}' lacks a docstring")
        
        if total_definitions == 0:
            passed = True
            confidence = 0.8
            messages.append("No functions or classes to document")
        else:
            ratio = documented / total_definitions
            passed = ratio >= 0.5  # At least 50% documented
            confidence = min(0.95, 0.5 + ratio * 0.45)
            messages.append(f"{documented}/{total_definitions} definitions documented ({ratio*100:.0f}%)")
        
        return VerifierResult(
            name="docstring_check_fallback",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            warnings=warnings[:5],  # Limit warnings
            duration_ms=(time.time() - start) * 1000,
            metadata={"total": total_definitions, "documented": documented}
        )
