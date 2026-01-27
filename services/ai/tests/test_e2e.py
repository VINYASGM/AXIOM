"""
End-to-End Integration Tests for AXIOM AI Services

Tests the full pipeline from intent to verified code.
"""
import pytest
import asyncio
import time
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
import sys

sys.path.insert(0, '..')

# Test configuration
TIMEOUT_SECONDS = 30


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_router():
    """Mock LLM router for testing."""
    router = MagicMock()
    router.route.return_value = AsyncMock()
    return router


@pytest.fixture
def mock_event_store():
    """Mock event store for testing."""
    from ivcu_events import IVCUEventStore, IVCUStateProjector
    
    store = MagicMock(spec=IVCUEventStore)
    store.append = AsyncMock(return_value="event-1")
    store.get_events = AsyncMock(return_value=[])
    store.get_state = AsyncMock(return_value=MagicMock(
        ivcu_id="test-ivcu",
        version=0,
        intent="",
        status="new"
    ))
    return store


@pytest.fixture
def mock_verification_orchestra():
    """Mock verification orchestra."""
    orchestra = MagicMock()
    
    async def mock_verify(code, language, contracts=None):
        from verification.orchestra import VerificationResult
        return VerificationResult(
            passed=True,
            overall_confidence=0.92,
            tier0_result=MagicMock(passed=True, confidence=0.95),
            tier1_result=MagicMock(passed=True, confidence=0.90),
            tier2_result=None,
            tier3_result=None,
            total_time_ms=150.0
        )
    
    orchestra.verify = mock_verify
    return orchestra


# ============================================================================
# GENERATION PIPELINE TESTS
# ============================================================================

class TestGenerationPipeline:
    """Test the full generation pipeline."""
    
    @pytest.mark.asyncio
    async def test_simple_generation_flow(self, mock_router, mock_event_store):
        """Test a simple generation from intent to code."""
        from grpc_server.generation_service import GenerationServicer
        
        servicer = GenerationServicer(
            orchestra=None,
            router=mock_router,
            event_store=mock_event_store
        )
        
        # Create mock context
        context = MagicMock()
        
        # Create request iterator
        async def request_iterator():
            yield {
                "ivcu_id": "test-ivcu-1",
                "initial": {
                    "raw_intent": "Create a function to reverse a string",
                    "language": "python",
                    "model_id": "deepseek-v3"
                }
            }
            # Select first candidate
            yield {
                "ivcu_id": "test-ivcu-1",
                "select": {
                    "candidate_id": None  # Will be filled by first candidate
                }
            }
        
        # Collect events
        events = []
        candidate_id = None
        
        async for event in servicer.GenerateStream(request_iterator(), context):
            events.append(event)
            
            # Capture candidate ID
            if "candidate" in event:
                candidate_id = event["candidate"]["candidate_id"]
        
        # Verify events received
        assert len(events) > 0
        
        # Check we got a started event
        started_events = [e for e in events if "started" in e]
        assert len(started_events) >= 1
        
        # Check we got token events
        token_events = [e for e in events if "token" in e]
        assert len(token_events) > 0
        
        # Check we got a candidate
        candidate_events = [e for e in events if "candidate" in e]
        assert len(candidate_events) >= 1
        
        # Check we got verification
        verification_events = [e for e in events if "verification" in e]
        assert len(verification_events) >= 1
    
    @pytest.mark.asyncio
    async def test_generation_with_contracts(self, mock_router, mock_event_store):
        """Test generation with input contracts."""
        from grpc_server.generation_service import GenerationServicer
        
        servicer = GenerationServicer(
            orchestra=None,
            router=mock_router,
            event_store=mock_event_store
        )
        
        # Unary request with contracts
        result = await servicer.Generate({
            "raw_intent": "Create a sorting function",
            "language": "python",
            "contracts": [
                {"type": "precondition", "expression": "len(items) > 0"},
                {"type": "postcondition", "expression": "is_sorted(result)"}
            ]
        }, MagicMock())
        
        assert "ivcu_id" in result
        assert result.get("success") is not None
    
    @pytest.mark.asyncio
    async def test_generation_cancellation(self, mock_router, mock_event_store):
        """Test that generation can be cancelled."""
        from grpc_server.generation_service import GenerationServicer
        
        servicer = GenerationServicer()
        
        # Start generation
        async def slow_request_iterator():
            yield {
                "ivcu_id": "test-cancel",
                "initial": {
                    "raw_intent": "Complex task that takes a while",
                    "language": "python"
                }
            }
            await asyncio.sleep(0.5)  # Simulate delay before stop
            yield {
                "ivcu_id": "test-cancel",
                "stop": {"reason": "User cancelled"}
            }
        
        events = []
        async for event in servicer.GenerateStream(slow_request_iterator(), MagicMock()):
            events.append(event)
        
        # Should have some events but stopped early
        assert len(events) > 0


