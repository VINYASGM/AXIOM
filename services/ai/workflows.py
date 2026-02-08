"""
Temporal Workflow Definitions for AXIOM

Durable workflows for critical operations:
- IntentParsingWorkflow: Parse intent → extract constraints → create SDO
- CodeGenerationWorkflow: Generate candidates → verify → select best
- VerificationWorkflow: Run verification tiers → aggregate results

Temporal provides:
- Durable execution (survives crashes)
- Automatic retries with backoff
- Workflow versioning
- Visibility into running workflows
"""
import asyncio
from datetime import timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from temporalio import workflow, activity
from temporalio.common import RetryPolicy


# =============================================================================
# Data Classes for Workflow Parameters
# =============================================================================

@dataclass
class IntentInput:
    """Input for intent parsing workflow."""
    intent: str
    user_id: str
    org_id: str
    session_id: Optional[str] = None
    complexity: int = 5


@dataclass
class IntentOutput:
    """Output from intent parsing workflow."""
    sdo_id: str
    parsed_intent: Dict[str, Any]
    constraints: List[str]
    confidence: float


@dataclass
class GenerationInput:
    """Input for code generation workflow."""
    sdo_id: str
    intent: str
    constraints: List[str]
    language: str = "python"
    candidate_count: int = 3
    model_tier: str = "balanced"


@dataclass
class GenerationOutput:
    """Output from code generation workflow."""
    sdo_id: str
    candidates: List[Dict[str, Any]]
    selected_code: str
    selected_candidate_id: str
    total_cost: float


@dataclass
class VerificationInput:
    """Input for verification workflow."""
    sdo_id: str
    code: str
    candidate_id: str
    language: str = "python"
    verification_tier: str = "standard"


@dataclass
class VerificationOutput:
    """Output from verification workflow."""
    sdo_id: str
    passed: bool
    confidence: float
    tiers_passed: List[str]
    tiers_failed: List[str]
    details: Dict[str, Any]


# =============================================================================
# Default Retry Policy
# =============================================================================

DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
)


# =============================================================================
# Activities (Individual Operations)
# =============================================================================

@activity.defn
async def parse_intent_activity(intent: str, complexity: int) -> Dict[str, Any]:
    """
    Parse user intent and extract structured information.
    
    This activity interfaces with the LLM to parse intent.
    """
    # Import here to avoid circular imports
    from llm import LLMService
    
    llm = LLMService()
    result = await llm.parse_intent(intent)
    
    return {
        "parsed_intent": result.get("parsed_intent", {}),
        "constraints": result.get("constraints", []),
        "confidence": result.get("confidence", 0.0)
    }


@activity.defn
async def create_sdo_activity(
    user_id: str,
    org_id: str,
    parsed_intent: Dict[str, Any],
    constraints: List[str]
) -> str:
    """
    Create a new SDO (Semantic Development Object).
    
    Returns SDO ID.
    """
    from sdo import SDOEngine
    
    engine = SDOEngine()
    sdo = await engine.create_sdo({
        "user_id": user_id,
        "org_id": org_id,
        "intent": parsed_intent,
        "constraints": constraints
    })
    
    return sdo.id if hasattr(sdo, 'id') else str(sdo)


@activity.defn
async def generate_candidates_activity(
    intent: str,
    constraints: List[str],
    language: str,
    count: int,
    model_tier: str
) -> List[Dict[str, Any]]:
    """
    Generate code candidates using LLM.
    """
    from llm import LLMService
    
    llm = LLMService()
    candidates = []
    
    for i in range(count):
        result = await llm.generate(
            prompt=f"Generate {language} code for: {intent}\nConstraints: {constraints}",
            temperature=0.7 + (i * 0.1)  # Vary temperature for diversity
        )
        candidates.append({
            "id": f"candidate-{i}",
            "code": result.get("code", ""),
            "model": result.get("model", "unknown"),
            "cost": result.get("cost", 0.0)
        })
    
    return candidates


