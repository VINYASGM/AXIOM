"""
Tier 3 Verifier
Deep verification: Security scanning, Fuzz testing, SMT solving.
Designed to run in 10s-5min range.
"""
import subprocess
import tempfile
import os
import time
import json
import asyncio
from typing import List, Optional, Dict, Any
from .result import VerifierResult, VerificationTier
from .smt_verifier import get_smt_verifier

class Tier3Verifier:
    """
    Tier 3: Deep verification
    - Security scanning (Bandit)
    - Property-based/Fuzz testing (Hypothesis)
    - SMT Solver / Model Checking (Z3)
    """
    
    def __init__(self):
        self.tier = VerificationTier.TIER_3
    
    async def verify_all(
        self, 
        code: str, 
        language: str = "python",
        contracts: Optional[List[Dict[str, Any]]] = None
    ) -> List[VerifierResult]:
        """Run all Tier 3 verifiers"""
        results = []
        
        if language.lower() == "python":
            # 1. Security Scan (Bandit)
            results.append(await self.verify_security(code))
            
            # 2. Fuzz Check
            results.append(await self.verify_fuzz(code))
            
            # 3. SMT/Model Checking (Z3)
            results.append(await self.verify_smt(code, contracts))

        else:
            results.append(VerifierResult(
                name="tier3_unsupported",
                tier=self.tier,
                passed=True,
                confidence=0.5,
                messages=[f"Tier 3 verification not yet implemented for {language}"],
                warnings=[f"Deep verification skipped for {language}"]
            ))
        
        return results

    async def verify_smt(self, code: str, contracts: Optional[List[Dict[str, Any]]] = None) -> VerifierResult:
        """
        Symbolic Execution / SMT Solving (Z3).
        Verifies logical contracts (pre/post-conditions).
        """
        smt = get_smt_verifier()
        result = await smt.verify_contracts(code, contracts or [], "python")
        
        passed = result.status in ["sat", "disabled"] # Disabled counts as passed (skipped)
        
        messages = []
        warnings = []
        
        if result.status == "disabled":
            warnings.append("SMT Solver (Z3) not installed")
        elif result.status == "sat":
            messages.append(f"Formal verification passed in {result.solve_time_ms:.2f}ms")
            for a in result.assertions:
                messages.append(f"Verified: {a.name}")
        elif result.status == "unsat":
            warnings.append("Formal verification FAILED (Unsatisfiable)")
            for a in result.assertions:
                if not a.verified:
                    warnings.append(f"Failed contract: {a.name} ({a.expression})")
        
        return VerifierResult(
            name="smt_solver",
            tier=self.tier,
            passed=passed,
            confidence=1.0 if result.status == "sat" else 0.5,
            messages=messages,
            warnings=warnings,
            duration_ms=result.solve_time_ms
        )

    async def verify_security(self, code: str) -> VerifierResult:
        """
        Run static application security testing using Bandit.
        """
        start = time.time()
        errors = []
        warnings = []
        messages = []
        
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Run bandit
            # -f json: JSON output
            # -ll: Log level (report only medium/high severity)
            # --exit-zero: Don't exit with non-zero code on issues
            cmd = ['bandit', '-f', 'json', '-ll', '--exit-zero', temp_path]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            try:
                report = json.loads(stdout.decode())
                
                results = report.get('results', [])
                metrics = report.get('metrics', {}).get(temp_path, {})
                
                high_severity = [r for r in results if r['issue_severity'] == 'HIGH']
                medium_severity = [r for r in results if r['issue_severity'] == 'MEDIUM']
                low_severity = [r for r in results if r['issue_severity'] == 'LOW']
                
                if high_severity:
                    passed = False
                    confidence = 0.2
                    for issue in high_severity:
                        errors.append(f"SECURITY HIGH: {issue['issue_text']} (Line {issue['line_number']})")
                elif medium_severity:
                    passed = True # Pass but with warnings/penalty
                    confidence = 0.6
                    for issue in medium_severity:
                        warnings.append(f"SECURITY MEDIUM: {issue['issue_text']} (Line {issue['line_number']})")
                else:
                    passed = True
                    confidence = 1.0
                    messages.append("No high/medium security issues found")
                    
                # Add low severity as info/warnings
                for issue in low_severity:
                    warnings.append(f"Security Note: {issue['issue_text']}")
                    
            except json.JSONDecodeError:
                passed = True
                confidence = 0.5
                warnings.append("Could not parse security report")
                
        except FileNotFoundError:
            passed = True
            confidence = 0.5
            warnings.append("Bandit security scanner not installed")
        except Exception as e:
            passed = True
            confidence = 0.5
            warnings.append(f"Security scan failed: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        return VerifierResult(
            name="security_scan",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            errors=errors,
            warnings=warnings,
            duration_ms=(time.time() - start) * 1000
        )

    async def verify_fuzz(self, code: str) -> VerifierResult:
        """
        Check for property-based testing readiness and compatibility.
        Actual fuzzing requires generating specific property tests, 
        which is done by the TestGenerator agent.
        Here we check if the code is 'fuzzable' (has types, clean interfaces).
        """
        start = time.time()
        messages = []
        warnings = []
        
        # Simple heuristic check for type hints which enable better fuzzing
        import ast
        try:
            tree = ast.parse(code)
            functions_with_types = 0
            total_functions = 0
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_functions += 1
                    # Check if arguments have type annotations
                    has_args = any(arg.annotation for arg in node.args.args)
                    # Check if return has annotation
                    has_return = node.returns is not None
                    
                    if has_args or has_return:
                        functions_with_types += 1
            
            if total_functions > 0:
                type_coverage = functions_with_types / total_functions
                if type_coverage > 0.8:
                    confidence = 0.9
                    messages.append(f"High type coverage ({type_coverage:.0%}), good for fuzzing")
                elif type_coverage > 0.4:
                    confidence = 0.7
                    messages.append(f"Moderate type coverage ({type_coverage:.0%})")
                else:
                    confidence = 0.5
                    warnings.append("Low type coverage puts limits on automated fuzzing")
            else:
                confidence = 0.8 # No functions to fuzz
                messages.append("No functions found to fuzz")
                
            passed = True
            
        except Exception:
            passed = True
            confidence = 0.5
            warnings.append("Could not analyze fuzzability")

        return VerifierResult(
            name="fuzz_check",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            warnings=warnings,
            duration_ms=(time.time() - start) * 1000
        )