# ============================================================================
# VERIFICATION PIPELINE TESTS
# ============================================================================

class TestVerificationPipeline:
    """Test the full verification pipeline."""
    
    @pytest.mark.asyncio
    async def test_tier0_quick_verify(self):
        """Test quick Tier 0 verification."""
        from grpc_server.verification_service import VerificationServicer
        
        servicer = VerificationServicer()
        
        code = """
def hello(name):
    return f"Hello, {name}!"
"""
        
        result = await servicer.QuickVerify({
            "code": code,
            "language": "python"
        }, MagicMock())
        
        assert "passed" in result
        assert "confidence" in result
        assert "parse_time_ms" in result
        
        # Tier 0 should be fast
        assert result["parse_time_ms"] < 100  # Less than 100ms
    
    @pytest.mark.asyncio
    async def test_tier0_syntax_error_detection(self):
        """Test that Tier 0 catches syntax errors."""
        from grpc_server.verification_service import VerificationServicer
        
        servicer = VerificationServicer()
        
        # Invalid Python syntax
        code = """
def broken_function(
    return "missing closing paren"
"""
        
        result = await servicer.QuickVerify({
            "code": code,
            "language": "python"
        }, MagicMock())
        
        assert result["passed"] == False
        assert len(result.get("errors", [])) > 0
    
    @pytest.mark.asyncio
    async def test_streaming_verification_progress(self):
        """Test streaming verification with progress updates."""
        from grpc_server.verification_service import VerificationServicer
        
        servicer = VerificationServicer()
        
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        
        events = []
        async for event in servicer.VerifyStream({
            "ivcu_id": "test-verify",
            "candidate_id": "cand-1",
            "code": code,
            "language": "python",
            "options": {
                "run_tier0": True,
                "run_tier1": True,
                "run_tier2": False,
                "run_tier3": False
            }
        }, MagicMock()):
            events.append(event)
        
        # Should have tier events
        tier_started = [e for e in events if "tier_started" in e]
        tier_complete = [e for e in events if "tier_complete" in e]
        
        assert len(tier_started) >= 1
        assert len(tier_complete) >= 1
        
        # Should have final complete event
        complete_events = [e for e in events if "complete" in e]
        assert len(complete_events) == 1


# ============================================================================
# MEMORY SERVICE TESTS
# ============================================================================

class TestMemoryService:
    """Test GraphRAG memory service."""
    
    @pytest.mark.asyncio
    async def test_store_and_search(self):
        """Test storing and searching memory nodes."""
        from grpc_server.memory_service import MemoryServicer
        
        servicer = MemoryServicer()
        
        # Store a node
        store_result = await servicer.Store({
            "content": "A function that sorts a list of integers",
            "node_type": "function_description",
            "tier": 2,  # PROJECT tier
            "metadata": {"language": "python"}
        }, MagicMock())
        
        assert store_result["success"] == True
        assert "node_id" in store_result
        
        # Search for it (without real vector/graph DB, will return empty)
        search_result = await servicer.Search({
            "query": "sorting integers",
            "limit": 10
        }, MagicMock())
        
        assert "primary_nodes" in search_result
        assert "query_time_ms" in search_result
    
    @pytest.mark.asyncio
    async def test_impact_analysis(self):
        """Test impact analysis endpoint."""
        from grpc_server.memory_service import MemoryServicer
        
        servicer = MemoryServicer()
        
        impact = await servicer.GetImpact({
            "node_id": "test-node",
            "max_depth": 3
        }, MagicMock())
        
        assert "source_node_id" in impact
        assert "affected_count" in impact
        assert "impact_severity" in impact


