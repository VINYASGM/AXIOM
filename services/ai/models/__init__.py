"""
Models Package - Multi-Tier Model Infrastructure

Exports model catalog, cost oracle, and cloud providers for
accuracy-first routing per Architecture v2.1.
"""

from .catalog import (
    ModelTier,
    TaskType,
    ModelSpec,
    MODEL_CATALOG,
    register_model,
    get_model,
    get_models_by_tier,
    get_models_by_provider,
    get_recommended_model,
    get_default_model,
    get_next_tier_model,
    list_all_models
)

from .cost_oracle import (
    CostEstimate,
    UsageRecord,
    CostOracle,
    get_cost_oracle
)

from .providers import (
    AnthropicProvider,
    GoogleProvider,
    DeepSeekProvider,
    OpenAIEnhancedProvider,
    create_provider,
    get_available_providers
)


__all__ = [
    # Catalog
    "ModelTier",
    "TaskType", 
    "ModelSpec",
    "MODEL_CATALOG",
    "register_model",
    "get_model",
    "get_models_by_tier",
    "get_models_by_provider",
    "get_recommended_model",
    "get_default_model",
    "get_next_tier_model",
    "list_all_models",
    
    # Cost Oracle
    "CostEstimate",
    "UsageRecord",
    "CostOracle",
    "get_cost_oracle",
    
    # Providers
    "AnthropicProvider",
    "GoogleProvider",
    "DeepSeekProvider",
    "OpenAIEnhancedProvider",
    "create_provider",
    "get_available_providers"
]
