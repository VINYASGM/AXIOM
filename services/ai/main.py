from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import os
import uuid
import time
import json

# Import modules
from sdo import SDO, SDOStatus, Candidate
from llm import LLMService
from memory import MemoryService
from sdo_engine import SDOEngine
from economics import EconomicsService, CostEstimate
from verification import VerificationOrchestra, VerificationResult
from knowledge import KnowledgeService
from database import DatabaseService

# Initialize Services (will be fully initialized in lifespan)
llm_service = LLMService()
memory_service = MemoryService(embed_fn=llm_service.embed_text)
knowledge_service = KnowledgeService(memory_service)
sdo_engine = SDOEngine(llm_service, knowledge_service)
economics_service = EconomicsService()
verification_orchestra = VerificationOrchestra(llm_service)
database_service = DatabaseService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    # Startup
    print("Initializing AXIOM AI Service v0.5.0...")
    
    # Initialize Memory
    memory_initialized = await memory_service.initialize()
    if memory_initialized:
        print("Memory service connected to Qdrant")
    else:
        print("Memory service running without Qdrant (fallback mode)")
        
    # Initialize Database
    db_initialized = await database_service.initialize()
    if db_initialized:
        print("Database service connected to PostgreSQL")
    else:
        print("WARNING: Database service failed to connect")

    print("SDO Engine ready")
    print("Economics service ready")
    print("Verification Orchestra ready")
    yield
    # Shutdown
    print("Shutting down AXIOM AI Service...")
    await database_service.close()