# ============================================================================
# EVENT SOURCING INTEGRATION TESTS
# ============================================================================

class TestEventSourcingIntegration:
    """Test event sourcing with real projections."""
    
    def test_full_ivcu_lifecycle(self):
        """Test complete IVCU lifecycle through events."""
        from ivcu_events import (
            IVCUEventType,
            IVCUStateProjector,
            create_event
        )
        
        projector = IVCUStateProjector()
        ivcu_id = "test-lifecycle"
        
        # Create event sequence
        events = [
            create_event(ivcu_id, IVCUEventType.INTENT_CREATED, {
                "raw_intent": "Create a calculator",
                "language": "python",
                "model_id": "deepseek-v3"
            }),
            create_event(ivcu_id, IVCUEventType.CONTRACT_ADDED, {
                "contract_type": "precondition",
                "expression": "isinstance(a, (int, float))"
            }),
            create_event(ivcu_id, IVCUEventType.CANDIDATE_GENERATED, {
                "candidate_id": "cand-1",
                "code": "def add(a, b): return a + b",
                "model_id": "deepseek-v3",
                "tokens_used": 100,
                "cost": 0.001
            }),
            create_event(ivcu_id, IVCUEventType.VERIFICATION_COMPLETED, {
                "candidate_id": "cand-1",
                "tier": "tier_1",
                "passed": True,
                "confidence": 0.92
            }),
            create_event(ivcu_id, IVCUEventType.CANDIDATE_SELECTED, {
                "candidate_id": "cand-1"
            }),
            create_event(ivcu_id, IVCUEventType.IVCU_DEPLOYED, {
                "candidate_id": "cand-1",
                "deployment_target": "project"
            })
        ]
        
        # Project final state
        state = projector.project(events)
        
        assert state.ivcu_id == ivcu_id
        assert state.intent == "Create a calculator"
        assert len(state.contracts) == 1
        assert len(state.candidates) == 1
        assert state.selected_candidate_id == "cand-1"
        assert state.status == "deployed"
        assert state.version == 6
    
    def test_undo_to_previous_state(self):
        """Test undo by projecting to earlier version."""
        from ivcu_events import (
            IVCUEventType,
            IVCUStateProjector,
            create_event
        )
        
        projector = IVCUStateProjector()
        ivcu_id = "test-undo"
        
        events = [
            create_event(ivcu_id, IVCUEventType.INTENT_CREATED, {
                "raw_intent": "Version 1"
            }),
            create_event(ivcu_id, IVCUEventType.INTENT_REFINED, {
                "refined_intent": "Version 2"
            }),
            create_event(ivcu_id, IVCUEventType.INTENT_REFINED, {
                "refined_intent": "Version 3"
            }),
        ]
        
        # Current state
        current = projector.project(events)
        assert current.intent == "Version 3"
        
        # Undo to version 2
        v2 = projector.project(events, up_to_version=2)
        assert v2.intent == "Version 2"
        
        # Undo to version 1
        v1 = projector.project(events, up_to_version=1)
        assert v1.intent == "Version 1"


# ============================================================================
# MODEL ROUTING INTEGRATION TESTS
# ============================================================================

