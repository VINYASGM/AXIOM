"""
Projection Engine (Design.md Section 2.2)

Consumes events from NATS JetStream and projects them to read models:
- Writes to memory store for vector search
- Generates sync tokens for consistency tracking
- Supports at-least-once delivery with idempotency

Architecture v2.0+ compliant with eventual consistency patterns.
"""
import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
import hashlib

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from eventbus import get_event_bus, StreamName, JetStreamEventBus


class EventType(str, Enum):
    """Supported event types for projection."""
    INTENT_CREATED = "intent_created"
    CANDIDATE_GENERATED = "candidate_generated"
    VERIFICATION_COMPLETED = "verification_completed"
    SDO_UPDATED = "sdo_updated"
    IVCU_DEPLOYED = "ivcu_deployed"


@dataclass
class ProjectedEvent:
    """Wrapper for events being projected."""
    id: str
    type: EventType
    aggregate_id: str
    sequence: int
    timestamp: datetime
    data: Dict[str, Any]
    
    @property
    def sync_token(self) -> str:
        """Generate a sync token for this event."""
        return f"sync:{self.aggregate_id}:{self.sequence}"
    
    @property
    def idempotency_key(self) -> str:
        """Generate an idempotency key for deduplication."""
        return hashlib.sha256(f"{self.aggregate_id}:{self.sequence}".encode()).hexdigest()[:16]


class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    async def project(self, event: ProjectedEvent) -> bool:
        """
        Project an event to read models.
        
        Args:
            event: The event to project
            
        Returns:
            True if projection succeeded, False otherwise
        """
        pass


class IntentCreatedHandler(EventHandler):
    """Handler for intent_created events."""
    
    def __init__(self, memory_service, database_service):
        self.memory = memory_service
        self.database = database_service
    
    async def project(self, event: ProjectedEvent) -> bool:
        try:
            data = event.data
            
            # 1. Store in memory for semantic search
            if self.memory:
                await self.memory.store(
                    text=data.get("intent", ""),
                    metadata={
                        "sdo_id": event.aggregate_id,
                        "type": "intent",
                        "timestamp": event.timestamp.isoformat()
                    }
                )
            
            print(f"Projected intent_created for {event.aggregate_id}")
            return True
            
        except Exception as e:
            print(f"Error projecting intent_created: {e}")
            return False


