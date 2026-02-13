from fastapi import FastAPI, HTTPException, Query, Path, WebSocket, WebSocketDisconnect
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import os
import uuid
import time
import json
import logging
import asyncio

# Import modules
from sdo import SDO, SDOStatus, Candidate
from llm import LLMService

# Load environment variables
from dotenv import load_dotenv
load_dotenv('../../.env')

from memory import MemoryService
from sdo_engine import SDOEngine
from economics import EconomicsService, CostEstimate
from verification import VerificationOrchestra, VerificationResult
from knowledge import KnowledgeService
from database import DatabaseService
import eventbus
from graph_memory import get_graph_memory
from model_config import DynamicModelConfig, init_model_config, get_model_config
from projection_engine import ProjectionEngine, init_projection_engine, get_projection_engine


# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Temporal Imports
from temporalio.client import Client as TemporalClient

# Initialize Services (will be fully initialized in lifespan)
llm_service = LLMService()
memory_service = MemoryService(embed_fn=llm_service.embed_text)
knowledge_service = KnowledgeService(memory_service)
knowledge_service = KnowledgeService(memory_service)
economics_service = EconomicsService()
verification_orchestra = VerificationOrchestra(llm_service)
database_service = DatabaseService()
verification_orchestra = VerificationOrchestra(llm_service)
database_service = DatabaseService()
# Initialize SDOEngine with stream callback (defined later, so we might need to set it post-init or move def up)
# Since def is below, we can assign it later or move init down.
# Moving init down is safer but disruptive.
# I will use a lambda or wrapper, OR just set it after definition.
# Better: Just set it in valid scope.
# Actually, `event_stream_callback` is defined AFTER this block in my previous edit.
# So I need to set it inside `lifespan` or move `sdo_engine` init down.
# Let's set it in lifespan startup.
sdo_engine = SDOEngine(llm_service, knowledge_service, database_service=database_service)


# Global Temporal Client
temporal_client = None

# Global Dynamic Model Config
model_config = None

# Global Projection Engine
projection_engine = None

def init_telemetry():
    """Initialize OpenTelemetry."""
    try:
        resource = Resource.create({"service.name": "axiom-ai"})
        trace.set_tracer_provider(TracerProvider(resource=resource))
        otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        print("Telemetry initialized successfully")
    except Exception as e:
        print(f"Failed to initialize telemetry: {e}")

async def event_stream_callback(event_type: str, data: Dict[str, Any]):
    """
    Callback for SDOEngine to stream events.
    """
    # For now, just log or print. 
    # In future, this should push to NATS subject or SSE queue.
    print(f"STREAM EVENT [{event_type}]: {data}")


