"""
Dynamic Model Configuration Service

Database-driven model configuration as specified in design.md Section 3.3.
Replaces hardcoded model catalogs with cached database lookups.
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from threading import Lock


class ModelTier(Enum):
    """Model capability tiers per AXIOM architecture."""
    LOCAL = "local"           # Privacy + Speed (Qwen3-8B, etc.)
    BALANCED = "balanced"     # Speed + Quality (DeepSeek-V3)
    HIGH_ACCURACY = "high_accuracy"  # Complex Logic (Claude Sonnet, GPT-4o)
    FRONTIER = "frontier"     # Novel Problems (Claude Opus)


@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""
    name: str
    provider: str
    model_id: str
    tier: ModelTier
    cost_per_1k: float
    accuracy: float
    capabilities: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "provider": self.provider,
            "model_id": self.model_id,
            "tier": self.tier.value,
            "cost_per_1k": self.cost_per_1k,
            "accuracy": self.accuracy,
            "capabilities": self.capabilities,
            "is_active": self.is_active
        }


class DynamicModelConfig:
    """
    Database-driven model configuration manager.
    
    Provides cached access to model configurations stored in PostgreSQL.
    Cache refreshes automatically after TTL expires.
    
    Usage:
        config = DynamicModelConfig(db_pool)
        await config.initialize()
        
        models = await config.get_models_by_tier(ModelTier.BALANCED)
        model = await config.get_model_by_name("deepseek-v3")
    """
    
    def __init__(self, db_pool, cache_ttl: int = 60):
        """
        Initialize the dynamic model config.
        
        Args:
            db_pool: asyncpg connection pool
            cache_ttl: Cache time-to-live in seconds (default: 60s)
        """
        self._pool = db_pool
        self._cache_ttl = cache_ttl
        self._cache: Dict[str, ModelConfig] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._lock = Lock()
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the config cache from database."""
        try:
            await self._load_from_database()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize DynamicModelConfig: {e}")
            return False
    
    async def get_models_by_tier(self, tier: ModelTier) -> List[ModelConfig]:
        """
        Get all active models for a given tier.
        
        Args:
            tier: The model tier to filter by
            
        Returns:
            List of active ModelConfig objects for that tier
        """
        await self._refresh_cache_if_needed()
        
        return [
            config for config in self._cache.values()
            if config.tier == tier and config.is_active
        ]
    
    async def get_model_by_name(self, name: str) -> Optional[ModelConfig]:
        """
        Get a specific model configuration by name.
        
        Args:
            name: The model name (e.g., "deepseek-v3")
            
        Returns:
            ModelConfig if found, None otherwise
        """
        await self._refresh_cache_if_needed()
        return self._cache.get(name)
    
    async def get_all_active_models(self) -> List[ModelConfig]:
        """Get all active model configurations."""
        await self._refresh_cache_if_needed()
        return [c for c in self._cache.values() if c.is_active]
    
    async def get_default_model(self, tier: Optional[ModelTier] = None) -> Optional[ModelConfig]:
        """
        Get the best default model, optionally filtered by tier.
        
        Selection criteria: highest accuracy, then lowest cost.
        
        Args:
            tier: Optional tier filter
            
        Returns:
            Best ModelConfig or None
        """
        await self._refresh_cache_if_needed()
        
        candidates = [c for c in self._cache.values() if c.is_active]
        
        if tier:
            candidates = [c for c in candidates if c.tier == tier]
        
        if not candidates:
            return None
        
        # Sort by accuracy (desc), then cost (asc)
        candidates.sort(key=lambda m: (-m.accuracy, m.cost_per_1k))
        return candidates[0]
    
    async def _refresh_cache_if_needed(self):
        """Refresh cache if TTL has expired."""
        now = datetime.utcnow()
        
        if (self._cache_timestamp is None or 
            (now - self._cache_timestamp).total_seconds() > self._cache_ttl):
            
            with self._lock:
                # Double-check after acquiring lock
                if (self._cache_timestamp is None or 
                    (now - self._cache_timestamp).total_seconds() > self._cache_ttl):
                    await self._load_from_database()
                    self._cache_timestamp = now
    
    async def _load_from_database(self):
        """Load all active model configurations from database."""
        if not self._pool:
            print("Warning: No database pool available for model config")
            self._load_fallback_models()
            return
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT name, provider, model_id, tier, 
                           cost_per_1k_tokens, accuracy_score, 
                           capabilities, is_active
                    FROM model_configurations
                    WHERE is_active = TRUE
                """)
                
                self._cache = {}
                for row in rows:
                    tier_str = row['tier']
                    tier = ModelTier(tier_str) if tier_str else ModelTier.BALANCED
                    
                    capabilities = row['capabilities']
                    if isinstance(capabilities, str):
                        capabilities = json.loads(capabilities)
                    
                    config = ModelConfig(
                        name=row['name'],
                        provider=row['provider'],
                        model_id=row['model_id'],
                        tier=tier,
                        cost_per_1k=float(row['cost_per_1k_tokens'] or 0),
                        accuracy=float(row['accuracy_score'] or 0),
                        capabilities=capabilities or {},
                        is_active=row['is_active']
                    )
                    self._cache[config.name] = config
                
                print(f"Loaded {len(self._cache)} model configurations from database")
        
        except Exception as e:
            print(f"Error loading model configs from database: {e}")
            self._load_fallback_models()
    
    def _load_fallback_models(self):
        """Load hardcoded fallback models when database is unavailable."""
        fallbacks = [
            ModelConfig("mock", "mock", "mock-fast", ModelTier.LOCAL, 0.0, 0.5, {"testing": True}),
            ModelConfig("deepseek-v3", "deepseek", "deepseek-chat", ModelTier.BALANCED, 0.002, 0.90, {"code_generation": True}),
            ModelConfig("gpt-4-turbo", "openai", "gpt-4-turbo", ModelTier.HIGH_ACCURACY, 0.03, 0.88, {"code_generation": True}),
        ]
        
        self._cache = {m.name: m for m in fallbacks}
        print(f"Loaded {len(self._cache)} fallback model configurations")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "model_count": len(self._cache),
            "cache_age_seconds": (datetime.utcnow() - self._cache_timestamp).total_seconds() if self._cache_timestamp else None,
            "cache_ttl": self._cache_ttl,
            "models": list(self._cache.keys())
        }


# Global singleton for easy access
_global_model_config: Optional[DynamicModelConfig] = None


def get_model_config() -> Optional[DynamicModelConfig]:
    """Get the global model config instance."""
    return _global_model_config


async def init_model_config(db_pool, cache_ttl: int = 60) -> DynamicModelConfig:
    """Initialize and return the global model config."""
    global _global_model_config
    _global_model_config = DynamicModelConfig(db_pool, cache_ttl)
    await _global_model_config.initialize()
    return _global_model_config