class VerificationCompletedHandler(EventHandler):
    """Handler for verification_completed events."""
    
    def __init__(self, database_service):
        self.database = database_service
    
    async def project(self, event: ProjectedEvent) -> bool:
        try:
            data = event.data
            
            # Update verification stats in database
            # This is a read-model optimization
            if self.database and self.database.pool:
                async with self.database.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO projection_stats 
                        (entity_id, stat_type, value, updated_at)
                        VALUES ($1, 'verification_count', 1, CURRENT_TIMESTAMP)
                        ON CONFLICT (entity_id, stat_type) 
                        DO UPDATE SET 
                            value = projection_stats.value + 1,
                            updated_at = CURRENT_TIMESTAMP
                    """, event.aggregate_id, )
            
            print(f"Projected verification_completed for {event.aggregate_id}")
            return True
            
        except Exception as e:
            print(f"Error projecting verification_completed: {e}")
            return False


class SDOUpdatedHandler(EventHandler):
    """Handler for sdo_updated events - updates graph structure in Neo4j."""
    
    def __init__(self, graph_memory, neo4j_client=None):
        self.graph = graph_memory
        self.neo4j = neo4j_client
    
    async def project(self, event: ProjectedEvent) -> bool:
        try:
            data = event.data
            
            # 1. Project to Neo4j graph if available
            if self.neo4j:
                from neo4j_client import get_neo4j_client
                client = await get_neo4j_client()
                
                if client._initialized:
                    # Create/update SDO node
                    await client.create_sdo_node(
                        sdo_id=event.aggregate_id,
                        intent=data.get("intent", "")[:500],
                        language=data.get("language", "python"),
                        status=data.get("status", "pending"),
                        confidence=data.get("confidence", 0.0),
                        project_id=data.get("project_id")
                    )
                    
                    # Add dependencies if present
                    for dep in data.get("dependencies", []):
                        await client.add_dependency(
                            source_id=event.aggregate_id,
                            target_id=dep.get("id"),
                            dependency_type="DEPENDS_ON",
                            properties={"reason": dep.get("reason", "")}
                        )
            
            print(f"Projected sdo_updated for {event.aggregate_id}")
            return True
        except Exception as e:
            print(f"Error projecting sdo_updated: {e}")
            return False


class ConsistencyManager:
    """
    Manages read-after-write consistency using sync tokens (Design.md Section 2.3).
    
    Stores sync tokens in Redis with TTL.
    Clients can wait for specific sync tokens to ensure consistency.
    """
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 300):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://axiom-redis:6379")
        self.default_ttl = default_ttl  # 5 minutes
        self._redis = None
        self._local_cache: Dict[str, datetime] = {}  # Fallback when Redis unavailable
    
    async def initialize(self) -> bool:
        """Connect to Redis."""
        if aioredis is None:
            print("WARN: redis.asyncio not available, using local cache fallback")
            return False
            
        try:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            print(f"ConsistencyManager connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            print(f"WARN: Redis connection failed, using local cache: {e}")
            return False
    
    async def mark_complete(self, sync_token: str, ttl: Optional[int] = None) -> bool:
        """
        Mark a sync token as complete.
        
        Args:
            sync_token: The sync token to mark
            ttl: Time-to-live in seconds (default: 300)
            
        Returns:
            True if successfully marked
        """
        ttl = ttl or self.default_ttl
        
        if self._redis:
            try:
                await self._redis.setex(sync_token, ttl, "complete")
                return True
            except Exception as e:
                print(f"Redis setex failed: {e}")
        
        # Fallback to local cache
        self._local_cache[sync_token] = datetime.utcnow() + timedelta(seconds=ttl)
        return True
    
    async def is_complete(self, sync_token: str) -> bool:
        """
        Check if a sync token is complete.
        
        Args:
            sync_token: The sync token to check
            
        Returns:
            True if complete
        """
        if self._redis:
            try:
                result = await self._redis.get(sync_token)
                return result == "complete"
            except Exception as e:
                print(f"Redis get failed: {e}")
        
        # Fallback to local cache
        if sync_token in self._local_cache:
            if datetime.utcnow() < self._local_cache[sync_token]:
                return True
            else:
                del self._local_cache[sync_token]
        return False
    
    async def wait_for(
        self, 
        sync_token: str, 
        timeout: float = 5.0,
        poll_interval: float = 0.1
    ) -> bool:
        """
        Wait for a sync token to become complete.
        
        Args:
            sync_token: The sync token to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds
            
        Returns:
            True if token became complete within timeout
        """
        start = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start) < timeout:
            if await self.is_complete(sync_token):
                return True
            await asyncio.sleep(poll_interval)
        
        return False
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


class ProjectionEngine:
    """
    Main projection engine that coordinates event consumption and projection.
    
    Features:
    - Consumes from NATS JetStream with at-least-once delivery
    - Routes events to appropriate handlers
    - Tracks sync tokens via ConsistencyManager
    - Handles errors with backoff
    """
    
    def __init__(
        self,
        memory_service=None,
        database_service=None,
        graph_memory=None
    ):
        self.event_bus: Optional[JetStreamEventBus] = None
        self.consistency = ConsistencyManager()
        
        # Initialize handlers
        self.handlers: Dict[str, EventHandler] = {}
        
        if memory_service or database_service:
            self.handlers["intent_created"] = IntentCreatedHandler(memory_service, database_service)
        
        if database_service:
            self.handlers["verification_completed"] = VerificationCompletedHandler(database_service)
        
        if graph_memory:
            self.handlers["sdo_updated"] = SDOUpdatedHandler(graph_memory)
        
        # Metrics
        self.processed_count = 0
        self.error_count = 0
        self._running = False
        self._sequence_tracker: Dict[str, int] = {}  # Track last processed sequence per aggregate
    
    async def initialize(self) -> bool:
        """Initialize the projection engine."""
        try:
            # Connect to event bus
            self.event_bus = await get_event_bus()
            
            # Initialize consistency manager
            await self.consistency.initialize()
            
            print("ProjectionEngine initialized")
            return True
        except Exception as e:
            print(f"Failed to initialize ProjectionEngine: {e}")
            return False
    
    async def start(self):
        """Start consuming events."""
        if not self.event_bus:
            await self.initialize()
        
        self._running = True
        
        # Subscribe to relevant streams
        await self.event_bus.subscribe(
            subject="gen.>",
            stream=StreamName.GENERATIONS,
            consumer_name="projection-engine-gen",
            callback=self._handle_event,
            max_deliver=3
        )
        
        await self.event_bus.subscribe(
            subject="ivcu.>",
            stream=StreamName.IVCU_EVENTS,
            consumer_name="projection-engine-ivcu",
            callback=self._handle_event,
            max_deliver=3
        )
        
        print("ProjectionEngine started consuming events")
    
    async def _handle_event(self, msg_data: Dict[str, Any]):
        """
        Handle an incoming event.
        
        Implements:
        1. Event parsing
        2. Idempotency check
        3. Handler routing
        4. Sync token emission
        """
        try:
            # 1. Parse event
            event_type = msg_data.get("event", "unknown")
            aggregate_id = msg_data.get("ivcu_id") or msg_data.get("sdo_id") or "unknown"
            sequence = msg_data.get("_seq", 0)
            
            event = ProjectedEvent(
                id=f"{aggregate_id}-{sequence}",
                type=EventType(event_type) if event_type in [e.value for e in EventType] else None,
                aggregate_id=aggregate_id,
                sequence=sequence,
                timestamp=datetime.fromisoformat(msg_data.get("_timestamp", datetime.utcnow().isoformat())),
                data=msg_data
            )
            
            # 2. Idempotency check (skip if already processed)
            last_seq = self._sequence_tracker.get(aggregate_id, -1)
            if sequence <= last_seq:
                print(f"Skipping duplicate event {event.id}")
                return
            
            # 3. Route to handler
            handler = self.handlers.get(event_type)
            if handler:
                success = await handler.project(event)
                
                if success:
                    self.processed_count += 1
                    self._sequence_tracker[aggregate_id] = sequence
                    
                    # 4. Mark sync token as complete
                    await self.consistency.mark_complete(event.sync_token)
                else:
                    self.error_count += 1
            else:
                # No handler, but still acknowledge
                print(f"No handler for event type: {event_type}")
            
        except Exception as e:
            print(f"Error handling event: {e}")
            self.error_count += 1
    
    async def stop(self):
        """Stop the projection engine."""
        self._running = False
        await self.consistency.close()
        print("ProjectionEngine stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "handlers": list(self.handlers.keys()),
            "running": self._running
        }


# Global instance
_projection_engine: Optional[ProjectionEngine] = None


async def init_projection_engine(
    memory_service=None,
    database_service=None,
    graph_memory=None
) -> ProjectionEngine:
    """Initialize the global projection engine."""
    global _projection_engine
    _projection_engine = ProjectionEngine(memory_service, database_service, graph_memory)
    await _projection_engine.initialize()
    return _projection_engine


def get_projection_engine() -> Optional[ProjectionEngine]:
    """Get the global projection engine instance."""
    return _projection_engine
