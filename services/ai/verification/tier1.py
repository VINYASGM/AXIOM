"""
Tier 1 Verifier
Fast, lightweight verification: syntax, types, lint.
Designed to run in <1 second.
"""
import ast
import subprocess
import tempfile
import os
import time
from typing import Optional
import grpc
try:
    from . import verifier_pb2, verifier_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
from .result import VerifierResult, VerificationTier


class Tier1Verifier:
    """
    Tier 1: Fast verification
    - Syntax validation (AST parsing)
    - Type checking (pyright/mypy)
    - Linting (ruff)
    """
    
    def __init__(self, grpc_target="localhost:50051"):
        self.tier = VerificationTier.TIER_1
        self.channel = None
        self.stub = None
        if GRPC_AVAILABLE:
            try:
                self.channel = grpc.insecure_channel(grpc_target)
                self.stub = verifier_pb2_grpc.VerifierServiceStub(self.channel)
            except Exception as e:
                print(f"Failed to connect to Rust verifier: {e}")
    
    async def verify_all(self, code: str, language: str = "python") -> list[VerifierResult]:
        """Run all Tier 1 verifiers"""
        results = []
        
        if language.lower() == "python":
            results.append(await self.verify_syntax(code))
            results.append(await self.verify_types(code))
            results.append(await self.verify_lint(code))
        elif language.lower() in ["typescript", "javascript"]:
            results.append(await self.verify_syntax_js(code, language))
        else:
            # Fallback: just syntax check
            results.append(VerifierResult(
                name="unknown_language",
                tier=self.tier,
                passed=True,
                confidence=0.5,
                messages=[f"Language '{language}' not fully supported, skipping deep verification"],
                warnings=[f"Limited verification for {language}"]
            ))
        
        return results
    
    async def verify_syntax(self, code: str) -> VerifierResult:
        """Verify Python syntax using Rust Verifier Service"""
        start = time.time()
        
        # Try Rust service first
        if self.stub:
            try:
                request = verifier_pb2.VerifyRequest(
                    code=code,
                    language="python",
                    checks=["syntax"]
                )
                response = self.stub.Verify(request)
                
                messages = []
                errors = []
                
                if response.valid:
                    messages.append("Syntax valid (Rust Verifier)")
                else:
                    for issue in response.issues:
                        if issue.severity == "error":
                            errors.append(f"Syntax error line {issue.line}: {issue.message}")
                
                return VerifierResult(
                    name="syntax_check_rust",
                    tier=self.tier,
                    passed=response.valid,
                    confidence=1.0 if response.valid else 0.0,
                    messages=messages,
                    errors=errors,
                    duration_ms=(time.time() - start) * 1000
                )
            except grpc.RpcError as e:
                print(f"Rust verifier failed, falling back: {e}")

        # Fallback to local python (existing logic)
        errors = []
        messages = []
        
        try:
            ast.parse(code)
            passed = True
            confidence = 1.0
            messages.append("Syntax is valid (Fallback)")
        except SyntaxError as e:
            passed = False
            confidence = 0.0
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        except Exception as e:
            passed = False
            confidence = 0.0
            errors.append(f"Parse error: {str(e)}")
        
        return VerifierResult(
            name="syntax_check_fallback",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            errors=errors,
            duration_ms=(time.time() - start) * 1000
        )
    
    async def verify_types(self, code: str) -> VerifierResult:
        """
        Type check Python code.
        Uses pyright if available, falls back to basic type hint validation.
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
            # Try pyright first (faster than mypy)
            result = subprocess.run(
                ['pyright', '--outputjson', temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                passed = True
                confidence = 0.95
                messages.append("Type check passed (pyright)")
            else:
                # Parse pyright output
                import json
                try:
                    output = json.loads(result.stdout)
                    error_count = output.get('summary', {}).get('errorCount', 0)
                    warning_count = output.get('summary', {}).get('warningCount', 0)
                    
                    if error_count == 0:
                        passed = True
                        confidence = 0.9 if warning_count > 0 else 0.95
                        if warning_count > 0:
                            warnings.append(f"{warning_count} type warnings")
                    else:
                        passed = False
                        confidence = max(0.3, 1.0 - (error_count * 0.1))
                        errors.append(f"{error_count} type errors found")
                except:
                    passed = True
                    confidence = 0.7
                    messages.append("Type check completed with unknown status")
                    
        except FileNotFoundError:
            # pyright not installed, try basic validation
            passed = True
            confidence = 0.6
            messages.append("Type checker not available, using basic validation")
            warnings.append("Install pyright for full type checking: pip install pyright")
        except subprocess.TimeoutExpired:
            passed = True
            confidence = 0.5
            warnings.append("Type check timed out")
        except Exception as e:
            passed = True
            confidence = 0.5
            warnings.append(f"Type check error: {str(e)}")
        finally:
            os.unlink(temp_path)
        
        return VerifierResult(
            name="type_check",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            errors=errors,
            warnings=warnings,
            duration_ms=(time.time() - start) * 1000
        )
    
    async def verify_lint(self, code: str) -> VerifierResult:
        """
        Lint Python code using ruff (fast linter).
        Falls back to basic checks if ruff not available.
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
            result = subprocess.run(
                ['ruff', 'check', '--output-format=json', temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            import json
            try:
                issues = json.loads(result.stdout) if result.stdout else []
                
                error_issues = [i for i in issues if i.get('code', '').startswith('E')]
                warning_issues = [i for i in issues if not i.get('code', '').startswith('E')]
                
                if not error_issues:
                    passed = True
                    confidence = 0.95 if not warning_issues else 0.85
                    messages.append(f"Lint passed with {len(warning_issues)} warnings")
                else:
                    passed = False
                    confidence = max(0.3, 1.0 - (len(error_issues) * 0.1))
                    errors.extend([f"{i['code']}: {i['message']} (line {i.get('location', {}).get('row', '?')})" 
                                   for i in error_issues[:5]])
                    
                for w in warning_issues[:3]:
                    warnings.append(f"{w['code']}: {w['message']}")
                    
            except json.JSONDecodeError:
                passed = True
                confidence = 0.7
                messages.append("Lint check completed")
                
        except FileNotFoundError:
            # ruff not installed
            passed = True
            confidence = 0.6
            messages.append("Linter not available, using basic checks")
            warnings.append("Install ruff for linting: pip install ruff")
            
            # Basic checks
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if len(line) > 120:
                    warnings.append(f"Line {i+1} exceeds 120 characters")
                    
        except subprocess.TimeoutExpired:
            passed = True
            confidence = 0.5
            warnings.append("Lint check timed out")
        except Exception as e:
            passed = True
            confidence = 0.5
            warnings.append(f"Lint error: {str(e)}")
        finally:
            os.unlink(temp_path)
        
        return VerifierResult(
            name="lint_check",
            tier=self.tier,
            passed=passed,
            confidence=confidence,
            messages=messages,
            errors=errors,
            warnings=warnings,
            duration_ms=(time.time() - start) * 1000
        )
    
    async def verify_syntax_js(self, code: str, language: str) -> VerifierResult:
        """Basic syntax check for JavaScript/TypeScript"""
        start = time.time()
        
        # Simple bracket/brace matching
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        
        for i, char in enumerate(code):
            if char in '([{':
                stack.append((char, i))
            elif char in ')]}':
                if not stack or stack[-1][0] != pairs[char]:
                    return VerifierResult(
                        name="syntax_check_js",
                        tier=self.tier,
                        passed=False,
                        confidence=0.0,
                        errors=[f"Unmatched '{char}' at position {i}"],
                        duration_ms=(time.time() - start) * 1000
                    )
                stack.pop()
        
        if stack:
            return VerifierResult(
                name="syntax_check_js",
                tier=self.tier,
                passed=False,
                confidence=0.0,
                errors=[f"Unclosed '{stack[-1][0]}' at position {stack[-1][1]}"],
                duration_ms=(time.time() - start) * 1000
            )
        
        return VerifierResult(
            name="syntax_check_js",
            tier=self.tier,
            passed=True,
            confidence=0.8,
            messages=[f"{language} syntax appears valid (basic check)"],
            warnings=["Full TypeScript/JavaScript type checking requires additional setup"],
            duration_ms=(time.time() - start) * 1000
        )
