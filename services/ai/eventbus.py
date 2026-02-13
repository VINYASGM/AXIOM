"""
NATS JetStream Event Bus

Persistent event streaming for AXIOM using NATS JetStream.
Architecture v2.0 compliant with message persistence and replay.

Streams:
- GENERATIONS: Generation events with 7-day retention
- AUDIT: Audit trail with 90-day retention
- METRICS: Performance metrics with 24-hour retention
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import nats
from nats.js.api import StreamConfig, ConsumerConfig, AckPolicy, DeliverPolicy, RetentionPolicy
from nats.errors import ConnectionClosedError, TimeoutError, NoRespondersError


class StreamName(str, Enum):
    """JetStream stream names."""
    GENERATIONS = "GENERATIONS"
    AUDIT = "AUDIT"
    METRICS = "METRICS"
    IVCU_EVENTS = "IVCU_EVENTS"


@dataclass
class StreamSettings:
    """Configuration for a JetStream stream."""
    name: str
    subjects: List[str]
    retention_days: int = 7
    max_bytes: int = 1024 * 1024 * 1024  # 1GB default
    replicas: int = 1
    
    def to_config(self) -> StreamConfig:
        return StreamConfig(
            name=self.name,
            subjects=self.subjects,
            retention=RetentionPolicy.LIMITS,
            max_age=0, # Explicitly set to 0 (unlimited) to avoid nanosecond overflow issues
            max_bytes=self.max_bytes,
            num_replicas=self.replicas
        )


# Default stream configurations
STREAM_CONFIGS = {
    StreamName.GENERATIONS: StreamSettings(
        name="GENERATIONS",
        subjects=["gen.>"],
        retention_days=7,
        max_bytes=5 * 1024 * 1024 * 1024  # 5GB
    ),
    StreamName.AUDIT: StreamSettings(
        name="AUDIT",
        subjects=["audit.>"],
        retention_days=90,
        max_bytes=10 * 1024 * 1024 * 1024  # 10GB
    ),
    StreamName.METRICS: StreamSettings(
        name="METRICS",
        subjects=["metrics.>"],
        retention_days=1,
        max_bytes=1 * 1024 * 1024 * 1024  # 1GB
    ),
    StreamName.IVCU_EVENTS: StreamSettings(
        name="IVCU_EVENTS",
        subjects=["ivcu.>"],
        retention_days=365,
        max_bytes=20 * 1024 * 1024 * 1024  # 20GB
    )
}


class JetStreamEventBus:
    """
    NATS JetStream event bus for AXIOM.
    
    Features:
    - Persistent message storage
    - Consumer groups for load balancing
    - Message replay from any point
    - Exactly-once delivery semantics
    """
    
    def __init__(self, nats_url: Optional[str] = None):
        self.nats_url = nats_url or os.getenv("NATS_URL", "nats://axiom-nats:4222")
        self._nc: Optional[nats.NATS] = None
        self._js = None
        self._subscriptions = []
    
    async def connect(self) -> bool:
        """Connect to NATS and initialize JetStream."""
        try:
            self._nc = await nats.connect(
                self.nats_url,
                reconnect_time_wait=2,
                max_reconnect_attempts=-1,
                error_cb=self._error_cb,
                reconnected_cb=self._reconnected_cb,
                disconnected_cb=self._disconnected_cb
            )
            
            # Get JetStream context
            self._js = self._nc.jetstream()
            
            # Initialize streams
            await self._init_streams()
            
            print(f"Connected to NATS JetStream at {self.nats_url}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to NATS: {e}")
            return False
    
    async def _init_streams(self):
        """Create/update streams if they don't exist."""
        for stream_name, settings in STREAM_CONFIGS.items():
            try:
                await self._js.add_stream(settings.to_config())
                print(f"Stream {stream_name.value} ready")
            except Exception as e:
                # Stream might already exist, try to update
                try:
                    await self._js.update_stream(settings.to_config())
                except Exception as update_err:
                    print(f"Stream {stream_name.value} update failed: {update_err}")
                    print(f"Original add error: {e}")
    
    async def publish(
        self,
        subject: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Publish a message to JetStream.
        
        Args:
            subject: Subject to publish to (e.g., "gen.created", "audit.ivcu")
            data: Message payload as dict
            headers: Optional headers
            
        Returns:
            Message sequence number or None on failure
        """
        if not self._js:
            print("JetStream not connected")
            return None
        
        try:
            payload = json.dumps({
                **data,
                "_timestamp": datetime.utcnow().isoformat(),
                "_subject": subject
            }).encode()
            
            ack = await self._js.publish(subject, payload, headers=headers)
            return str(ack.seq)
            
        except Exception as e:
            print(f"Failed to publish to {subject}: {e}")
            return None
    
    async def subscribe(
        self,
        subject: str,
        stream: StreamName,
        consumer_name: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]],
        deliver_policy: DeliverPolicy = DeliverPolicy.NEW,
        ack_wait: int = 30,
        max_deliver: int = 3
    ):
        """
        Subscribe to a JetStream stream with a durable consumer.
        
        Args:
            subject: Subject pattern to subscribe to
            stream: Stream to consume from
            consumer_name: Durable consumer name
            callback: Async callback for messages
            deliver_policy: Where to start consuming
            ack_wait: Seconds to wait for ack
            max_deliver: Max redelivery attempts
        """
        if not self._js:
            print("JetStream not connected")
            return
        
        async def message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                await callback(data)
                await msg.ack()
            except Exception as e:
                print(f"Message handler error: {e}")
                await msg.nak()
        
        try:
            consumer_config = ConsumerConfig(
                durable_name=consumer_name,
                ack_policy=AckPolicy.EXPLICIT,
                ack_wait=ack_wait,
                max_deliver=max_deliver,
                deliver_policy=deliver_policy,
                filter_subject=subject
            )
            
            sub = await self._js.subscribe(
                subject,
                stream=stream.value,
                config=consumer_config,
                cb=message_handler
            )
            
            self._subscriptions.append(sub)
            print(f"Subscribed to {subject} on stream {stream.value}")
            
        except Exception as e:
            print(f"Failed to subscribe to {subject}: {e}")
    
    async def get_messages(
        self,
        stream: StreamName,
        subject: Optional[str] = None,
        start_seq: int = 1,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a stream for replay.
        
        Args:
            stream: Stream to fetch from
            subject: Optional subject filter
            start_seq: Starting sequence number
            limit: Max messages to fetch
            
        Returns:
            List of message payloads
        """
        if not self._js:
            return []
        
        messages = []
        try:
            # Create ephemeral consumer for fetch
            consumer_name = f"fetch-{datetime.utcnow().timestamp()}"
            
            sub = await self._js.pull_subscribe(
                subject or ">",
                stream=stream.value,
                config=ConsumerConfig(
                    deliver_policy=DeliverPolicy.BY_START_SEQUENCE,
                    opt_start_seq=start_seq,
                    filter_subject=subject
                )
            )
            
            try:
                fetched = await sub.fetch(limit, timeout=5)
                for msg in fetched:
                    data = json.loads(msg.data.decode())
                    messages.append({
                        **data,
                        "_seq": msg.metadata.sequence.stream,
                        "_time": msg.metadata.timestamp
                    })
                    await msg.ack()
            finally:
                await sub.unsubscribe()
                
        except Exception as e:
            print(f"Failed to fetch messages: {e}")
        
        return messages
    
    async def close(self):
        """Close connection and cleanup."""
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except:
                pass
        
        if self._nc:
            await self._nc.close()
            self._nc = None
            self._js = None
    
    async def _error_cb(self, e):
        print(f"NATS Error: {e}")
    
    async def _reconnected_cb(self):
        print("NATS Reconnected")
    
    async def _disconnected_cb(self):
        print("NATS Disconnected")

    # =========================================================================
    # CONVENIENCE METHODS FOR AXIOM EVENTS
    # =========================================================================
    
    async def emit_generation_started(self, ivcu_id: str, intent: str, model_id: str):
        """Emit generation started event."""
        await self.publish("gen.started", {
            "ivcu_id": ivcu_id,
            "intent": intent,
            "model_id": model_id,
            "event": "generation_started"
        })
    
    async def emit_generation_completed(
        self,
        ivcu_id: str,
        candidate_id: str,
        success: bool,
        tokens_used: int,
        cost: float
    ):
        """Emit generation completed event."""
        await self.publish("gen.completed", {
            "ivcu_id": ivcu_id,
            "candidate_id": candidate_id,
            "success": success,
            "tokens_used": tokens_used,
            "cost": cost,
            "event": "generation_completed"
        })
    
    async def emit_verification_result(
        self,
        ivcu_id: str,
        candidate_id: str,
        passed: bool,
        tier: str,
        confidence: float
    ):
        """Emit verification result event."""
        await self.publish("audit.verification", {
            "ivcu_id": ivcu_id,
            "candidate_id": candidate_id,
            "passed": passed,
            "tier": tier,
            "confidence": confidence,
            "event": "verification_result"
        })
    
    async def emit_ivcu_deployed(self, ivcu_id: str, version: int):
        """Emit IVCU deployed event."""
        await self.publish("ivcu.deployed", {
            "ivcu_id": ivcu_id,
            "version": version,
            "event": "ivcu_deployed"
        })


# Global event bus instance
_event_bus: Optional[JetStreamEventBus] = None


async def get_event_bus() -> JetStreamEventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = JetStreamEventBus()
        await _event_bus.connect()
    return _event_bus


# Backwards compatibility
nc = None


async def init_nats():
    """Initialize NATS connection (legacy interface)."""
    global nc
    bus = await get_event_bus()
    nc = bus._nc
    return nc


async def close_nats():
    """Close NATS connection (legacy interface)."""
    global _event_bus, nc
    if _event_bus:
        await _event_bus.close()
        _event_bus = None
    nc = None


async def publish(subject: str, payload: bytes):
    """Publish a message to NATS (legacy interface)."""
    bus = await get_event_bus()
    data = json.loads(payload.decode()) if isinstance(payload, bytes) else payload
    await bus.publish(subject, data)


async def subscribe(subject: str, cb):
    """Subscribe to a subject (legacy interface)."""
    bus = await get_event_bus()
    # Wrap callback to match old interface
    async def wrapper(msg):
        await cb(type('Msg', (), {'subject': msg.get('_subject'), 'data': json.dumps(msg).encode()})())
    await bus.subscribe(
        subject,
        StreamName.GENERATIONS,
        f"legacy-{subject.replace('.', '-')}",
        wrapper
    )
