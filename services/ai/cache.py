"""
Semantic Cache

LRU cache with semantic similarity matching for intent→code caching.
Ported from UACP's gateway/internal/cache/semantic.go

Reduces API costs by caching similar intents and their generated code.
"""
import hashlib
import math
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from threading import Lock, Thread
import json


@dataclass
class CacheEntry:
    """A cached intent→code mapping."""
    key: str
    query: str  # Original intent
    response: str  # Generated code
    model: str
    embedding: List[float] = field(default_factory=list)
    hit_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    ttl_seconds: int = 3600  # 1 hour default
    
    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def touch(self):
        """Update access time and hit count."""
        self.last_access = time.time()
        self.hit_count += 1
    
    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "query": self.query[:100] + "..." if len(self.query) > 100 else self.query,
            "model": self.model,
            "hit_count": self.hit_count,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "is_expired": self.is_expired
        }


def _generate_key(query: str, model: str) -> str:
    """Generate cache key from query and model."""
    h = hashlib.sha256()
    h.update(query.encode())
    h.update(model.encode())
    return h.hexdigest()[:16]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


class SemanticCache:
    """
    LRU cache with semantic similarity matching.
    
    Features:
    - Exact match lookup by key
    - Semantic similarity search for near-misses
    - TTL-based expiration
    - LRU eviction when at capacity
    - Background cleanup thread
    
    Usage:
        cache = SemanticCache(max_size=1000)
        
        # Check cache
        entry = await cache.get("Create fibonacci function", "gpt-4", embedding)
        if entry:
            return entry.response  # Cache hit!
        
        # Generate and cache
        code = await generate(...)
        await cache.set("Create fibonacci function", code, "gpt-4", embedding)
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_seconds: int = 3600,
        similarity_threshold: float = 0.92,
        enable_cleanup: bool = True
    ):
        self.entries: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self.similarity_threshold = similarity_threshold
        self._lock = Lock()
        
        # Stats
        self._hits = 0
        self._misses = 0
        self._semantic_hits = 0
        
        # Background cleanup
        if enable_cleanup:
            self._cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
    
    async def get(
        self,
        query: str,
        model: str,
        embedding: Optional[List[float]] = None
    ) -> Optional[CacheEntry]:
        """
        Check cache for a match.
        
        Args:
            query: The intent query
            model: Model name
            embedding: Optional query embedding for semantic search
        
        Returns:
            CacheEntry if found, None otherwise
        """
        key = _generate_key(query, model)
        
        with self._lock:
            # Exact match
            if key in self.entries:
                entry = self.entries[key]
                if not entry.is_expired:
                    entry.touch()
                    self._hits += 1
                    return entry
                else:
                    del self.entries[key]
            
            # Semantic similarity search (if embedding provided)
            if embedding and len(embedding) > 0:
                best_match: Optional[CacheEntry] = None
                best_score = 0.0
                
                for entry in self.entries.values():
                    if entry.is_expired or not entry.embedding:
                        continue
                    if entry.model != model:
                        continue
                    
                    score = _cosine_similarity(embedding, entry.embedding)
                    if score > best_score and score >= self.similarity_threshold:
                        best_score = score
                        best_match = entry
                
                if best_match:
                    best_match.touch()
                    self._semantic_hits += 1
                    self._hits += 1
                    return best_match
            
            self._misses += 1
            return None
    
    async def set(
        self,
        query: str,
        response: str,
        model: str,
        embedding: Optional[List[float]] = None,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Store a response in the cache.
        
        Returns:
            Cache key
        """
        key = _generate_key(query, model)
        
        entry = CacheEntry(
            key=key,
            query=query,
            response=response,
            model=model,
            embedding=embedding or [],
            ttl_seconds=ttl_seconds or self.default_ttl
        )
        
        with self._lock:
            # Evict if at capacity
            while len(self.entries) >= self.max_size:
                self._evict_one()
            
            self.entries[key] = entry
        
        return key
    
    def delete(self, key: str) -> bool:
        """Delete a specific entry."""
        with self._lock:
            if key in self.entries:
                del self.entries[key]
                return True
            return False
    
    def clear(self):
        """Clear all entries."""
        with self._lock:
            self.entries.clear()
            self._hits = 0
            self._misses = 0
            self._semantic_hits = 0
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            
            return {
                "size": len(self.entries),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "semantic_hits": self._semantic_hits,
                "hit_rate": round(hit_rate, 3),
                "total_requests": total
            }
    
    def list_entries(self, limit: int = 20) -> List[dict]:
        """List recent cache entries."""
        with self._lock:
            sorted_entries = sorted(
                self.entries.values(),
                key=lambda e: e.last_access,
                reverse=True
            )
            return [e.to_dict() for e in sorted_entries[:limit]]
    
    def _evict_one(self):
        """Evict the least recently used entry (must hold lock)."""
        if not self.entries:
            return
        
        oldest_key = min(
            self.entries.keys(),
            key=lambda k: self.entries[k].last_access
        )
        del self.entries[oldest_key]
    
    def _cleanup_loop(self):
        """Background thread for cleaning expired entries."""
        while True:
            time.sleep(60)  # Check every minute
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove all expired entries."""
        with self._lock:
            expired = [
                key for key, entry in self.entries.items()
                if entry.is_expired
            ]
            for key in expired:
                del self.entries[key]
    
    def to_json(self) -> str:
        """Serialize cache for debugging."""
        with self._lock:
            return json.dumps({
                "entries": [e.to_dict() for e in self.entries.values()],
                "stats": self.stats()
            }, indent=2)


# Singleton instance for global access
_global_cache: Optional[SemanticCache] = None


def get_cache() -> SemanticCache:
    """Get the global semantic cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = SemanticCache()
    return _global_cache


def init_cache(**kwargs) -> SemanticCache:
    """Initialize the global cache with custom settings."""
    global _global_cache
    _global_cache = SemanticCache(**kwargs)
    return _global_cache