@activity.defn
async def select_best_candidate_activity(
    candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Select the best candidate using weighted scoring.
    
    Scoring factors:
    - Verification passed: +50 points
    - Confidence: 0-30 points (scaled)
    - Cost efficiency: 0-20 points (inverse of cost)
    """
    if not candidates:
        return {"id": "", "code": "", "score": 0.0}
    
    scored_candidates = []
    max_cost = max(c.get("cost", 0.001) for c in candidates) or 0.001
    
    for candidate in candidates:
        score = 0.0
        
        # Verification bonus (50 points)
        if candidate.get("verified", False):
            score += 50.0
        
        # Confidence component (0-30 points)
        confidence = candidate.get("confidence", 0.0)
        score += confidence * 30.0
        
        # Cost efficiency (0-20 points, lower cost = higher score)
        cost = candidate.get("cost", 0.0)
        if max_cost > 0:
            cost_score = (1 - (cost / max_cost)) * 20.0
            score += max(0, cost_score)
        
        candidate["_selection_score"] = score
        scored_candidates.append(candidate)
    
    # Sort by score descending
    scored_candidates.sort(key=lambda c: c.get("_selection_score", 0), reverse=True)
    
    best = scored_candidates[0]
    return {
        "id": best.get("id", ""),
        "code": best.get("code", ""),
        "score": best.get("_selection_score", 0.0),
        "model": best.get("model", "unknown"),
        "cost": best.get("cost", 0.0)
    }


@activity.defn
async def run_verification_tier_activity(
    code: str,
    language: str,
    tier: str
) -> Dict[str, Any]:
    """
    Run a single verification tier.
    """
    from verification import VerificationOrchestra
    
    orchestra = VerificationOrchestra()
    result = await orchestra.verify_tier(code, language, tier)
    
    return {
        "tier": tier,
        "passed": result.get("passed", False),
        "confidence": result.get("confidence", 0.0),
        "details": result.get("details", {})
    }


@activity.defn
async def emit_event_activity(
    event_type: str,
    data: Dict[str, Any]
) -> bool:
    """
    Emit an event to the event bus.
    """
    from eventbus import get_event_bus
    
    bus = await get_event_bus()
    await bus.publish(f"workflow.{event_type}", data)
    return True


# =============================================================================
# Workflow Definitions
# =============================================================================

@workflow.defn
class IntentParsingWorkflow:
    """
    Workflow for parsing user intent and creating an SDO.
    
    Steps:
    1. Parse intent using LLM
    2. Extract constraints
    3. Create SDO
    4. Emit event
    """
    
    @workflow.run
    async def run(self, input: IntentInput) -> IntentOutput:
        workflow.logger.info(f"Starting intent parsing for: {input.intent[:50]}...")
        
        # Step 1: Parse intent
        parse_result = await workflow.execute_activity(
            parse_intent_activity,
            args=[input.intent, input.complexity],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY
        )
        
        # Step 2: Create SDO
        sdo_id = await workflow.execute_activity(
            create_sdo_activity,
            args=[
                input.user_id,
                input.org_id,
                parse_result["parsed_intent"],
                parse_result["constraints"]
            ],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY
        )
        
        # Step 3: Emit event
        await workflow.execute_activity(
            emit_event_activity,
            args=["intent_parsed", {"sdo_id": sdo_id, "intent": input.intent}],
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        return IntentOutput(
            sdo_id=sdo_id,
            parsed_intent=parse_result["parsed_intent"],
            constraints=parse_result["constraints"],
            confidence=parse_result["confidence"]
        )


@workflow.defn
class CodeGenerationWorkflow:
    """
    Workflow for generating and selecting best code candidate.
    
    Steps:
    1. Generate multiple candidates
    2. Verify each candidate
    3. Select best candidate
    4. Emit event
    """
    
    @workflow.run
    async def run(self, input: GenerationInput) -> GenerationOutput:
        workflow.logger.info(f"Starting code generation for SDO: {input.sdo_id}")
        
        # Step 1: Generate candidates
        candidates = await workflow.execute_activity(
            generate_candidates_activity,
            args=[
                input.intent,
                input.constraints,
                input.language,
                input.candidate_count,
                input.model_tier
            ],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=DEFAULT_RETRY_POLICY
        )
        
        # Step 2: Run basic verification on each candidate
        verified_candidates = []
        for candidate in candidates:
            try:
                verify_result = await workflow.execute_activity(
                    run_verification_tier_activity,
                    args=[candidate["code"], input.language, "syntax"],
                    start_to_close_timeout=timedelta(minutes=1)
                )
                candidate["verified"] = verify_result["passed"]
                candidate["confidence"] = verify_result["confidence"]
            except Exception:
                candidate["verified"] = False
                candidate["confidence"] = 0.0
            
            verified_candidates.append(candidate)
        
        # Step 3: Select best candidate
        best = await workflow.execute_activity(
            select_best_candidate_activity,
            args=[
                [c for c in verified_candidates if c.get("verified", False)] 
                or verified_candidates
            ],
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Calculate total cost
        total_cost = sum(c.get("cost", 0.0) for c in candidates)
        
        # Step 4: Emit event
        await workflow.execute_activity(
            emit_event_activity,
            args=["code_generated", {
                "sdo_id": input.sdo_id,
                "candidate_id": best.get("id"),
                "cost": total_cost
            }],
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        return GenerationOutput(
            sdo_id=input.sdo_id,
            candidates=verified_candidates,
            selected_code=best.get("code", ""),
            selected_candidate_id=best.get("id", ""),
            total_cost=total_cost
        )


@workflow.defn
class VerificationWorkflow:
    """
    Workflow for comprehensive code verification.
    
    Steps:
    1. Run syntax verification
    2. Run semantic verification
    3. Run security verification (if enabled)
    4. Aggregate results
    5. Issue ProofCertificate
    6. Emit event
    """
    
    VERIFICATION_TIERS = ["syntax", "semantic", "coverage"]
    
    @workflow.run
    async def run(self, input: VerificationInput) -> VerificationOutput:
        workflow.logger.info(f"Starting verification for SDO: {input.sdo_id}")
        
        tiers_passed = []
        tiers_failed = []
        all_details = {}
        total_confidence = 0.0
        verification_results = []
        
        # Run verification tiers
        for tier in self.VERIFICATION_TIERS:
            try:
                result = await workflow.execute_activity(
                    run_verification_tier_activity,
                    args=[input.code, input.language, tier],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=DEFAULT_RETRY_POLICY
                )
                
                if result["passed"]:
                    tiers_passed.append(tier)
                else:
                    tiers_failed.append(tier)
                
                total_confidence += result["confidence"]
                all_details[tier] = result["details"]
                
                # Collect for certificate
                verification_results.append({
                    "tier": tier,
                    "passed": result["passed"],
                    "confidence": result["confidence"],
                    "details": result["details"]
                })
                
            except Exception as e:
                tiers_failed.append(tier)
                all_details[tier] = {"error": str(e)}
                verification_results.append({
                    "tier": tier,
                    "passed": False,
                    "confidence": 0.0,
                    "details": {"error": str(e)}
                })
        
        # Calculate average confidence
        avg_confidence = total_confidence / len(self.VERIFICATION_TIERS) if self.VERIFICATION_TIERS else 0.0
        overall_passed = len(tiers_failed) == 0
        
        # Issue ProofCertificate if verification passed
        certificate_info = None
        if overall_passed:
            try:
                from proof_activity import issue_proof_certificate_activity
                certificate_info = await workflow.execute_activity(
                    issue_proof_certificate_activity,
                    args=[input.candidate_id, input.sdo_id, input.code, verification_results],
                    start_to_close_timeout=timedelta(seconds=30)
                )
                all_details["proof_certificate"] = certificate_info
            except Exception as e:
                workflow.logger.warn(f"ProofCertificate issuance failed: {e}")
        
        # Emit event
        await workflow.execute_activity(
            emit_event_activity,
            args=["verification_completed", {
                "sdo_id": input.sdo_id,
                "candidate_id": input.candidate_id,
                "passed": overall_passed,
                "confidence": avg_confidence,
                "certificate_id": certificate_info.get("certificate_id") if certificate_info else None
            }],
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        return VerificationOutput(
            sdo_id=input.sdo_id,
            passed=overall_passed,
            confidence=avg_confidence,
            tiers_passed=tiers_passed,
            tiers_failed=tiers_failed,
            details=all_details
        )


# =============================================================================
# Workflow Registry
# =============================================================================

WORKFLOWS = [
    IntentParsingWorkflow,
    CodeGenerationWorkflow,
    VerificationWorkflow,
]

ACTIVITIES = [
    parse_intent_activity,
    create_sdo_activity,
    generate_candidates_activity,
    select_best_candidate_activity,
    run_verification_tier_activity,
    emit_event_activity,
]
