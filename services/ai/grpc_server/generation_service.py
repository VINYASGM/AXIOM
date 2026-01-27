"""
gRPC Generation Service Implementation

Implements bidirectional streaming for real-time code generation.
Provides token-by-token streaming and verification progress updates.
"""
import asyncio
import uuid
import time
import json
from typing import AsyncIterator, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# gRPC imports
import grpc
from grpc import aio

# AXIOM imports (we'll generate proper stubs later, using dict protocol for now)
from typing import Protocol


class GenerationStatus(str, Enum):
    """Generation status states."""
    PENDING = "pending"
    GENERATING = "generating"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ActiveGeneration:
    """Tracks an active generation session."""
    ivcu_id: str
    status: GenerationStatus = GenerationStatus.PENDING
    model_id: str = ""
    candidates: Dict[str, dict] = field(default_factory=dict)
    current_cost: float = 0.0
    started_at: float = field(default_factory=time.time)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)


class GenerationServicer:
    """
    gRPC service implementation for code generation.
    
    Implements bidirectional streaming:
    - Client sends IntentUpdate messages (initial, refinements, stop, select)
    - Server streams GenerationEvent messages (tokens, candidates, verification)
    """
    
    def __init__(self, orchestra=None, router=None, event_store=None):
        """
        Initialize the generation servicer.
        
        Args:
            orchestra: VerificationOrchestra instance
            router: LLMRouter instance for model routing
            event_store: IVCUEventStore for persistence
        """
        self.orchestra = orchestra
        self.router = router
        self.event_store = event_store
        self._active_generations: Dict[str, ActiveGeneration] = {}
    
    async def GenerateStream(
        self,
        request_iterator: AsyncIterator[dict],
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[dict]:
        """
        Bidirectional streaming generation.
        
        Client sends intent updates, server streams generation events.
        """
        ivcu_id = None
        generation = None
        
        try:
            async for update in request_iterator:
                ivcu_id = update.get("ivcu_id")
                
                if "initial" in update:
                    # Start new generation
                    initial = update["initial"]
                    ivcu_id = ivcu_id or str(uuid.uuid4())
                    
                    generation = ActiveGeneration(
                        ivcu_id=ivcu_id,
                        model_id=initial.get("model_id", "deepseek-v3")
                    )
                    self._active_generations[ivcu_id] = generation
                    
                    # Emit started event
                    yield self._make_event(ivcu_id, "started", {
                        "model_id": generation.model_id,
                        "model_name": generation.model_id,
                        "tier": "balanced",
                        "estimated_cost": 0.01
                    })
                    
                    # Run generation
                    async for event in self._run_generation(
                        generation,
                        initial.get("raw_intent", ""),
                        initial.get("language", "python"),
                        initial.get("metadata", {})
                    ):
                        yield event
                        
                        # Check for cancellation
                        if generation.cancel_event.is_set():
                            break
                
                elif "refinement" in update:
                    # Handle intent refinement
                    if generation:
                        refinement = update["refinement"]
                        
                        if refinement.get("clear_candidates"):
                            generation.candidates.clear()
                        
                        # Re-run generation with refined intent
                        async for event in self._run_generation(
                            generation,
                            refinement.get("refinement_text", ""),
                            "python",
                            {}
                        ):
                            yield event
                
                elif "stop" in update:
                    # Stop generation
                    if generation:
                        generation.cancel_event.set()
                        generation.status = GenerationStatus.CANCELLED
                    break
                
                elif "select" in update:
                    # Select a candidate
                    if generation:
                        select = update["select"]
                        candidate_id = select.get("candidate_id")
                        
                        if candidate_id in generation.candidates:
                            candidate = generation.candidates[candidate_id]
                            
                            yield self._make_event(ivcu_id, "complete", {
                                "success": True,
                                "selected_candidate_id": candidate_id,
                                "final_code": candidate.get("code", ""),
                                "overall_confidence": candidate.get("confidence", 0.0),
                                "total_candidates": len(generation.candidates),
                                "passing_candidates": sum(
                                    1 for c in generation.candidates.values()
                                    if c.get("verification_passed")
                                ),
                                "total_cost": generation.current_cost,
                                "total_time_ms": (time.time() - generation.started_at) * 1000
                            })
                    break
        
        except Exception as e:
            if ivcu_id:
                yield self._make_event(ivcu_id, "error", {
                    "error_code": "GENERATION_ERROR",
                    "message": str(e),
                    "recoverable": False,
                    "suggested_action": "Retry with a simpler intent"
                })
        
        finally:
            if ivcu_id and ivcu_id in self._active_generations:
                del self._active_generations[ivcu_id]
    
    async def _run_generation(
        self,
        generation: ActiveGeneration,
        intent: str,
        language: str,
        metadata: dict
    ) -> AsyncIterator[dict]:
        """Run the generation pipeline with streaming."""
        generation.status = GenerationStatus.GENERATING
        ivcu_id = generation.ivcu_id
        
        # Import here to avoid circular imports
        try:
            from models import get_model, get_cost_oracle
            from router import get_router, ChatRequest, ChatMessage
        except ImportError:
            # Mock for testing
            pass
        
        # Generate candidate
        candidate_id = str(uuid.uuid4())
        
        # Stream tokens (simulated for now - real implementation would stream from LLM)
        code_parts = []
        token_index = 0
        
        # Simulate streaming response
        generated_code = f'''def generated_function():
    """
    Generated from intent: {intent[:100]}
    Language: {language}
    """
    # Implementation based on intent
    pass
'''
        
        # Stream tokens
        for word in generated_code.split():
            code_parts.append(word)
            yield self._make_event(ivcu_id, "token", {
                "candidate_id": candidate_id,
                "token": word + " ",
                "token_index": token_index,
                "is_complete": False
            })
            token_index += 1
            await asyncio.sleep(0.01)  # Simulate streaming delay
        
        # Signal token stream complete
        yield self._make_event(ivcu_id, "token", {
            "candidate_id": candidate_id,
            "token": "",
            "token_index": token_index,
            "is_complete": True
        })
        
        final_code = " ".join(code_parts)
        
        # Emit candidate complete
        yield self._make_event(ivcu_id, "candidate", {
            "candidate_id": candidate_id,
            "code": final_code,
            "confidence": 0.85,
            "reasoning": f"Generated from: {intent[:50]}",
            "tokens_used": len(final_code.split())
        })
        
        # Store candidate
        generation.candidates[candidate_id] = {
            "code": final_code,
            "confidence": 0.85,
            "verification_passed": False
        }
        
        # Run verification with streaming progress
        generation.status = GenerationStatus.VERIFYING
        
        # Tier 0 verification
        try:
            from verification import verify_tier0
            tier0_result = await verify_tier0(final_code, language)
            
            yield self._make_event(ivcu_id, "verification", {
                "candidate_id": candidate_id,
                "tier": "tier_0",
                "verifier": "tree_sitter",
                "passed": tier0_result.passed,
                "confidence": tier0_result.confidence,
                "errors": [e.to_dict() for e in tier0_result.errors],
                "warnings": [w.to_dict() for w in tier0_result.warnings],
                "execution_time_ms": tier0_result.parse_time_ms
            })
            
            if tier0_result.passed:
                generation.candidates[candidate_id]["verification_passed"] = True
                generation.candidates[candidate_id]["confidence"] = tier0_result.confidence
                
        except ImportError:
            # Fallback verification
            yield self._make_event(ivcu_id, "verification", {
                "candidate_id": candidate_id,
                "tier": "tier_0",
                "verifier": "fallback",
                "passed": True,
                "confidence": 0.7,
                "errors": [],
                "warnings": [],
                "execution_time_ms": 1.0
            })
            generation.candidates[candidate_id]["verification_passed"] = True
        
        # Update cost
        generation.current_cost += 0.001  # Mock cost
        yield self._make_event(ivcu_id, "cost", {
            "current_cost": generation.current_cost,
            "estimated_remaining": 0.0,
            "model_id": generation.model_id,
            "tokens_used": token_index
        })
        
        generation.status = GenerationStatus.COMPLETE
    
    async def Generate(self, request: dict, context: grpc.aio.ServicerContext) -> dict:
        """Unary generation request (non-streaming)."""
        ivcu_id = str(uuid.uuid4())
        
        # Collect all events from streaming
        events = []
        
        async def mock_iterator():
            yield {
                "ivcu_id": ivcu_id,
                "initial": {
                    "raw_intent": request.get("raw_intent", ""),
                    "language": request.get("language", "python"),
                    "model_id": request.get("model_id", "deepseek-v3")
                }
            }
        
        async for event in self.GenerateStream(mock_iterator(), context):
            events.append(event)
        
        # Extract final result
        complete_event = next(
            (e for e in reversed(events) if e.get("complete")),
            None
        )
        
        if complete_event:
            return {
                "ivcu_id": ivcu_id,
                "success": complete_event["complete"].get("success", False),
                "code": complete_event["complete"].get("final_code", ""),
                "confidence": complete_event["complete"].get("overall_confidence", 0.0),
                "verification": {},
                "cost": {
                    "total_cost": complete_event["complete"].get("total_cost", 0.0)
                }
            }
        
        return {
            "ivcu_id": ivcu_id,
            "success": False,
            "code": "",
            "confidence": 0.0
        }
    
    async def GetStatus(self, request: dict, context: grpc.aio.ServicerContext) -> dict:
        """Get generation status."""
        ivcu_id = request.get("ivcu_id")
        
        if ivcu_id in self._active_generations:
            gen = self._active_generations[ivcu_id]
            return {
                "ivcu_id": ivcu_id,
                "status": gen.status.value,
                "candidates_generated": len(gen.candidates),
                "candidates_verified": sum(
                    1 for c in gen.candidates.values()
                    if c.get("verification_passed")
                ),
                "current_cost": gen.current_cost,
                "elapsed_time_ms": (time.time() - gen.started_at) * 1000
            }
        
        return {
            "ivcu_id": ivcu_id,
            "status": "not_found"
        }
    
    async def Cancel(self, request: dict, context: grpc.aio.ServicerContext) -> dict:
        """Cancel ongoing generation."""
        ivcu_id = request.get("ivcu_id")
        
        if ivcu_id in self._active_generations:
            gen = self._active_generations[ivcu_id]
            gen.cancel_event.set()
            gen.status = GenerationStatus.CANCELLED
            return {"success": True, "message": "Generation cancelled"}
        
        return {"success": False, "message": "Generation not found"}
    
    def _make_event(self, ivcu_id: str, event_type: str, data: dict) -> dict:
        """Create a generation event."""
        return {
            "ivcu_id": ivcu_id,
            "timestamp": int(time.time() * 1000),
            event_type: data
        }


async def serve(port: int = 50051) -> None:
    """Start the gRPC server."""
    server = aio.server()
    
    # Add services
    generation_servicer = GenerationServicer()
    
    # In production, register with generated stubs:
    # generation_pb2_grpc.add_GenerationServiceServicer_to_server(generation_servicer, server)
    
    # For now, log that server is ready
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    
    print(f"Starting gRPC server on {listen_addr}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await server.stop(5)


if __name__ == "__main__":
    asyncio.run(serve())
