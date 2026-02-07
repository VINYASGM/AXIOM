"""
IVCU Event Models

Defines the events and state projections for the Event Sourcing system.
"""
import uuid
import json
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

class EventType(str, Enum):
    """IVCU Event Types per Architecture v2.0"""
    INTENT_CREATED = "intent_created"
    CONTRACT_ADDED = "contract_added"
    CANDIDATE_GENERATED = "candidate_generated"
    VERIFICATION_COMPLETED = "verification_completed"
    CANDIDATE_SELECTED = "candidate_selected"
    INTENT_REFINED = "intent_refined"
    PROOF_GENERATED = "proof_generated"
    IVCU_DEPLOYED = "ivcu_deployed"
    IVCU_DEPRECATED = "ivcu_deprecated"
    COST_INCURRED = "cost_incurred"


@dataclass
class IVCUEvent:
    """
    Immutable event representing a state change to an IVCU.
    Events are append-only.
    """
    id: str
    ivcu_id: str
    sequence_number: int
    event_type: EventType
    event_data: Dict[str, Any]
    timestamp: datetime
    actor_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ivcu_id": self.ivcu_id,
            "sequence_number": self.sequence_number,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "event_data": self.event_data,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "actor_id": self.actor_id
        }
    
    @classmethod
    def from_row(cls, row: Any) -> 'IVCUEvent':
        """Create event from database row (asyncpg Record)."""
        return cls(
            id=str(row['id']),
            ivcu_id=str(row['ivcu_id']),
            sequence_number=row['sequence_number'],
            event_type=EventType(row['event_type']),
            event_data=json.loads(row['event_data']) if isinstance(row['event_data'], str) else row['event_data'],
            timestamp=row['timestamp'],
            actor_id=str(row['actor_id']) if row['actor_id'] else None
        )


@dataclass
class IVCUState:
    """
    Current state of an IVCU, projected from events.
    """
    id: str
    version: int = 0
    raw_intent: Optional[str] = None
    parsed_intent: Optional[Dict[str, Any]] = None
    contracts: List[Dict[str, Any]] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected_candidate_id: Optional[str] = None
    code: Optional[str] = None
    language: str = "python"
    confidence: float = 0.0
    verification_result: Optional[Dict[str, Any]] = None
    proof_certificate: Optional[Dict[str, Any]] = None
    status: str = "draft"
    total_cost: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def apply_event(self, event: IVCUEvent) -> 'IVCUState':
        """Apply an event to produce new state. Immutable - returns new state."""
        new_state = IVCUState(
            id=self.id,
            version=self.version + 1,
            raw_intent=self.raw_intent,
            parsed_intent=self.parsed_intent,
            contracts=self.contracts.copy(),
            candidates=[c.copy() for c in self.candidates], # Deepish copy
            selected_candidate_id=self.selected_candidate_id,
            code=self.code,
            language=self.language,
            confidence=self.confidence,
            verification_result=self.verification_result,
            proof_certificate=self.proof_certificate,
            status=self.status,
            total_cost=self.total_cost,
            created_at=self.created_at,
            updated_at=event.timestamp
        )
        
        data = event.event_data
        
        if event.event_type == EventType.INTENT_CREATED:
            new_state.raw_intent = data.get("raw_intent")
            new_state.parsed_intent = data.get("parsed_intent")
            new_state.language = data.get("language", "python")
            new_state.status = "draft"
            new_state.created_at = event.timestamp
            
        elif event.event_type == EventType.CONTRACT_ADDED:
            contract = data.get("contract", {})
            new_state.contracts.append(contract)
            
        elif event.event_type == EventType.CANDIDATE_GENERATED:
            candidate = {
                "id": data.get("candidate_id"),
                "code": data.get("code"),
                "confidence": data.get("confidence", 0.0),
                "model_id": data.get("model_id"),
                "reasoning": data.get("reasoning"),
                "verification_passed": False,
                "verification_score": 0.0
            }
            new_state.candidates.append(candidate)
            new_state.status = "generating"
            
        elif event.event_type == EventType.VERIFICATION_COMPLETED:
            candidate_id = data.get("candidate_id")
            for cand in new_state.candidates:
                if cand.get("id") == candidate_id:
                    cand["verification_passed"] = data.get("passed", False)
                    cand["verification_score"] = data.get("score", 0.0)
                    cand["verification_result"] = data.get("results")
            new_state.status = "verifying"
            
        elif event.event_type == EventType.CANDIDATE_SELECTED:
            new_state.selected_candidate_id = data.get("candidate_id")
            new_state.code = data.get("code")
            new_state.confidence = data.get("confidence", 0.0)
            new_state.verification_result = data.get("verification_result")
            new_state.status = "verified"
            
        elif event.event_type == EventType.INTENT_REFINED:
            new_state.raw_intent = data.get("new_intent", new_state.raw_intent)
            new_state.parsed_intent = data.get("new_parsed_intent", new_state.parsed_intent)
            if data.get("clear_candidates", False):
                new_state.candidates = []
                new_state.selected_candidate_id = None
                new_state.code = None
                new_state.status = "draft"
        
        elif event.event_type == EventType.COST_INCURRED:
            new_state.total_cost += data.get("amount", 0.0)
            
        return new_state
