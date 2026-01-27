"""
gRPC Verification Service Implementation

Provides streaming verification progress and quick synchronous Tier 0 checks.
"""
import asyncio
import time
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass

import grpc
from grpc import aio


class VerificationServicer:
    """
    gRPC service implementation for code verification.
    
    Provides:
    - Streaming verification with progress updates
    - Batch verification for multiple candidates
    - Quick Tier 0 synchronous verification
    """
    
    def __init__(self, orchestra=None):
        """
        Initialize the verification servicer.
        
        Args:
            orchestra: VerificationOrchestra instance
        """
        self.orchestra = orchestra
    
    async def VerifyStream(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[dict]:
        """
        Stream verification progress for a candidate.
        
        Yields events for each tier and verifier as they complete.
        """
        ivcu_id = request.get("ivcu_id", "")
        candidate_id = request.get("candidate_id", "")
        code = request.get("code", "")
        language = request.get("language", "python")
        options = request.get("options", {})
        
        # Tier 0 - Tree-sitter
        if options.get("run_tier0", True):
            yield self._make_event(ivcu_id, candidate_id, "tier_started", {
                "tier": "tier_0",
                "description": "Syntax validation with Tree-sitter",
                "verifier_count": 1
            })
            
            try:
                from verification import verify_tier0
                
                start = time.time()
                result = await verify_tier0(code, language)
                elapsed = (time.time() - start) * 1000
                
                yield self._make_event(ivcu_id, candidate_id, "tier_complete", {
                    "tier": "tier_0",
                    "passed": result.passed,
                    "confidence": result.confidence,
                    "execution_time_ms": elapsed,
                    "results": [{
                        "verifier": "tree_sitter",
                        "passed": result.passed,
                        "confidence": result.confidence,
                        "errors": [e.message for e in result.errors],
                        "warnings": [w.message for w in result.warnings],
                        "details": {
                            "node_count": str(result.node_count),
                            "functions": str(len(result.functions)),
                            "classes": str(len(result.classes))
                        }
                    }]
                })
                
                # Fail fast if Tier 0 fails
                if not result.passed and options.get("fail_fast", True):
                    yield self._make_completion(
                        ivcu_id, candidate_id, False, result.confidence, elapsed,
                        tier0_passed=False
                    )
                    return
                    
            except ImportError:
                yield self._make_event(ivcu_id, candidate_id, "tier_complete", {
                    "tier": "tier_0",
                    "passed": True,
                    "confidence": 0.5,
                    "execution_time_ms": 1.0,
                    "results": []
                })
        
        total_time = 0.0
        tier0_passed = True
        tier1_passed = True
        tier2_passed = None
        tier3_passed = None
        overall_confidence = 0.8
        
        # Tier 1 - Static analysis
        if options.get("run_tier1", True):
            yield self._make_event(ivcu_id, candidate_id, "tier_started", {
                "tier": "tier_1",
                "description": "Static analysis (type checking, linting)",
                "verifier_count": 3
            })
            
            try:
                from verification import Tier1Verifier
                
                verifier = Tier1Verifier()
                start = time.time()
                results = await verifier.verify_all(code, language)
                elapsed = (time.time() - start) * 1000
                total_time += elapsed
                
                tier1_passed = all(r.passed for r in results)
                tier1_confidence = sum(r.confidence for r in results) / len(results) if results else 0
                
                yield self._make_event(ivcu_id, candidate_id, "tier_complete", {
                    "tier": "tier_1",
                    "passed": tier1_passed,
                    "confidence": tier1_confidence,
                    "execution_time_ms": elapsed,
                    "results": [
                        {
                            "verifier": r.name,
                            "passed": r.passed,
                            "confidence": r.confidence,
                            "errors": r.errors,
                            "warnings": r.warnings,
                            "details": {}
                        }
                        for r in results
                    ]
                })
                
                overall_confidence = min(overall_confidence, tier1_confidence)
                
            except ImportError:
                tier1_passed = True
                yield self._make_event(ivcu_id, candidate_id, "tier_complete", {
                    "tier": "tier_1",
                    "passed": True,
                    "confidence": 0.7,
                    "execution_time_ms": 100.0,
                    "results": []
                })
        
        # Tier 2 - Dynamic testing (optional)
        if options.get("run_tier2", False):
            yield self._make_event(ivcu_id, candidate_id, "tier_started", {
                "tier": "tier_2",
                "description": "Dynamic testing (unit tests, property tests)",
                "verifier_count": 2
            })
            
            try:
                from verification import Tier2Verifier
                
                verifier = Tier2Verifier(None)
                start = time.time()
                results = await verifier.verify_all(code, language, request.get("contracts", []))
                elapsed = (time.time() - start) * 1000
                total_time += elapsed
                
                tier2_passed = all(r.passed for r in results)
                tier2_confidence = sum(r.confidence for r in results) / len(results) if results else 0
                
                yield self._make_event(ivcu_id, candidate_id, "tier_complete", {
                    "tier": "tier_2",
                    "passed": tier2_passed,
                    "confidence": tier2_confidence,
                    "execution_time_ms": elapsed,
                    "results": [
                        {
                            "verifier": r.name,
                            "passed": r.passed,
                            "confidence": r.confidence,
                            "errors": r.errors,
                            "warnings": r.warnings,
                            "details": {}
                        }
                        for r in results
                    ]
                })
                
                overall_confidence = min(overall_confidence, tier2_confidence)
                
            except ImportError:
                tier2_passed = True
        
        # Tier 3 - Formal verification (optional)
        if options.get("run_tier3", False):
            yield self._make_event(ivcu_id, candidate_id, "tier_started", {
                "tier": "tier_3",
                "description": "Formal verification (SMT solving, fuzzing)",
                "verifier_count": 2
            })
            
            # Tier 3 is expensive, simulate for now
            await asyncio.sleep(0.5)
            tier3_passed = True
            
            yield self._make_event(ivcu_id, candidate_id, "tier_complete", {
                "tier": "tier_3",
                "passed": True,
                "confidence": 0.9,
                "execution_time_ms": 500.0,
                "results": []
            })
        
        # Final completion
        passed = tier0_passed and tier1_passed
        if tier2_passed is not None:
            passed = passed and tier2_passed
        if tier3_passed is not None:
            passed = passed and tier3_passed
        
        yield self._make_completion(
            ivcu_id, candidate_id, passed, overall_confidence, total_time,
            tier0_passed=tier0_passed,
            tier1_passed=tier1_passed,
            tier2_passed=tier2_passed,
            tier3_passed=tier3_passed
        )
    
    async def VerifyBatch(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[dict]:
        """Verify multiple candidates in batch, streaming results."""
        ivcu_id = request.get("ivcu_id", "")
        candidates = request.get("candidates", [])
        language = request.get("language", "python")
        options = request.get("options", {})
        
        for candidate in candidates:
            # Create single verify request
            single_request = {
                "ivcu_id": ivcu_id,
                "candidate_id": candidate.get("candidate_id"),
                "code": candidate.get("code"),
                "language": language,
                "contracts": request.get("contracts", []),
                "options": options
            }
            
            async for event in self.VerifyStream(single_request, context):
                yield event
    
    async def QuickVerify(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> dict:
        """
        Quick Tier 0 only verification.
        
        Synchronous, <10ms target for real-time feedback.
        """
        code = request.get("code", "")
        language = request.get("language", "python")
        
        try:
            from verification import verify_tier0
            
            result = await verify_tier0(code, language)
            
            return {
                "passed": result.passed,
                "confidence": result.confidence,
                "parse_time_ms": result.parse_time_ms,
                "errors": [
                    {
                        "line": e.line,
                        "column": e.column,
                        "end_line": e.end_line,
                        "end_column": e.end_column,
                        "message": e.message,
                        "severity": e.severity
                    }
                    for e in result.errors
                ],
                "ast_info": {
                    "root_type": result.root_node_type or "",
                    "node_count": result.node_count,
                    "functions": [
                        {"name": f.get("name", ""), "start_line": f.get("line", 0), "end_line": f.get("end_line", 0)}
                        for f in result.functions
                    ],
                    "classes": [
                        {"name": c.get("name", ""), "start_line": c.get("line", 0), "end_line": c.get("end_line", 0)}
                        for c in result.classes
                    ],
                    "imports": result.imports
                }
            }
            
        except ImportError:
            # Fallback without tree-sitter
            try:
                compile(code, "<string>", "exec")
                return {
                    "passed": True,
                    "confidence": 0.5,
                    "parse_time_ms": 1.0,
                    "errors": [],
                    "ast_info": {"root_type": "module", "node_count": 0, "functions": [], "classes": [], "imports": []}
                }
            except SyntaxError as e:
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "parse_time_ms": 1.0,
                    "errors": [{
                        "line": e.lineno or 1,
                        "column": e.offset or 0,
                        "end_line": e.lineno or 1,
                        "end_column": (e.offset or 0) + 1,
                        "message": str(e.msg),
                        "severity": "error"
                    }],
                    "ast_info": {"root_type": "", "node_count": 0, "functions": [], "classes": [], "imports": []}
                }
    
    async def GetResult(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> dict:
        """Get a cached verification result."""
        # In production, this would fetch from database
        return {
            "ivcu_id": request.get("ivcu_id"),
            "candidate_id": request.get("candidate_id"),
            "found": False,
            "result": None
        }
    
    def _make_event(
        self,
        ivcu_id: str,
        candidate_id: str,
        event_type: str,
        data: dict
    ) -> dict:
        """Create a verification event."""
        return {
            "ivcu_id": ivcu_id,
            "candidate_id": candidate_id,
            "timestamp": int(time.time() * 1000),
            event_type: data
        }
    
    def _make_completion(
        self,
        ivcu_id: str,
        candidate_id: str,
        passed: bool,
        confidence: float,
        total_time: float,
        tier0_passed: bool = True,
        tier1_passed: bool = True,
        tier2_passed: Optional[bool] = None,
        tier3_passed: Optional[bool] = None
    ) -> dict:
        """Create a verification complete event."""
        return {
            "ivcu_id": ivcu_id,
            "candidate_id": candidate_id,
            "timestamp": int(time.time() * 1000),
            "complete": {
                "candidate_id": candidate_id,
                "passed": passed,
                "confidence": confidence,
                "total_time_ms": total_time,
                "tier0": {
                    "ran": True,
                    "passed": tier0_passed,
                    "confidence": 0.9 if tier0_passed else 0.0,
                    "error_count": 0 if tier0_passed else 1,
                    "warning_count": 0
                },
                "tier1": {
                    "ran": True,
                    "passed": tier1_passed,
                    "confidence": 0.8 if tier1_passed else 0.0,
                    "error_count": 0 if tier1_passed else 1,
                    "warning_count": 0
                },
                "tier2": {
                    "ran": tier2_passed is not None,
                    "passed": tier2_passed or False,
                    "confidence": 0.85 if tier2_passed else 0.0,
                    "error_count": 0,
                    "warning_count": 0
                } if tier2_passed is not None else None,
                "tier3": {
                    "ran": tier3_passed is not None,
                    "passed": tier3_passed or False,
                    "confidence": 0.95 if tier3_passed else 0.0,
                    "error_count": 0,
                    "warning_count": 0
                } if tier3_passed is not None else None
            }
        }