class TestModelRoutingIntegration:
    """Test model routing with cost oracle."""
    
    def test_model_selection_by_complexity(self):
        """Test that models are selected appropriately by task complexity."""
        from models.catalog import get_recommended_model, TaskType, ModelTier
        
        # Simple task -> lower tier
        simple_model = get_recommended_model(TaskType.SIMPLE)
        assert simple_model.tier in [ModelTier.LOCAL, ModelTier.BALANCED]
        
        # Complex debugging -> higher tier
        debug_model = get_recommended_model(TaskType.COMPLEX_DEBUG)
        assert debug_model.tier in [ModelTier.HIGH_ACCURACY, ModelTier.FRONTIER]
        
        # Novel problem -> frontier
        novel_model = get_recommended_model(TaskType.NOVEL_PROBLEM)
        assert novel_model.tier == ModelTier.FRONTIER
    
    def test_cost_oracle_accuracy_first(self):
        """Test that cost oracle recommends based on effective cost."""
        from models.cost_oracle import CostOracle
        from models.catalog import get_model
        
        oracle = CostOracle()
        
        # Get estimates for two models
        high_accuracy = oracle.estimate_cost(
            model_id="claude-sonnet-4",
            intent_text="Complex debugging task",
            complexity="complex"
        )
        
        lower_accuracy = oracle.estimate_cost(
            model_id="gpt-4o-mini",
            intent_text="Complex debugging task",
            complexity="complex"
        )
        
        # High accuracy model should have lower retry multiplier
        assert high_accuracy.retry_multiplier < lower_accuracy.retry_multiplier
    
    def test_tier_upgrade_on_failure(self):
        """Test model tier upgrade path."""
        from models.catalog import get_model, get_next_tier_model, ModelTier
        
        # Start with balanced tier
        current = get_model("deepseek-v3")
        assert current.tier == ModelTier.BALANCED
        
        # Get next tier
        upgraded = get_next_tier_model(current.id)
        assert upgraded is not None
        
        # Should be same or higher tier
        tier_order = [ModelTier.LOCAL, ModelTier.BALANCED, ModelTier.HIGH_ACCURACY, ModelTier.FRONTIER]
        assert tier_order.index(upgraded.tier) >= tier_order.index(current.tier)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance benchmarks for critical paths."""
    
    @pytest.mark.asyncio
    async def test_tier0_performance(self):
        """Test that Tier 0 verification is fast (<10ms target)."""
        from grpc_server.verification_service import VerificationServicer
        
        servicer = VerificationServicer()
        
        # Test code of varying sizes
        small_code = "def f(): pass"
        medium_code = "\n".join([f"def func_{i}(): pass" for i in range(50)])
        large_code = "\n".join([f"def func_{i}(): return {i} * 2" for i in range(200)])
        
        for name, code in [("small", small_code), ("medium", medium_code), ("large", large_code)]:
            start = time.time()
            result = await servicer.QuickVerify({
                "code": code,
                "language": "python"
            }, MagicMock())
            elapsed = (time.time() - start) * 1000
            
            print(f"Tier 0 ({name}): {elapsed:.2f}ms")
            
            # Target is <10ms, but allow some slack for test environment
            assert elapsed < 100, f"Tier 0 too slow for {name} code: {elapsed}ms"
    
    def test_state_projection_performance(self):
        """Test that state projection is fast even with many events."""
        from ivcu_events import IVCUEventType, IVCUStateProjector, create_event
        
        projector = IVCUStateProjector()
        ivcu_id = "perf-test"
        
        # Create many events
        events = []
        for i in range(100):
            events.append(create_event(ivcu_id, IVCUEventType.INTENT_REFINED, {
                "refined_intent": f"Refinement {i}"
            }))
        
        start = time.time()
        state = projector.project(events)
        elapsed = (time.time() - start) * 1000
        
        print(f"Projection of 100 events: {elapsed:.2f}ms")
        
        assert elapsed < 50, f"Projection too slow: {elapsed}ms"
        assert state.version == 100


# Run with: pytest tests/test_e2e.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