app = FastAPI(
    title="AXIOM AI Service",
    description="AI-powered intent parsing, code generation with parallel candidates, verification, cost control, and persistence",
    version="0.5.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session tracking for economics (simple in-memory for now, could be in DB too)
session_store: Dict[str, str] = {}  # sdo_id -> session_id

class ParseIntentRequest(BaseModel):
    intent: str
    context: Optional[str] = None

class ParseIntentResponse(BaseModel):
    parsed_intent: Dict[str, Any]
    confidence: float
    suggested_refinements: List[str]
    extracted_constraints: List[str]
    sdo_id: str

class GenerateRequest(BaseModel):
    sdo_id: str
    intent: Optional[str] = None # Optional override
    language: str
    contracts: Optional[List[Dict[str, Any]]] = None

class GenerateResponse(BaseModel):
    code: str
    confidence: float
    model_id: str
    sdo_id: str
    reasoning: Optional[str] = None

@app.get("/health")
async def health():
    """Health check endpoint"""
    memory_health = memory_service.health_check()
    db_status = "connected" if database_service.pool else "disconnected"
    return {
        "status": "healthy",
        "service": "axiom-ai",
        "version": "0.5.0",
        "database": db_status,
        "llm_provider": "openai" if llm_service.openai_key else "mock",
        "memory": memory_health
    }

@app.post("/parse-intent", response_model=ParseIntentResponse)
async def parse_intent(request: ParseIntentRequest):
    """
    Parse raw natural language intent into structured format using LLM.
    Creates a new SDO instance.
    """
    # 1. Call LLM to parse intent
    parsed_result = await llm_service.parse_intent(request.intent)
    
    # 2. Create SDO
    sdo_id = str(uuid.uuid4())
    sdo = SDO(
        id=sdo_id,
        raw_intent=request.intent,
        language="python", # Default, will be updated
        status=SDOStatus.PARSING
    )
    
    # 3. Update SDO with parsed data
    sdo.parsed_intent = parsed_result
    # Map parsed result to flattened response fields
    if isinstance(parsed_result, dict):
        constraints = parsed_result.get("constraints", [])
        refinements = parsed_result.get("suggested_refinements", [])
        confidence = 0.85 if len(refinements) == 0 else 0.6
    else:
        # Pydantic model handling if raw object returned
        constraints = parsed_result.constraints
        refinements = parsed_result.suggested_refinements
        confidence = 0.85
        parsed_result = parsed_result.dict()

    sdo.constraints = constraints
    sdo.status = SDOStatus.PLANNING
    sdo.confidence = confidence
    
    # Store SDO in DB
    await database_service.save_sdo(sdo.model_dump())
    
    return ParseIntentResponse(
        parsed_intent=parsed_result,
        confidence=confidence,
        suggested_refinements=refinements,
        extracted_constraints=constraints,
        sdo_id=sdo_id
    )

@app.post("/generate", response_model=GenerateResponse)
async def generate_code(request: GenerateRequest):
    """
    Generate code from SDO state.
    """
    # 1. Retrieve or Create SDO
    sdo_data = await database_service.get_sdo(request.sdo_id)
    if sdo_data:
        sdo = SDO(**sdo_data)
        if request.intent:
            sdo.raw_intent = request.intent # Update intent if provided
    else:
        # Create ad-hoc SDO if ID not found (fallback)
        sdo = SDO(
            id=request.sdo_id or str(uuid.uuid4()),
            raw_intent=request.intent or "Unknown intent",
            language=request.language,
            status=SDOStatus.DRAFT
        )
        await database_service.save_sdo(sdo.model_dump())

    # 2. Update SDO state
    sdo.status = SDOStatus.GENERATING
    sdo.language = request.language
    
    # 3. Call LLM
    start_time = time.time()
    code = await llm_service.generate_code(sdo)
    latency = time.time() - start_time
    
    # 4. Update SDO with result
    sdo.code = code
    sdo.status = SDOStatus.VERIFYING # Ready for verification
    
    # Add step to history
    sdo.add_step(
        step_type="generation",
        content={"code_length": len(code), "latency": latency},
        confidence=0.8, # Placeholder
        model="gpt-4-turbo"
    )

    # Save to DB
    await database_service.save_sdo(sdo.model_dump())

    return GenerateResponse(
        code=code,
        confidence=sdo.confidence,
        model_id="gpt-4-turbo", # Should come from LLM service
        sdo_id=sdo.id,
        reasoning=f"Generated {sdo.language} code. Latency: {latency:.3f}s"
    )

# ============================================================================
# Memory Endpoints
# ============================================================================

class MemoryStoreRequest(BaseModel):
    content: str
    type: str = "code"  # code, intent, context
    language: Optional[str] = "python"
    file_path: Optional[str] = None
    sdo_id: Optional[str] = None

class MemoryStoreResponse(BaseModel):
    id: Optional[str]
    success: bool
    message: str

class MemoryRetrieveResponse(BaseModel):
    results: List[Dict[str, Any]]
    query: str
    count: int


@app.get("/memory/health")
async def memory_health_endpoint():
    """Check memory service (Qdrant) health."""
    return memory_service.health_check()


@app.post("/memory/store", response_model=MemoryStoreResponse)
async def store_in_memory(request: MemoryStoreRequest):
    """
    Store content in vector memory.
    """
    try:
        if request.type == "code":
            chunk_id = await memory_service.store_code_chunk(
                content=request.content,
                file_path=request.file_path,
                language=request.language or "python",
                sdo_id=request.sdo_id
            )
        elif request.type == "intent":
            chunk_id = await memory_service.store_intent(
                raw_intent=request.content,
                sdo_id=request.sdo_id
            )
        else:
            return MemoryStoreResponse(
                id=None,
                success=False,
                message=f"Unknown type: {request.type}. Use 'code' or 'intent'."
            )
        
        if chunk_id:
            return MemoryStoreResponse(
                id=chunk_id,
                success=True,
                message=f"Stored {request.type} chunk"
            )
        else:
            return MemoryStoreResponse(
                id=None,
                success=False,
                message="Failed to store (check if Qdrant is running)"
            )
    except Exception as e:
        return MemoryStoreResponse(
            id=None,
            success=False,
            message=str(e)
        )


@app.get("/memory/retrieve", response_model=MemoryRetrieveResponse)
async def retrieve_from_memory(
    query: str = Query(..., description="Search query"),
    type: str = Query("code", description="Type: code or intent"),
    limit: int = Query(5, ge=1, le=20, description="Max results")
):
    """
    Retrieve relevant context from vector memory using semantic search.
    """
    collection = "code_chunks" if type == "code" else "intent_history"
    
    results = await memory_service.retrieve_context(
        query=query,
        collection=collection,
        limit=limit
    )
    
    return MemoryRetrieveResponse(
        results=[r.model_dump() for r in results],
        query=query,
        count=len(results)
    )


# ============================================================================
# Phase 2: Parallel Generation Endpoints
# ============================================================================

class ParallelGenerateRequest(BaseModel):
    sdo_id: str
    intent: Optional[str] = None
    language: str = "python"
    candidate_count: int = 3
    session_id: Optional[str] = "default"

class CandidateResponse(BaseModel):
    id: str
    code: str
    confidence: float
    verification_passed: bool
    verification_score: float
    pruned: bool
    verification_result: Optional[Dict[str, Any]] = None

class ParallelGenerateResponse(BaseModel):
    sdo_id: str
    status: str
    candidates: List[CandidateResponse]
    selected_candidate_id: Optional[str] = None
    selected_code: Optional[str] = None
    confidence: float
    cost_usd: float = 0.0
    retrieved_context: Optional[Dict[str, Any]] = None


@app.post("/generate/parallel", response_model=ParallelGenerateResponse)
async def generate_parallel(request: ParallelGenerateRequest):
    """
    Generate multiple code candidates in parallel, verify, and select best.
    """
    # Get or create SDO
    sdo_data = await database_service.get_sdo(request.sdo_id)
    if sdo_data:
        sdo = SDO(**sdo_data)
        if request.intent:
            sdo.raw_intent = request.intent
    else:
        sdo = SDO(
            id=request.sdo_id or str(uuid.uuid4()),
            raw_intent=request.intent or "Unknown intent",
            language=request.language,
            status=SDOStatus.DRAFT
        )
    
    # Save initial state
    await database_service.save_sdo(sdo.model_dump())
    
    # Track session
    session_store[sdo.id] = request.session_id or "default"
    
    # Estimate cost first
    estimate = economics_service.estimate_generation_cost(
        intent=sdo.raw_intent,
        language=sdo.language,
        candidate_count=request.candidate_count
    )
    
    # Check budget
    can_proceed, msg, warning = economics_service.check_budget(
        session_id=request.session_id or "default",
        estimated_cost=estimate.estimated_cost_usd
    )
    
    if not can_proceed:
        raise HTTPException(status_code=402, detail=msg)
    
    # Run full generation flow
    await sdo_engine.full_generation_flow(sdo, candidate_count=request.candidate_count)
    
    # Record cost
    economics_service.record_usage(
        session_id=request.session_id or "default",
        sdo_id=sdo.id,
        operation="parallel_generate",
        model="gpt-4-turbo",
        input_tokens=estimate.input_tokens,
        output_tokens=estimate.output_tokens
    )
    
    # Save final state
    await database_service.save_sdo(sdo.model_dump())
    
    # If successful, ingest the result into Knowledge Service for RAG loop
    if sdo.status == SDOStatus.VERIFIED and sdo.code:
        asyncio.create_task(knowledge_service.ingest_sdo_result(
            sdo_id=sdo.id,
            intent=sdo.raw_intent,
            code=sdo.code,
            language=sdo.language
        ))
    
    return ParallelGenerateResponse(
        sdo_id=sdo.id,
        status=sdo.status.value,
        candidates=[
            CandidateResponse(
                id=c.id,
                code=c.code,
                confidence=c.confidence,
                verification_passed=c.verification_passed,
                verification_score=c.verification_score,
                pruned=c.pruned,
                verification_result=c.verification_result
            )
            for c in sdo.candidates
        ],
        selected_candidate_id=sdo.selected_candidate_id,
        selected_code=sdo.code,
        confidence=sdo.confidence,
        cost_usd=estimate.estimated_cost_usd,
        retrieved_context=sdo.retrieved_context
    )


# ============================================================================
# Verification Endpoints
# ============================================================================

class VerifyRequest(BaseModel):
    code: str
    language: str = "python"
    run_tier2: bool = True

class VerifyResponse(BaseModel):
    passed: bool
    confidence: float
    tier_1_passed: bool
    tier_2_passed: Optional[bool] = None
    total_errors: int
    total_warnings: int
    duration_ms: float
    verifier_results: List[Dict[str, Any]]


@app.post("/verify")
async def verify_code(request: VerifyRequest):
    """
    Verify code through the verification orchestra.
    """
    result = await verification_orchestra.verify(
        code=request.code,
        sdo_id="adhoc",
        language=request.language,
        run_tier2=request.run_tier2
    )
    
    return VerifyResponse(
        passed=result.passed,
        confidence=result.confidence,
        tier_1_passed=result.tier_1_passed,
        tier_2_passed=result.tier_2_passed,
        total_errors=result.total_errors,
        total_warnings=result.total_warnings,
        duration_ms=result.total_duration_ms,
        verifier_results=[r.model_dump() for r in result.verifier_results]
    )


@app.get("/verify/{sdo_id}")
async def get_verification_status(sdo_id: str = Path(..., description="SDO ID")):
    """
    Get verification status for an SDO.
    """
    sdo_data = await database_service.get_sdo(sdo_id)
    if not sdo_data:
        raise HTTPException(status_code=404, detail="SDO not found")
    
    sdo = SDO(**sdo_data)
    
    # Get verification results from candidates
    results = []
    if sdo.candidates:
        for candidate in sdo.candidates:
            results.append({
                "candidate_id": candidate.id,
                "passed": candidate.verification_passed,
                "score": candidate.verification_score,
                "pruned": candidate.pruned
            })
    
    return {
        "sdo_id": sdo_id,
        "status": sdo.status.value,
        "selected_candidate_id": sdo.selected_candidate_id,
        "confidence": sdo.confidence,
        "candidates": results
    }


# ============================================================================
# Cost Endpoints
# ============================================================================

class CostEstimateRequest(BaseModel):
    intent: str
    language: str = "python"
    candidate_count: int = 3

class CostEstimateResponse(BaseModel):
    estimated_cost_usd: float
    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    model: str


@app.post("/cost/estimate", response_model=CostEstimateResponse)
async def estimate_cost(request: CostEstimateRequest):
    """
    Estimate cost before generation.
    """
    estimate = economics_service.estimate_generation_cost(
        intent=request.intent,
        language=request.language,
        candidate_count=request.candidate_count
    )
    
    return CostEstimateResponse(
        estimated_cost_usd=estimate.estimated_cost_usd,
        input_tokens=estimate.input_tokens,
        output_tokens=estimate.output_tokens,
        embedding_tokens=estimate.embedding_tokens,
        model=estimate.model
    )


@app.get("/cost/session/{session_id}")
async def get_session_cost(session_id: str = Path(..., description="Session ID")):
    """
    Get cost summary for a session.
    """
    return economics_service.get_session_summary(session_id)


# ============================================================================
# Undo & History Endpoints (Phase 2)
# ============================================================================

class UndoResponse(BaseModel):
    success: bool
    message: str
    previous_state: Optional[Dict[str, Any]] = None

class HistoryItem(BaseModel):
    id: str
    operation: str
    created_at: str
    is_current: bool

class HistoryResponse(BaseModel):
    sdo_id: str
    snapshots: List[HistoryItem]

class StatsResponse(BaseModel):
    total_generations: int
    successful: int
    success_rate: float
    bandit_arms: List[Dict[str, Any]]
    overall_stats: Dict[str, Any]


@app.post("/undo/{sdo_id}", response_model=UndoResponse)
async def undo_sdo(sdo_id: str = Path(..., description="SDO ID")):
    """
    Rollback SDO to previous state.
    Uses the SDOHistory system for snapshots.
    """
    previous_state = sdo_engine.undo(sdo_id)
    
    if previous_state is None:
        return UndoResponse(
            success=False,
            message="No previous state available for undo",
            previous_state=None
        )
    
    # Save the restored state to database
    await database_service.save_sdo(previous_state)
    
    return UndoResponse(
        success=True,
        message="Successfully restored previous state",
        previous_state=previous_state
    )


@app.post("/redo/{sdo_id}", response_model=UndoResponse)
async def redo_sdo(sdo_id: str = Path(..., description="SDO ID")):
    """
    Redo the last undone operation on an SDO.
    """
    next_state = sdo_engine.redo(sdo_id)
    
    if next_state is None:
        return UndoResponse(
            success=False,
            message="No next state available for redo",
            previous_state=None
        )
    
    # Save the restored state to database
    await database_service.save_sdo(next_state)
    
    return UndoResponse(
        success=True,
        message="Successfully restored next state",
        previous_state=next_state
    )


@app.get("/history/{sdo_id}", response_model=HistoryResponse)
async def get_sdo_history(sdo_id: str = Path(..., description="SDO ID")):
    """
    Get operation history for an SDO.
    """
    snapshots = sdo_engine.get_history(sdo_id)
    
    return HistoryResponse(
        sdo_id=sdo_id,
        snapshots=[
            HistoryItem(
                id=s["id"],
                operation=s["operation"],
                created_at=s["created_at"],
                is_current=s["is_current"]
            )
            for s in snapshots
        ]
    )


@app.post("/history/{sdo_id}/restore/{snapshot_id}")
async def restore_snapshot(
    sdo_id: str = Path(..., description="SDO ID"),
    snapshot_id: str = Path(..., description="Snapshot ID to restore")
):
    """
    Restore SDO to a specific snapshot.
    """
    state = sdo_engine.history.restore(snapshot_id)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Save the restored state
    await database_service.save_sdo(state)
    
    return {
        "success": True,
        "message": f"Restored to snapshot {snapshot_id}",
        "sdo_id": sdo_id
    }


@app.get("/stats/generation", response_model=StatsResponse)
async def get_generation_stats():
    """
    Get generation statistics including bandit arm performance.
    """
    stats = sdo_engine.get_stats()
    
    return StatsResponse(
        total_generations=stats["total_generations"],
        successful=stats["successful"],
        success_rate=stats["success_rate"],
        bandit_arms=stats["bandit_arms"],
        overall_stats=stats["overall_stats"]
    )


# ============================================================================
# Adaptive Generation Endpoints (Phase 2)
# ============================================================================

class AdaptiveGenerateRequest(BaseModel):
    sdo_id: str
    intent: Optional[str] = None
    language: str = "python"
    early_stop_threshold: float = 0.9
    session_id: Optional[str] = "default"


@app.post("/generate/adaptive", response_model=ParallelGenerateResponse)
async def generate_adaptive(request: AdaptiveGenerateRequest):
    """
    Generate code using adaptive strategy with early stopping.
    """
    try:
        # Get or create SDO
        sdo_data = await database_service.get_sdo(request.sdo_id)
        if sdo_data:
            sdo = SDO(**sdo_data)
            if request.intent:
                sdo.raw_intent = request.intent
        else:
            sdo = SDO(
                id=request.sdo_id or str(uuid.uuid4()),
                raw_intent=request.intent or "Unknown intent",
                language=request.language,
                status=SDOStatus.DRAFT
            )
        
        # Save initial state
        await database_service.save_sdo(sdo.model_dump())
        
        # Track session
        session_store[sdo.id] = request.session_id or "default"
        
        # Run adaptive generation flow
        await sdo_engine.adaptive_generation_flow(
            sdo, 
            early_stop_threshold=request.early_stop_threshold
        )
        
        # Save final state
        await database_service.save_sdo(sdo.model_dump())
        
        # Ingest successful results for RAG
        if sdo.status == SDOStatus.VERIFIED and sdo.code:
            asyncio.create_task(knowledge_service.ingest_sdo_result(
                sdo_id=sdo.id,
                intent=sdo.raw_intent,
                code=sdo.code,
                language=sdo.language
            ))
        
        return ParallelGenerateResponse(
            sdo_id=sdo.id,
            status=sdo.status.value,
            candidates=[
                CandidateResponse(
                    id=c.id,
                    code=c.code,
                    confidence=c.confidence,
                    verification_score=c.verification_score,
                    verification_passed=c.verification_passed,
                    verification_result=c.verification_result,
                    pruned=c.pruned
                )
                for c in sdo.candidates
            ],
            selected_candidate_id=sdo.selected_candidate_id,
            selected_code=sdo.code,
            confidence=sdo.confidence,
            cost_usd=0.0,
            retrieved_context=sdo.retrieved_context
        )
    except Exception as e:
        import traceback
        with open("error.log", "w") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/sdo/{sdo_id}")
async def get_sdo(sdo_id: str = Path(..., description="SDO ID")):
    """
    Get full SDO state.
    """
    sdo_data = await database_service.get_sdo(sdo_id)
    if not sdo_data:
        raise HTTPException(status_code=404, detail="SDO not found")
    
    # Ensure SDO model validation
    sdo = SDO(**sdo_data)
    return sdo.model_dump()


# ============================================================================
# Phase 3: Intelligence Layer Endpoints
# ============================================================================

@app.get("/cache/stats")
async def get_cache_stats():
    """
    Get semantic cache statistics.
    """
    if sdo_engine.cache:
        return sdo_engine.cache.stats()
    return {"error": "Cache not enabled"}


@app.get("/cache/entries")
async def list_cache_entries(limit: int = Query(20, ge=1, le=100)):
    """
    List recent cache entries.
    """
    if sdo_engine.cache:
        return {"entries": sdo_engine.cache.list_entries(limit=limit)}
    return {"error": "Cache not enabled", "entries": []}


@app.delete("/cache/clear")
async def clear_cache():
    """
    Clear all cache entries.
    """
    if sdo_engine.cache:
        sdo_engine.cache.clear()
        return {"success": True, "message": "Cache cleared"}
    return {"success": False, "message": "Cache not enabled"}


@app.get("/router/providers")
async def list_providers():
    """
    List registered LLM providers.
    """
    return {
        "providers": sdo_engine.router.list_providers(),
        "fallback": sdo_engine.router.fallback
    }


@app.get("/router/metrics")
async def get_router_metrics():
    """
    Get LLM router metrics.
    """
    return sdo_engine.router.get_metrics()


@app.get("/router/health")
async def check_provider_health():
    """
    Check health of all LLM providers.
    """
    return await sdo_engine.router.health_check()


@app.get("/policy/rules")
async def list_policy_rules():
    """
    List all policy rules.
    """
    if sdo_engine.policy:
        return {"rules": sdo_engine.policy.list_rules()}
    return {"error": "Policy engine not enabled", "rules": []}


class PolicyCheckRequest(BaseModel):
    code: str
    check_type: str = "post"  # "pre" or "post"


@app.post("/policy/check")
async def check_policy(request: PolicyCheckRequest):
    """
    Check code or intent against policies.
    """
    if not sdo_engine.policy:
        return {"error": "Policy engine not enabled"}
    
    if request.check_type == "pre":
        result = sdo_engine.policy.check_pre_generation(request.code)
    else:
        result = sdo_engine.policy.check_post_generation(request.code)
    
    return result.to_dict()


if __name__ == "__main__":
    import uvicorn
    print("DEBUG: STARTING ON PORT 8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)



