"""
Tests for Event Sourcing System

Tests event store, state projection, and undo/redo functionality.
"""
import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Import event sourcing components
import sys
sys.path.insert(0, '.')

from ivcu_events import (
    IVCUEventType,
    IVCUEvent,
    IVCUState,
    IVCUStateProjector,
    IVCUEventStore,
    create_event
)


class TestIVCUEvent:
    """Test event creation and serialization."""
    
    def test_create_intent_created_event(self):
        """Test creating an intent created event."""
        event = create_event(
            ivcu_id="test-ivcu-1",
            event_type=IVCUEventType.INTENT_CREATED,
            data={
                "raw_intent": "Create a function to sort a list",
                "language": "python",
                "model_id": "deepseek-v3"
            },
            user_id="user-1"
        )
        
        assert event.ivcu_id == "test-ivcu-1"
        assert event.event_type == IVCUEventType.INTENT_CREATED
        assert event.data["raw_intent"] == "Create a function to sort a list"
        assert event.user_id == "user-1"
        assert event.version == 1
    
    def test_event_to_dict(self):
        """Test event dictionary serialization."""
        event = create_event(
            ivcu_id="test-ivcu-2",
            event_type=IVCUEventType.CONTRACT_ADDED,
            data={
                "contract_type": "precondition",
                "expression": "len(items) > 0"
            }
        )
        
        event_dict = event.to_dict()
        
        assert "id" in event_dict
        assert event_dict["ivcu_id"] == "test-ivcu-2"
        assert event_dict["event_type"] == "contract_added"
        assert "timestamp" in event_dict


class TestIVCUStateProjector:
    """Test state projection from events."""
    
    def test_project_intent_created(self):
        """Test projecting intent created event."""
        projector = IVCUStateProjector()
        
        event = create_event(
            ivcu_id="test-ivcu",
            event_type=IVCUEventType.INTENT_CREATED,
            data={
                "raw_intent": "Sort a list",
                "language": "python",
                "model_id": "claude-sonnet"
            }
        )
        
        state = projector.project([event])
        
        assert state.ivcu_id == "test-ivcu"
        assert state.intent == "Sort a list"
        assert state.language == "python"
        assert state.model_id == "claude-sonnet"
        assert state.status == "intent_created"
        assert state.version == 1
    
    def test_project_contract_added(self):
        """Test projecting contract added event."""
        projector = IVCUStateProjector()
        
        events = [
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.INTENT_CREATED,
                data={"raw_intent": "Sort", "language": "python"}
            ),
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.CONTRACT_ADDED,
                data={
                    "contract_type": "precondition",
                    "expression": "items is not None"
                }
            )
        ]
        
        state = projector.project(events)
        
        assert len(state.contracts) == 1
        assert state.contracts[0]["contract_type"] == "precondition"
        assert state.version == 2
    
    def test_project_candidate_generated(self):
        """Test projecting candidate generation."""
        projector = IVCUStateProjector()
        
        events = [
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.INTENT_CREATED,
                data={"raw_intent": "Sort", "language": "python"}
            ),
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.CANDIDATE_GENERATED,
                data={
                    "candidate_id": "cand-1",
                    "code": "def sort(items): return sorted(items)",
                    "model_id": "deepseek-v3",
                    "tokens_used": 50,
                    "cost": 0.001
                }
            )
        ]
        
        state = projector.project(events)
        
        assert len(state.candidates) == 1
        assert "cand-1" in state.candidates
        assert state.candidates["cand-1"]["code"] == "def sort(items): return sorted(items)"
        assert state.total_cost == Decimal("0.001")
    
    def test_project_verification_completed(self):
        """Test projecting verification completion."""
        projector = IVCUStateProjector()
        
        events = [
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.INTENT_CREATED,
                data={"raw_intent": "Sort", "language": "python"}
            ),
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.CANDIDATE_GENERATED,
                data={
                    "candidate_id": "cand-1",
                    "code": "def sort(items): return sorted(items)",
                    "model_id": "deepseek-v3"
                }
            ),
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.VERIFICATION_COMPLETED,
                data={
                    "candidate_id": "cand-1",
                    "tier": "tier_1",
                    "passed": True,
                    "confidence": 0.95
                }
            )
        ]
        
        state = projector.project(events)
        
        assert state.candidates["cand-1"]["verified"] == True
        assert state.candidates["cand-1"]["verification"]["tier"] == "tier_1"
    
    def test_project_candidate_selected(self):
        """Test projecting candidate selection."""
        projector = IVCUStateProjector()
        
        events = [
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.INTENT_CREATED,
                data={"raw_intent": "Sort", "language": "python"}
            ),
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.CANDIDATE_GENERATED,
                data={"candidate_id": "cand-1", "code": "def sort(): pass"}
            ),
            create_event(
                ivcu_id="test-ivcu",
                event_type=IVCUEventType.CANDIDATE_SELECTED,
                data={"candidate_id": "cand-1"}
            )
        ]
        
        state = projector.project(events)
        
        assert state.selected_candidate_id == "cand-1"
        assert state.status == "selected"
    
    def test_project_to_version(self):
        """Test projecting to a specific version."""
        projector = IVCUStateProjector()
        
        events = [
            create_event(ivcu_id="test-ivcu", event_type=IVCUEventType.INTENT_CREATED,
                        data={"raw_intent": "v1"}),
            create_event(ivcu_id="test-ivcu", event_type=IVCUEventType.INTENT_REFINED,
                        data={"refined_intent": "v2"}),
            create_event(ivcu_id="test-ivcu", event_type=IVCUEventType.INTENT_REFINED,
                        data={"refined_intent": "v3"})
        ]
        
        # Project to version 2
        state = projector.project(events, up_to_version=2)
        
        assert state.intent == "v2"
        assert state.version == 2


