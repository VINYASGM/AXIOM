"""
Verification Orchestra
Coordinates multi-tier verification across all verifiers.

Architecture v2.0:
- Tier 0: Tree-sitter (<10ms) - Instant syntax validation
- Tier 1: Static analysis (<2s) - Type checking, linting
- Tier 2: Dynamic testing (2-15s) - Unit tests, property checks
- Tier 3: Formal verification (15s-5min) - SMT solving, fuzzing
"""
import asyncio
import time
from typing import Optional, List, Dict, Any
from .result import VerificationResult, VerificationTier, TierResult
from .tier0 import verify_tier0, Tier0Result
from .tier1 import Tier1Verifier
from .tier2 import Tier2Verifier
from .tier3 import Tier3Verifier


from llm import LLMService

class VerificationOrchestra:
    """
    Orchestrates all verification tiers.
    
    Verification Pipeline:
    1. Tier 0 (Tree-sitter): Instant syntax check - always runs first
    2. Tier 1 (Static): Type checking, linting - runs if Tier 0 passes
    3. Tier 2 (Dynamic): Tests in sandbox - runs if Tier 1 passes
    4. Tier 3 (Formal): SMT solving - runs on request for high assurance
    
    Implements fail-fast strategy: stops if earlier tiers fail critically.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.tier1 = Tier1Verifier()
        self.tier2 = Tier2Verifier(llm_service)
        self.tier3 = Tier3Verifier()
        self._tier0_enabled = True
    
    async def verify(
        self,
        code: str,
        sdo_id: str,
        candidate_id: Optional[str] = None,
        language: str = "python",
        contracts: Optional[List[dict]] = None,
        run_tier2: bool = True,
        run_tier3: bool = False,
        fail_fast: bool = True
    ) -> VerificationResult:
        """
        Run full verification on code.
        
        Args:
            code: The code to verify
            sdo_id: SDO identifier
            candidate_id: Optional candidate identifier
            language: Programming language
            contracts: Optional contract specifications
            run_tier2: Whether to run Tier 2 (slower)
            fail_fast: Stop if Tier 1 has critical failures
        
        Returns:
            VerificationResult with all tier results
        """
        result = VerificationResult(
            sdo_id=sdo_id,
            candidate_id=candidate_id
        )
        
        # Run Tier 0 (Tree-sitter, <10ms) - Always runs first
        if self._tier0_enabled:
            tier0_start = time.time()
            tier0_result = await verify_tier0(code, language)
            tier0_time = (time.time() - tier0_start) * 1000
            
            # Convert Tier 0 result to TierResult
            tier0_tier_result = TierResult(
                tier=VerificationTier.TIER_0,
                verifier="tree_sitter",
                passed=tier0_result.passed,
                confidence=tier0_result.confidence,
                execution_time_ms=tier0_time,
                details={
                    "node_count": tier0_result.node_count,
                    "functions": tier0_result.functions,
                    "classes": tier0_result.classes,
                    "imports": tier0_result.imports
                },
                errors=[e.to_dict() for e in tier0_result.errors],
                warnings=[w.to_dict() for w in tier0_result.warnings]
            )
            result.add_result(tier0_tier_result)
            
            # Fail fast if Tier 0 has syntax errors
            if fail_fast and not tier0_result.passed:
                result.limitations.append("Subsequent tiers skipped due to syntax errors")
                return result.finalize()
        
        # Run Tier 1 (Static analysis, <2s)
        tier1_results = await self.tier1.verify_all(code, language)
        for r in tier1_results:
            result.add_result(r)
        
        # Check if we should continue to Tier 2
        tier1_passed = all(r.passed for r in tier1_results)
        tier1_critical_fail = any(
            not r.passed and r.confidence < 0.2 
            for r in tier1_results
        )
        
        if fail_fast and tier1_critical_fail:
            result.limitations.append("Tier 2 skipped due to critical Tier 1 failures")
            return result.finalize()
        
        # Run Tier 2 if requested and Tier 1 passed
        if run_tier2 and tier1_passed:
            tier2_results = await self.tier2.verify_all(code, language, contracts)
            for r in tier2_results:
                result.add_result(r)
        elif run_tier2 and not tier1_passed:
            result.limitations.append("Tier 2 skipped due to Tier 1 failures")
            
        # Run Tier 3 if requested and passed previous tiers
        if run_tier3 and result.passed:
            tier3_results = await self.tier3.verify_all(code, language)
            for r in tier3_results:
                result.add_result(r)
        elif run_tier3 and not result.passed:
            result.limitations.append("Tier 3 skipped due to prior failures")
        
        return result.finalize()
    
    async def verify_parallel_candidates(
        self,
        candidates: List[dict],
        sdo_id: str,
        language: str = "python",
        contracts: Optional[List[dict]] = None
    ) -> List[VerificationResult]:
        """
        Verify multiple candidates in parallel.
        
        Args:
            candidates: List of {id, code} dicts
            sdo_id: SDO identifier
            language: Programming language
            contracts: Optional contract specifications
        
        Returns:
            List of VerificationResults, one per candidate
        """
        tasks = [
            self.verify(
                code=c['code'],
                sdo_id=sdo_id,
                candidate_id=c['id'],
                language=language,
                contracts=contracts
            )
            for c in candidates
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                # Create error result
                final_results.append(VerificationResult(
                    sdo_id=sdo_id,
                    candidate_id=candidates[i]['id'],
                    passed=False,
                    confidence=0.0,
                    limitations=[f"Verification failed: {str(r)}"]
                ).finalize())
            else:
                final_results.append(r)
        
        return final_results
    
    async def quick_verify(
        self,
        code: str,
        sdo_id: str,
        language: str = "python"
    ) -> VerificationResult:
        """
        Quick Tier 1 only verification.
        Use for rapid feedback during generation.
        """
        return await self.verify(
            code=code,
            sdo_id=sdo_id,
            language=language,
            run_tier2=False,
            fail_fast=False
        )
    
    def select_best_candidate(
        self,
        results: List[VerificationResult]
    ) -> Optional[VerificationResult]:
        """
        Select the best candidate based on verification results.
        
        Selection criteria:
        1. Must pass all tiers
        2. Highest confidence
        3. Fewest warnings
        """
        passing = [r for r in results if r.passed]
        
        if not passing:
            # No passing candidates, return least bad
            return max(results, key=lambda r: r.confidence) if results else None
        
        # Score candidates
        def score(r: VerificationResult) -> float:
            return r.confidence - (r.total_warnings * 0.01)
        
        return max(passing, key=score)