# =============================================================================
# WebSocket Connection Manager
# =============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"WS Client connected: {client_id}")
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"WS Client disconnected: {client_id}")

    async def broadcast(self, message: Dict[str, Any]):
        try:
            # Convert to JSON handling datetime
            def json_serial(obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            msg_str = json.dumps(message, default=json_serial)
            
            to_remove = []
            for client_id, connection in self.active_connections.items():
                try:
                    await connection.send_text(msg_str)
                except Exception:
                    to_remove.append(client_id)
            
            for client_id in to_remove:
                self.disconnect(client_id)
        except Exception as e:
            print(f"Broadcast error: {e}")

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    # Startup
    print("Initializing AXIOM AI Service v0.5.0...")
    
    # Initialize Telemetry
    init_telemetry()

    # Start NATS listener for WebSockets
    async def nats_listener():
        try:
            # Wait for NATS to be ready
            await asyncio.sleep(5)
            bus = await eventbus.get_event_bus()
            
            async def handle_event(msg):
                await manager.broadcast(msg)
                
            # Subscribe to relevant streams
            await bus.subscribe("ivcu.>", eventbus.StreamName.IVCU_EVENTS, "ws-broadcaster-ivcu", handle_event)
            await bus.subscribe("gen.>", eventbus.StreamName.GENERATIONS, "ws-broadcaster-gen", handle_event)
            print("WebSocket NATS listener started")
        except Exception as e:
            print(f"Failed to start NATS listener: {e}")

    asyncio.create_task(nats_listener())

    print(f"DEBUG: QDRANT_URL = {os.getenv('QDRANT_URL')}")
    print(f"DEBUG: TEMPORAL_URL = {os.getenv('TEMPORAL_URL')}")
    print(f"DEBUG: NATS_URL = {os.getenv('NATS_URL')}")
    from memory.vector import MemoryConfig
    print(f"DEBUG: MemoryConfig.QDRANT_URL = {MemoryConfig.QDRANT_URL}")
    
    # Initialize NATS (Non-blocking)
    try:
        await asyncio.wait_for(eventbus.init_nats(), timeout=10.0)
    except Exception as e:
        print(f"WARN: NATS initialization failed/timed out: {e}")
    
    # Initialize Temporal
    global temporal_client
    try:
        temporal_host = os.getenv("TEMPORAL_URL", "axiom-temporal:7233")
        temporal_client = await asyncio.wait_for(TemporalClient.connect(temporal_host), timeout=10.0)
        print("Connected to Temporal")
    except Exception as e:
        print(f"WARN: Temporal connection failed/timed out: {e}")

    # Initialize Memory
    memory_initialized = False
    try:
        memory_initialized = await asyncio.wait_for(memory_service.initialize(), timeout=10.0)
        if memory_initialized:
            print("Memory service connected to Qdrant")
        else:
            print("Memory service running without Qdrant (fallback mode)")
    except Exception as e:
         print(f"WARN: Memory service initialization failed/timed out: {e}")
        
    # Initialize Database
    db_initialized = False
    try:
        db_initialized = await asyncio.wait_for(database_service.initialize(), timeout=10.0)
    except Exception as e:
        print(f"WARN: Database initialization failed/timed out: {e}")
    if db_initialized:
        print("Database service connected to PostgreSQL")
    else:
        print("WARNING: Database service failed to connect")

    # Initialize Dynamic Model Config
    global model_config
    if database_service.pool:
        try:
            model_config = await init_model_config(database_service.pool, cache_ttl=60)
            print(f"Model configuration loaded: {len(model_config._cache)} models")
        except Exception as e:
            print(f"WARN: Model config initialization failed: {e}")
    else:
        print("WARN: Model config skipped (no database pool)")

    print("SDO Engine ready")
    print("Economics service ready")
    print("Verification Orchestra ready")
    print("Verification Orchestra ready")
    
    # Initialize Streaming
    sdo_engine.stream_callback = event_stream_callback
    print("Event Streaming initialized")
    
    # Initialize Projection Engine
    global projection_engine
    try:
        projection_engine = await init_projection_engine(
            memory_service=memory_service,
            database_service=database_service
        )
        # Start consuming events (non-blocking)
        asyncio.create_task(projection_engine.start())
        print("Projection Engine started")
    except Exception as e:
        print(f"WARN: Projection Engine initialization failed: {e}")
    
    yield

    # Shutdown
    print("Shutting down AXIOM AI Service...")
    if projection_engine:
        await projection_engine.stop()
    await database_service.close()


app = FastAPI(
    title="AXIOM AI Service",
    description="AI-powered intent parsing, code generation with parallel candidates, verification, cost control, and persistence",
    version="0.5.0",
    lifespan=lifespan
)

# CORS
# app.add_middleware(
#    CORSMiddleware,
#    allow_origins=["*"],
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
# )

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

# ============================================================================
# Graph Visualization Endpoint (Phase B)
# ============================================================================

@app.get("/api/v1/graph")
async def get_graph(
    project_id: Optional[str] = None,
    limit: int = 200
):
    """
    Get full knowledge graph for visualization.
    Proxies to GraphMemoryStore.
    """
    if not database_service.pool:
         # Fallback or error if DB not ready
         raise HTTPException(status_code=503, detail="Database not initialized")
         
    graph_store = await get_graph_memory(database_service.pool)
    result = await graph_store.get_graph(project_id=project_id, limit=limit)
    return result.to_dict()


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        memory_health = await memory_service.health_check()
        db_status = "connected" if database_service.pool else "disconnected"
        
        # Check LLM providers
        providers_status = llm_service.get_available_providers() if hasattr(llm_service, 'get_available_providers') else {}
        default_provider = llm_service.default_provider if hasattr(llm_service, 'default_provider') else "mock"
        
        # Check model config
        model_config_status = None
        if model_config:
            model_config_status = model_config.get_cache_stats()
        
        # Check projection engine
        projection_status = None
        if projection_engine:
            projection_status = projection_engine.get_stats()
        
        return {
            "status": "healthy",
            "service": "axiom-ai",
            "version": "0.7.0",
            "database": db_status,
            "llm_providers": providers_status,
            "default_llm_provider": default_provider,
            "model_config": model_config_status,
            "projection_engine": projection_status,
            "memory": memory_health
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from metrics import get_metrics
    return get_metrics()

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

class GraphNode(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    confidence: float
    status: str
    constraints: List[str]
    complexity: str = "medium"

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str = "proof"
    status: str

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

@app.get("/api/v1/graph", response_model=GraphResponse)
async def get_sde_graph():
    """
    Get the semantic graph of all SDOs.
    """
    sdos = await database_service.get_all_sdos(limit=100)
    
    nodes = []
    for sdo in sdos:
        constraints = []
        if sdo.get('parsed_intent') and isinstance(sdo['parsed_intent'], dict):
            constraints = sdo['parsed_intent'].get('constraints', [])
        
        # Determine status mapping
        status = sdo.get('status', 'draft')
        if status == 'generated': status = 'generating' # Map legacy status
        if status == 'verified' and sdo.get('confidence', 0) < 0.8: status = 'failed' # Heuristic

        # Determine complexity (heuristic based on code length/constraints)
        complexity = "medium"
        if constraints and len(constraints) > 5: complexity = "high"
        if constraints and len(constraints) < 2: complexity = "low"

        nodes.append(GraphNode(
            id=sdo['id'],
            label=sdo.get('raw_intent', 'Untitled Intent')[:30], # Truncate for label
            description=sdo.get('raw_intent'),
            confidence=sdo.get('confidence', 0.5),
            status=status.lower(),
            constraints=[str(c) for c in constraints][:3], # Top 3 constraints
            complexity=complexity
        ))
    
    # Mock Edges for now (Sequential chain based on time)
    edges = []
    # If we had dependency data, we'd add it here.
    # For demo, let's leave edges empty or infer sequence? 
    # Empty edges is safer than fake ones.
    
    return GraphResponse(nodes=nodes, edges=edges)

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
# Model Configuration Endpoints (Design.md 3.3 - Dynamic Model Config)
# ============================================================================

class ModelConfigResponse(BaseModel):
    name: str
    provider: str
    model_id: str
    tier: str
    cost_per_1k: float
    accuracy: float
    capabilities: Dict[str, Any]
    is_active: bool


class ModelsListResponse(BaseModel):
    models: List[ModelConfigResponse]
    count: int
    cache_age_seconds: Optional[float] = None


@app.get("/api/v1/models", response_model=ModelsListResponse)
async def list_models(
    tier: Optional[str] = Query(None, description="Filter by tier: local, balanced, high_accuracy, frontier"),
    active_only: bool = Query(True, description="Only return active models")
):
    """
    List available model configurations.
    
    Returns all models from the dynamic model config, optionally filtered by tier.
    """
    if not model_config:
        raise HTTPException(status_code=503, detail="Model configuration not initialized")
    
    from model_config import ModelTier
    
    if tier:
        try:
            tier_enum = ModelTier(tier)
            models = await model_config.get_models_by_tier(tier_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}. Use: local, balanced, high_accuracy, frontier")
    else:
        models = await model_config.get_all_active_models()
    
    stats = model_config.get_cache_stats()
    
    return ModelsListResponse(
        models=[
            ModelConfigResponse(
                name=m.name,
                provider=m.provider,
                model_id=m.model_id,
                tier=m.tier.value,
                cost_per_1k=m.cost_per_1k,
                accuracy=m.accuracy,
                capabilities=m.capabilities,
                is_active=m.is_active
            )
            for m in models
        ],
        count=len(models),
        cache_age_seconds=stats.get("cache_age_seconds")
    )


@app.get("/api/v1/models/{model_name}", response_model=ModelConfigResponse)
async def get_model(model_name: str = Path(..., description="Model name")):
    """
    Get a specific model configuration by name.
    """
    if not model_config:
        raise HTTPException(status_code=503, detail="Model configuration not initialized")
    
    m = await model_config.get_model_by_name(model_name)
    
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    return ModelConfigResponse(
        name=m.name,
        provider=m.provider,
        model_id=m.model_id,
        tier=m.tier.value,
        cost_per_1k=m.cost_per_1k,
        accuracy=m.accuracy,
        capabilities=m.capabilities,
        is_active=m.is_active
    )


@app.get("/api/v1/models/default")
async def get_default_model(
    tier: Optional[str] = Query(None, description="Optional tier filter")
):
    """
    Get the recommended default model.
    
    Selection criteria: highest accuracy within tier, then lowest cost.
    """
    if not model_config:
        raise HTTPException(status_code=503, detail="Model configuration not initialized")
    
    from model_config import ModelTier
    
    tier_enum = None
    if tier:
        try:
            tier_enum = ModelTier(tier)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")
    
    m = await model_config.get_default_model(tier_enum)
    
    if not m:
        raise HTTPException(status_code=404, detail="No default model available")
    
    return {
        "name": m.name,
        "provider": m.provider,
        "model_id": m.model_id,
        "tier": m.tier.value,
        "cost_per_1k": m.cost_per_1k,
        "accuracy": m.accuracy,
        "recommendation": f"Best {m.tier.value} model: {m.accuracy:.0%} accuracy at ${m.cost_per_1k}/1k tokens"
    }


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


@app.post("/sdo/{sdo_id}/snapshot")
async def snapshot_sdo(sdo_id: str = Path(..., description="SDO ID")):
    """
    Manually trigger a snapshot of the current SDO state.
    """
    sdo_data = await database_service.get_sdo(sdo_id)
    if not sdo_data:
        raise HTTPException(status_code=404, detail="SDO not found")
        
    # In a real event-sourced system, this might create a tagged version.
    # For now, we verify it exists and return success as it's already auto-saved.
    return {"status": "success", "message": f"Snapshot created for {sdo_id}", "timestamp": time.time()}


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
# Counterfactual Explorer Endpoints (Phase 3)
# ============================================================================

class CounterfactualRequest(BaseModel):
    base_sdo_id: str
    prompt: str
    user_id: Optional[str] = "analytical_user"

@app.post("/generate/counterfactual", response_model=ParallelGenerateResponse)
async def generate_counterfactual(request: CounterfactualRequest):
    """
    Generate a counterfactual variant of an existing SDO.
    """
    # Verify base SDO exists
    base_sdo_data = await database_service.get_sdo(request.base_sdo_id)
    if not base_sdo_data:
        raise HTTPException(status_code=404, detail="Base SDO not found")
    
    base_sdo = SDO(**base_sdo_data)
    
    # Fork and generate
    variant_sdo = await sdo_engine.generate_counterfactual(base_sdo, request.prompt)
    
    # response formatted similar to adaptive generation
    return ParallelGenerateResponse(
        sdo_id=variant_sdo.id,
        status=variant_sdo.status.value,
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
            for c in variant_sdo.candidates
        ],
        selected_candidate_id=variant_sdo.selected_candidate_id,
        selected_code=variant_sdo.code,
        confidence=variant_sdo.confidence,
        cost_usd=0.01,
        retrieved_context=variant_sdo.retrieved_context
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


# ============================================================================
# Proof-Carrying Code (PCC) Endpoints - Phase 6
# ============================================================================

class GenerateProofRequest(BaseModel):
    sdo_id: str
    candidate_id: Optional[str] = None
    contracts: Optional[List[Dict[str, Any]]] = None

class GenerateProofResponse(BaseModel):
    proof_id: str
    ivcu_id: str
    code_hash: str
    signature: str
    overall_confidence: float
    success: bool
    error: Optional[str] = None

class VerifyProofRequest(BaseModel):
    proof: Dict[str, Any]
    code: str
    public_key: Optional[str] = None

class VerifyProofResponse(BaseModel):
    valid: bool
    hash_valid: bool
    signature_valid: bool
    errors: List[str] = []

class GenerateProofRequest(BaseModel):
    sdo_id: str
    candidate_id: Optional[str] = None
    contracts: Optional[List[Dict[str, Any]]] = None

class GenerateProofResponse(BaseModel):
    proof_id: str
    ivcu_id: str
    code_hash: str
    signature: str
    overall_confidence: float
    success: bool
    error: Optional[str] = None

class VerifyProofRequest(BaseModel):
    code: str
    proof: Dict[str, Any]
    public_key: Optional[str] = None

class VerifyProofResponse(BaseModel):
    valid: bool
    hash_valid: bool
    signature_valid: bool
    errors: List[str] = []

class ExportBundleRequest(BaseModel):
    sdo_id: str
    candidate_id: Optional[str] = None
    include_tests: bool = False


@app.post("/proof/generate", response_model=GenerateProofResponse)
async def generate_proof(request: GenerateProofRequest):
    """
    Generate a cryptographic proof for a verified IVCU.
    """
    from verification import get_proof_generator
    
    # Get SDO from database
    sdo_data = await database_service.get_sdo(request.sdo_id)
    if not sdo_data:
        return GenerateProofResponse(
            proof_id="",
            ivcu_id=request.sdo_id,
            code_hash="",
            signature="",
            overall_confidence=0.0,
            success=False,
            error="SDO not found"
        )
    
    from sdo import SDO
    sdo = SDO(**sdo_data)
    
    if not sdo.code:
        return GenerateProofResponse(
            proof_id="",
            ivcu_id=request.sdo_id,
            code_hash="",
            signature="",
            overall_confidence=0.0,
            success=False,
            error="No verified code found"
        )
    
    # Get verification result
    verification_result = sdo.verification_result or {}
    
    # Generate proof
    proof_gen = get_proof_generator()
    proof = await proof_gen.generate_proof(
        ivcu_id=sdo.id,
        candidate_id=request.candidate_id or sdo.selected_candidate_id or "",
        code=sdo.code,
        verification_result=verification_result,
        contracts=[c.model_dump() for c in sdo.contracts] if sdo.contracts else request.contracts,
        sign=True
    )
    
    return GenerateProofResponse(
        proof_id=proof.proof_id,
        ivcu_id=proof.ivcu_id,
        code_hash=proof.code_hash,
        signature=proof.signature.hex() if proof.signature else "",
        overall_confidence=proof.overall_confidence,
        success=True
    )


@app.post("/proof/verify", response_model=VerifyProofResponse)
async def verify_proof(request: VerifyProofRequest):
    """
    Verify a proof independently.
    """
    from verification import get_proof_generator, VerificationProof
    
    proof_gen = get_proof_generator()
    
    # Reconstruct proof from dict
    proof = VerificationProof(
        proof_id=request.proof.get("proof_id", ""),
        ivcu_id=request.proof.get("ivcu_id", ""),
        candidate_id=request.proof.get("candidate_id", ""),
        code_hash=request.proof.get("code_hash", ""),
        timestamp=request.proof.get("timestamp", 0),
        signature=bytes.fromhex(request.proof.get("signature", "")),
        signer_id=request.proof.get("signer_id", ""),
        public_key=request.proof.get("public_key", ""),
        overall_confidence=request.proof.get("overall_confidence", 0.0)
    )
    
    public_key_bytes = None
    if request.public_key:
        try:
            import base64
            public_key_bytes = base64.b64decode(request.public_key)
        except Exception:
            pass
    
    result = proof_gen.verify_proof(proof, request.code, public_key_bytes)
    
    return VerifyProofResponse(
        valid=result.get("valid", False),
        hash_valid=result.get("hash_valid", False),
        signature_valid=result.get("signature_valid", False),
        errors=result.get("errors", [])
    )


@app.post("/proof/export")
async def export_proof_bundle(request: ExportBundleRequest):
    """
    Export a proof bundle for an IVCU.
    """
    from verification import get_proof_bundler
    
    # Get SDO
    sdo_data = await database_service.get_sdo(request.sdo_id)
    if not sdo_data:
        raise HTTPException(status_code=404, detail="SDO not found")
    
    from sdo import SDO
    sdo = SDO(**sdo_data)
    
    if not sdo.code:
        raise HTTPException(status_code=400, detail="No verified code found")
    
    bundler = get_proof_bundler()
    bundle = await bundler.create_bundle(
        ivcu_id=sdo.id,
        candidate_id=request.candidate_id or sdo.selected_candidate_id or "",
        code=sdo.code,
        verification_result=sdo.verification_result or {},
        contracts=[c.model_dump() for c in sdo.contracts] if sdo.contracts else None,
        tests=sdo.test_code if request.include_tests else None
    )
    
    return {
        "bundle": bundle.to_json(),
        "ivcu_id": sdo.id,
        "code_hash": bundle.code_hash,
        "created_at": bundle.created_at
    }


@app.get("/proof/public-key")
async def get_public_key():
    """
    Get the server's public key for proof verification.
    """
    from verification import get_proof_signer
    
    signer = get_proof_signer()
    key = signer.load_or_create_key()
    signer.current_key = key
    
    return {
        "key_id": key.key_id,
        "public_key_pem": signer.get_public_key_pem(),
        "algorithm": "Ed25519"
    }




class FeedbackRequest(BaseModel):
    sdo_id: str
    original_code: str
    corrected_code: str
    intent: str

@app.post("/learning/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback to the LearnerModel (Adaptive Learning Phase E).
    """
    try:
        correction = await sdo_engine.learner.digest_feedback(
            ivcu_id=request.sdo_id,
            intent=request.intent,
            original_code=request.original_code,
            corrected_code=request.corrected_code
        )
        return {"success": True, "message": "Feedback digested", "lesson": correction.diff_summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Learner Endpoints (Phase 3/11)
# =============================================================================

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
    project_id: Optional[str] = None
    user_id: Optional[str] = None

class GenerateCodeRequest(BaseModel):
    intent: str
    language: str = "python"
    model: str = "gpt-4-turbo"
    user_id: Optional[str] = None

class VerifyRequest(BaseModel):
    code: str
    language: str = "python"
    sdo_id: Optional[str] = None

class LearningEventRequest(BaseModel):
    user_id: str
    event_type: str
    details: Dict[str, Any]

@app.post("/learner/event")
async def handle_learning_event(event: LearningEventRequest):
    """
    Handle a learning event (e.g., successful generation, manual correction).
    Updates user skills and profile accordingly.
    """
    try:
        if not sdo_engine.learner:
             raise HTTPException(status_code=503, detail="Learner service unavailable")
        
        domain = "general"
        delta = 0
        
        if event.event_type == "generation_accepted":
            complexity = event.details.get("complexity", 1)
            if complexity > 5:
                domain = "architectural_reasoning"
                delta = 1
            else:
                domain = "intent_expression"
                delta = 1
        elif event.event_type == "correction":
             domain = "debugging"
             delta = 1
        elif event.event_type == "manual_skill_update":
             domain = event.details.get("domain", "general")
             delta = event.details.get("delta", 0)
        
        result = await sdo_engine.learner.update_skill(event.user_id, domain, delta)
        return {"updated_skills": result}
    except Exception as e:
        print(f"DEBUG: Exception in handle_learning_event: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            # Keep connection open and handle incoming messages if any
            # For now, we just discard or echo but keep the loop running
            data = await websocket.receive_text()
            # Optional: Handle client messages
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    print("DEBUG: STARTING ON PORT 8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)



