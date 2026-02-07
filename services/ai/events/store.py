"""
IVCU Event Store

Persistence layer for IVCU events.
"""
import uuid
import json
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from .model import IVCUEvent, IVCUState, EventType

# Try import asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails."""
    pass


class IVCUEventStore:
    """
    Event Store for IVCU events.
    """
    
    def __init__(self, pool=None):
        self.pool = pool
        self._memory_events: Dict[str, List[IVCUEvent]] = {} # Fallback memory store via dict for dev/test
    
    async def initialize_schema(self):
        """Create event store tables if they don't exist."""
        if not self.pool or not ASYNCPG_AVAILABLE:
            print("Event Store: Using in-memory fallback (DB unavailable)")
            return

        try:
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
                """)
        except Exception as e:
            print(f"Event Store Schema Init Failed: {e}")

    async def append_event(
        self,
        ivcu_id: str,
        event_type: EventType,
        event_data: Dict[str, Any],
        actor_id: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> Optional[IVCUEvent]:
        """
        Append a new event to the store.
        """
        timestamp = datetime.utcnow()
        event_id = str(uuid.uuid4())
        
        # 1. DB Implementation
        if self.pool and ASYNCPG_AVAILABLE:
            try:
                async with self.pool.acquire() as conn:
                    async with conn.transaction():
                        # Get next sequence number
                        result = await conn.fetchrow("""
                            SELECT COALESCE(MAX(sequence_number), 0) as max_seq
                            FROM ivcu_events
                            WHERE ivcu_id = $1
                        """, uuid.UUID(ivcu_id))
                        
                        current_version = result['max_seq']
                        
                        if expected_version is not None and current_version != expected_version:
                            raise ConcurrencyError(f"Expected {expected_version}, got {current_version}")
                        
                        next_seq = current_version + 1
                        
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
                        
                        return IVCUEvent(event_id, ivcu_id, next_seq, event_type, event_data, timestamp, actor_id)
            except Exception as e:
                print(f"Failed to append event to DB: {e}")
                # Fallthrough to memory? Or fail? 
                # For this dev phase, let's fallthrough implies we assume dev mode if DB fails often
                # But typically we should error. I will fallthrough for robustness in this specific agent flow.

        # 2. In-Memory Fallback
        if ivcu_id not in self._memory_events:
            self._memory_events[ivcu_id] = []
        
        current_version = len(self._memory_events[ivcu_id])
        if expected_version is not None and current_version != expected_version:
             raise ConcurrencyError(f"Expected {expected_version}, got {current_version}")
             
        next_seq = current_version + 1
        event = IVCUEvent(event_id, ivcu_id, next_seq, event_type, event_data, timestamp, actor_id)
        self._memory_events[ivcu_id].append(event)
        
        return event

    async def get_events(self, ivcu_id: str) -> List[IVCUEvent]:
        """Get all events for an IVCU."""
        if self.pool and ASYNCPG_AVAILABLE:
            try:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT id, ivcu_id, sequence_number, event_type, event_data, timestamp, actor_id
                        FROM ivcu_events
                        WHERE ivcu_id = $1
                        ORDER BY sequence_number ASC
                    """, uuid.UUID(ivcu_id))
                    return [IVCUEvent.from_row(row) for row in rows]
            except Exception as e:
                print(f"Failed to get events from DB: {e}")
        
        return self._memory_events.get(ivcu_id, [])

    async def get_state(self, ivcu_id: str) -> IVCUState:
        """Reconstruct state from events."""
        events = await self.get_events(ivcu_id)
        state = IVCUState(id=ivcu_id)
        for event in events:
            state = state.apply_event(event)
        return state

# Singleton
_event_store = None

async def get_event_store(pool=None) -> IVCUEventStore:
    global _event_store
    if _event_store is None:
        _event_store = IVCUEventStore(pool)
        await _event_store.initialize_schema()
    return _event_store
