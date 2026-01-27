"""
IVCU Event Sourcing System

Implements event sourcing for Intent-Verified Code Units (IVCUs).
All state changes are stored as immutable events, enabling:
- Perfect undo/redo
- Complete audit trail
- Point-in-time reconstruction
- Cost ledger tracking

Architecture v2.0 compliant.
"""
import uuid
import json
import asyncio
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
import asyncpg


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
    
    Events are append-only - they cannot be modified or deleted.
    """
    id: str
    ivcu_id: str
    sequence_number: int
    event_type: EventType
    event_data: Dict[str, Any]
    timestamp: datetime
    actor_id: Optional[str] = None  # User or system that triggered the event
    
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
    def from_row(cls, row: asyncpg.Record) -> 'IVCUEvent':
        """Create event from database row."""
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
    
    This is a read model that can be reconstructed from events at any time.
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
        # Create a copy
        new_state = IVCUState(
            id=self.id,
            version=self.version + 1,
            raw_intent=self.raw_intent,
            parsed_intent=self.parsed_intent,
            contracts=self.contracts.copy(),
            candidates=self.candidates.copy(),
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
        
        match event.event_type:
            case EventType.INTENT_CREATED:
                new_state.raw_intent = data.get("raw_intent")
                new_state.parsed_intent = data.get("parsed_intent")
                new_state.language = data.get("language", "python")
                new_state.status = "draft"
                new_state.created_at = event.timestamp
                
            case EventType.CONTRACT_ADDED:
                contract = data.get("contract", {})
                new_state.contracts.append(contract)
                
            case EventType.CANDIDATE_GENERATED:
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
                
            case EventType.VERIFICATION_COMPLETED:
                candidate_id = data.get("candidate_id")
                for cand in new_state.candidates:
                    if cand.get("id") == candidate_id:
                        cand["verification_passed"] = data.get("passed", False)
                        cand["verification_score"] = data.get("score", 0.0)
                        cand["verification_result"] = data.get("results")
                new_state.status = "verifying"
                
            case EventType.CANDIDATE_SELECTED:
                new_state.selected_candidate_id = data.get("candidate_id")
                new_state.code = data.get("code")
                new_state.confidence = data.get("confidence", 0.0)
                new_state.verification_result = data.get("verification_result")
                new_state.status = "verified"
                
            case EventType.INTENT_REFINED:
                new_state.raw_intent = data.get("new_intent", new_state.raw_intent)
                new_state.parsed_intent = data.get("new_parsed_intent", new_state.parsed_intent)
                if data.get("clear_candidates", False):
                    new_state.candidates = []
                    new_state.selected_candidate_id = None
                    new_state.code = None
                    new_state.status = "draft"
                
            case EventType.PROOF_GENERATED:
                new_state.proof_certificate = data.get("certificate")
                
            case EventType.IVCU_DEPLOYED:
                new_state.status = "deployed"
                
            case EventType.IVCU_DEPRECATED:
                new_state.status = "deprecated"
                
            case EventType.COST_INCURRED:
                new_state.total_cost += data.get("amount", 0.0)
        
        return new_state
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "raw_intent": self.raw_intent,
            "parsed_intent": self.parsed_intent,
            "contracts": self.contracts,
            "candidates": self.candidates,
            "selected_candidate_id": self.selected_candidate_id,
            "code": self.code,
            "language": self.language,
            "confidence": self.confidence,
            "verification_result": self.verification_result,
            "proof_certificate": self.proof_certificate,
            "status": self.status,
            "total_cost": self.total_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class IVCUEventStore:
    """
    Event Store for IVCU events.
    
    Implements append-only event storage with:
    - Sequence number enforcement
    - Optimistic concurrency control
    - State projection at any point in time
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def initialize_schema(self):
        """Create event store tables if they don't exist."""
        async with self.pool.acquire() as conn:
            # IVCU Events table (append-only)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ivcu_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    ivcu_id UUID NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data JSONB NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    actor_id UUID,
                    
                    UNIQUE(ivcu_id, sequence_number)
                );
                
                CREATE INDEX IF NOT EXISTS idx_ivcu_events_ivcu_id 
                    ON ivcu_events(ivcu_id);
                CREATE INDEX IF NOT EXISTS idx_ivcu_events_timestamp 
                    ON ivcu_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_ivcu_events_type 
                    ON ivcu_events(event_type);
            """)
            
            # IVCU Current State projection (materialized view)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ivcu_current_state (
                    id UUID PRIMARY KEY,
                    version INTEGER NOT NULL DEFAULT 0,
                    raw_intent TEXT,
                    parsed_intent JSONB,
                    contracts JSONB DEFAULT '[]'::jsonb,
                    selected_candidate_id UUID,
                    code TEXT,
                    language TEXT DEFAULT 'python',
                    confidence FLOAT DEFAULT 0.0,
                    verification_result JSONB,
                    proof_certificate JSONB,
                    status TEXT DEFAULT 'draft',
                    total_cost DECIMAL(10, 6) DEFAULT 0.0,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Proof Certificates table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS proof_certificates (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    ivcu_id UUID NOT NULL,
                    proof_type TEXT NOT NULL,
                    assertions JSONB NOT NULL,
                    proof_data BYTEA,
                    verifier_version TEXT,
                    hash_chain TEXT,
                    signature BYTEA,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT fk_ivcu FOREIGN KEY (ivcu_id) 
                        REFERENCES ivcu_current_state(id) ON DELETE CASCADE
                );
            """)
            
            # Audit Log view
            await conn.execute("""
                CREATE OR REPLACE VIEW ivcu_audit_log AS
                SELECT 
                    e.id,
                    e.ivcu_id,
                    e.sequence_number,
                    e.event_type,
                    e.timestamp,
                    e.actor_id,
                    CASE 
                        WHEN e.event_type = 'intent_created' THEN 'IVCU created'
                        WHEN e.event_type = 'candidate_generated' THEN 'Code generated'
                        WHEN e.event_type = 'verification_completed' THEN 'Verification completed'
                        WHEN e.event_type = 'candidate_selected' THEN 'Candidate selected'
                        ELSE e.event_type
                    END as description
                FROM ivcu_events e
                ORDER BY e.timestamp DESC;
            """)
            
            # Cost Ledger view
            await conn.execute("""
                CREATE OR REPLACE VIEW ivcu_cost_ledger AS
                SELECT 
                    ivcu_id,
                    SUM((event_data->>'amount')::float) as total_cost,
                    COUNT(*) as cost_events,
                    MIN(timestamp) as first_cost,
                    MAX(timestamp) as last_cost
                FROM ivcu_events
                WHERE event_type = 'cost_incurred'
                GROUP BY ivcu_id;
            """)
    
    async def append_event(
        self,
        ivcu_id: str,
        event_type: EventType,
        event_data: Dict[str, Any],
        actor_id: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> IVCUEvent:
        """
        Append a new event to the store.
        
        Args:
            ivcu_id: The IVCU ID
            event_type: Type of event
            event_data: Event payload
            actor_id: User/system that triggered the event
            expected_version: For optimistic concurrency (optional)
            
        Returns:
            The created event
            
        Raises:
            ConcurrencyError: If expected_version doesn't match
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Get next sequence number
                result = await conn.fetchrow("""
                    SELECT COALESCE(MAX(sequence_number), 0) as max_seq
                    FROM ivcu_events
                    WHERE ivcu_id = $1
                """, uuid.UUID(ivcu_id))
                
                current_version = result['max_seq']
                
                # Check optimistic concurrency
                if expected_version is not None and current_version != expected_version:
                    raise ConcurrencyError(
                        f"Expected version {expected_version}, but current is {current_version}"
                    )
                
                next_seq = current_version + 1
                event_id = str(uuid.uuid4())
                timestamp = datetime.utcnow()
                
                # Insert event
                await conn.execute("""
                    INSERT INTO ivcu_events 
                        (id, ivcu_id, sequence_number, event_type, event_data, timestamp, actor_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    uuid.UUID(event_id),
                    uuid.UUID(ivcu_id),
                    next_seq,
                    event_type.value,
                    json.dumps(event_data),
                    timestamp,
                    uuid.UUID(actor_id) if actor_id else None
                )
                
                # Update projection
                await self._update_projection(conn, ivcu_id)
                
                return IVCUEvent(
                    id=event_id,
                    ivcu_id=ivcu_id,
                    sequence_number=next_seq,
                    event_type=event_type,
                    event_data=event_data,
                    timestamp=timestamp,
                    actor_id=actor_id
                )
    
    async def get_events(
        self,
        ivcu_id: str,
        from_sequence: int = 0,
        to_sequence: Optional[int] = None
    ) -> List[IVCUEvent]:
        """Get events for an IVCU within a sequence range."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, ivcu_id, sequence_number, event_type, event_data, timestamp, actor_id
                FROM ivcu_events
                WHERE ivcu_id = $1 AND sequence_number > $2
            """
            params = [uuid.UUID(ivcu_id), from_sequence]
            
            if to_sequence is not None:
                query += " AND sequence_number <= $3"
                params.append(to_sequence)
            
            query += " ORDER BY sequence_number ASC"
            
            rows = await conn.fetch(query, *params)
            return [IVCUEvent.from_row(row) for row in rows]
    
    async def get_state(self, ivcu_id: str) -> Optional[IVCUState]:
        """Get current state from projection."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM ivcu_current_state WHERE id = $1
            """, uuid.UUID(ivcu_id))
            
            if not row:
                return None
            
            return IVCUState(
                id=str(row['id']),
                version=row['version'],
                raw_intent=row['raw_intent'],
                parsed_intent=json.loads(row['parsed_intent']) if row['parsed_intent'] else None,
                contracts=json.loads(row['contracts']) if row['contracts'] else [],
                selected_candidate_id=str(row['selected_candidate_id']) if row['selected_candidate_id'] else None,
                code=row['code'],
                language=row['language'] or 'python',
                confidence=row['confidence'] or 0.0,
                verification_result=json.loads(row['verification_result']) if row['verification_result'] else None,
                proof_certificate=json.loads(row['proof_certificate']) if row['proof_certificate'] else None,
                status=row['status'] or 'draft',
                total_cost=float(row['total_cost']) if row['total_cost'] else 0.0,
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def get_state_at(self, ivcu_id: str, timestamp: datetime) -> Optional[IVCUState]:
        """Reconstruct state at a specific point in time."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, ivcu_id, sequence_number, event_type, event_data, timestamp, actor_id
                FROM ivcu_events
                WHERE ivcu_id = $1 AND timestamp <= $2
                ORDER BY sequence_number ASC
            """, uuid.UUID(ivcu_id), timestamp)
            
            if not rows:
                return None
            
            # Replay events to reconstruct state
            state = IVCUState(id=ivcu_id)
            for row in rows:
                event = IVCUEvent.from_row(row)
                state = state.apply_event(event)
            
            return state
    
    async def undo(self, ivcu_id: str, actor_id: Optional[str] = None) -> Optional[IVCUState]:
        """
        Undo the last operation by generating a compensating event.
        
        Returns the new state after undo.
        """
        events = await self.get_events(ivcu_id)
        if len(events) < 2:
            return None  # Nothing to undo
        
        last_event = events[-1]
        
        # Generate compensating event based on event type
        compensating_data = await self._create_compensating_event(ivcu_id, last_event, events)
        
        if compensating_data:
            event_type, event_data = compensating_data
            await self.append_event(ivcu_id, event_type, event_data, actor_id)
        
        return await self.get_state(ivcu_id)
    
    async def _create_compensating_event(
        self, 
        ivcu_id: str, 
        last_event: IVCUEvent,
        all_events: List[IVCUEvent]
    ) -> Optional[tuple]:
        """Create a compensating event to undo the last operation."""
        match last_event.event_type:
            case EventType.CANDIDATE_SELECTED:
                # Undo selection - go back to verifying state
                return (EventType.INTENT_REFINED, {
                    "clear_candidates": False,
                    "undo_selection": True,
                    "reason": "Undo candidate selection"
                })
            
            case EventType.INTENT_REFINED:
                # Find previous intent from events
                for event in reversed(all_events[:-1]):
                    if event.event_type == EventType.INTENT_CREATED:
                        return (EventType.INTENT_REFINED, {
                            "new_intent": event.event_data.get("raw_intent"),
                            "new_parsed_intent": event.event_data.get("parsed_intent"),
                            "reason": "Undo intent refinement"
                        })
                return None
            
            case _:
                # For other events, we can't easily undo
                return None
    
    async def _update_projection(self, conn: asyncpg.Connection, ivcu_id: str):
        """Update the current state projection from events."""
        # Get all events
        rows = await conn.fetch("""
            SELECT id, ivcu_id, sequence_number, event_type, event_data, timestamp, actor_id
            FROM ivcu_events
            WHERE ivcu_id = $1
            ORDER BY sequence_number ASC
        """, uuid.UUID(ivcu_id))
        
        if not rows:
            return
        
        # Replay events
        state = IVCUState(id=ivcu_id)
        for row in rows:
            event = IVCUEvent.from_row(row)
            state = state.apply_event(event)
        
        # Upsert projection
        await conn.execute("""
            INSERT INTO ivcu_current_state 
                (id, version, raw_intent, parsed_intent, contracts, selected_candidate_id,
                 code, language, confidence, verification_result, proof_certificate,
                 status, total_cost, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (id) DO UPDATE SET
                version = EXCLUDED.version,
                raw_intent = EXCLUDED.raw_intent,
                parsed_intent = EXCLUDED.parsed_intent,
                contracts = EXCLUDED.contracts,
                selected_candidate_id = EXCLUDED.selected_candidate_id,
                code = EXCLUDED.code,
                language = EXCLUDED.language,
                confidence = EXCLUDED.confidence,
                verification_result = EXCLUDED.verification_result,
                proof_certificate = EXCLUDED.proof_certificate,
                status = EXCLUDED.status,
                total_cost = EXCLUDED.total_cost,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at
        """,
            uuid.UUID(ivcu_id),
            state.version,
            state.raw_intent,
            json.dumps(state.parsed_intent) if state.parsed_intent else None,
            json.dumps(state.contracts),
            uuid.UUID(state.selected_candidate_id) if state.selected_candidate_id else None,
            state.code,
            state.language,
            state.confidence,
            json.dumps(state.verification_result) if state.verification_result else None,
            json.dumps(state.proof_certificate) if state.proof_certificate else None,
            state.status,
            state.total_cost,
            state.created_at,
            state.updated_at
        )
    
    async def get_audit_log(self, ivcu_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get human-readable audit log for an IVCU."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM ivcu_audit_log
                WHERE ivcu_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, uuid.UUID(ivcu_id), limit)
            
            return [dict(row) for row in rows]
    
    async def get_cost_ledger(self, ivcu_id: str) -> Dict[str, Any]:
        """Get cost ledger for an IVCU."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM ivcu_cost_ledger WHERE ivcu_id = $1
            """, uuid.UUID(ivcu_id))
            
            if not row:
                return {"total_cost": 0.0, "cost_events": 0}
            
            return dict(row)


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails."""
    pass


# Singleton instance
_event_store: Optional[IVCUEventStore] = None


async def get_event_store(pool: asyncpg.Pool) -> IVCUEventStore:
    """Get or create the event store singleton."""
    global _event_store
    if _event_store is None:
        _event_store = IVCUEventStore(pool)
        await _event_store.initialize_schema()
    return _event_store