class TestIVCUEventStoreUnit:
    """Unit tests for event store (mocked database)."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        conn.transaction.return_value.__aenter__.return_value = None
        return pool
    
    @pytest.mark.asyncio
    async def test_append_event(self, mock_pool):
        """Test appending an event."""
        store = IVCUEventStore(mock_pool)
        
        event = create_event(
            ivcu_id="test-ivcu",
            event_type=IVCUEventType.INTENT_CREATED,
            data={"raw_intent": "Test"}
        )
        
        mock_pool.acquire.return_value.__aenter__.return_value.execute = AsyncMock()
        
        event_id = await store.append(event)
        
        assert event_id == event.id
    
    @pytest.mark.asyncio
    async def test_get_events_empty(self, mock_pool):
        """Test getting events for non-existent IVCU."""
        store = IVCUEventStore(mock_pool)
        
        mock_pool.acquire.return_value.__aenter__.return_value.fetch = AsyncMock(return_value=[])
        
        events = await store.get_events("non-existent")
        
        assert events == []

    @pytest.mark.asyncio
    async def test_get_state(self, mock_pool):
        """Test state reconstruction from events."""
        store = IVCUEventStore(mock_pool)
        
        # Mock events from database
        mock_rows = [
            {
                "id": str(uuid.uuid4()),
                "ivcu_id": "test-ivcu",
                "event_type": "intent_created",
                "data": '{"raw_intent": "Test", "language": "python"}',
                "timestamp": datetime.utcnow(),
                "version": 1,
                "user_id": None,
                "correlation_id": None
            }
        ]
        
        mock_pool.acquire.return_value.__aenter__.return_value.fetch = AsyncMock(
            return_value=mock_rows
        )
        
        state = await store.get_state("test-ivcu")
        
        assert state.ivcu_id == "test-ivcu"
        assert state.intent == "Test"
        assert state.language == "python"


class TestUndoRedo:
    """Test undo/redo functionality."""
    
    def test_projector_undo_simulation(self):
        """Test that projecting to earlier version simulates undo."""
        projector = IVCUStateProjector()
        
        events = [
            create_event(ivcu_id="test", event_type=IVCUEventType.INTENT_CREATED,
                        data={"raw_intent": "Original"}),
            create_event(ivcu_id="test", event_type=IVCUEventType.INTENT_REFINED,
                        data={"refined_intent": "Refined"}),
        ]
        
        # Current state
        current = projector.project(events)
        assert current.intent == "Refined"
        
        # "Undo" by projecting to version 1
        undone = projector.project(events, up_to_version=1)
        assert undone.intent == "Original"


# Run with: pytest test_event_sourcing.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
