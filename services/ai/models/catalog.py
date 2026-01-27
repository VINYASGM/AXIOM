"""
Model Catalog - Multi-Tier Model Definitions

Defines available models organized by tier (Local, Balanced, High Accuracy, Frontier).
Implements accuracy-first routing per Architecture v2.1.

Core Philosophy: "Low accuracy models are expensive because verification failures trigger regeneration."
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal


class ModelTier(str, Enum):
    """Model classification tiers per Architecture v2.1"""
    LOCAL = "local"           # Privacy + Speed (runs on user hardware)
    BALANCED = "balanced"     # Speed + Quality (default for most tasks)
    HIGH_ACCURACY = "high_accuracy"  # Complex logic, debugging
    FRONTIER = "frontier"     # Novel problems, architectural reasoning


class TaskType(str, Enum):
    """Types of tasks for model selection"""
    CODE_GENERATION = "code_generation"
    CODE_REFACTORING = "code_refactoring"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    BUG_FIXING = "bug_fixing"
    ARCHITECTURE = "architecture"
    EXPLANATION = "explanation"
    SIMPLE_EDIT = "simple_edit"


@dataclass
class ModelSpec:
    """Specification for an LLM model."""
    id: str                          # Unique identifier
    name: str                        # Display name
    provider: str                    # openai, anthropic, google, deepseek, etc.
    tier: ModelTier                  # Classification tier
    context_window: int              # Max context tokens
    
    # Pricing (per 1M tokens)
    input_price: Decimal             # $/1M input tokens
    output_price: Decimal            # $/1M output tokens
    
    # Capabilities
    humaneval_score: float           # HumanEval benchmark (0-100)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    # Routing hints
    recommended_for: List[TaskType] = field(default_factory=list)
    not_recommended_for: List[TaskType] = field(default_factory=list)
    
    # Technical details
    api_model_name: str = ""         # Actual API model name
    supports_streaming: bool = True
    supports_function_calling: bool = True
    max_output_tokens: int = 4096
    
    # Status
    available: bool = True
    deprecated: bool = False
    
    def __post_init__(self):
        if not self.api_model_name:
            self.api_model_name = self.id
    
    @property
    def effective_cost_multiplier(self) -> float:
        """
        Cost multiplier based on expected verification success rate.
        Lower accuracy = more retries = higher effective cost.
        """
        if self.humaneval_score >= 90:
            return 1.1  # ~10% retry overhead
        elif self.humaneval_score >= 80:
            return 1.3  # ~30% retry overhead
        elif self.humaneval_score >= 70:
            return 1.6  # ~60% retry overhead
        else:
            return 2.0  # ~100% retry overhead (expect many failures)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Estimate cost for a request."""
        input_cost = (Decimal(input_tokens) / 1_000_000) * self.input_price
        output_cost = (Decimal(output_tokens) / 1_000_000) * self.output_price
        return input_cost + output_cost
    
    def estimate_effective_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Estimate cost including expected retries."""
        base_cost = self.estimate_cost(input_tokens, output_tokens)
        return base_cost * Decimal(str(self.effective_cost_multiplier))


# =============================================================================
# MODEL CATALOG (Architecture v2.1 - 2025-2026)
# =============================================================================

MODEL_CATALOG: Dict[str, ModelSpec] = {}


def register_model(model: ModelSpec):
    """Register a model in the catalog."""
    MODEL_CATALOG[model.id] = model


# -----------------------------------------------------------------------------
# CLASS_LOCAL (Privacy + Speed)
# -----------------------------------------------------------------------------

register_model(ModelSpec(
    id="qwen3-8b",
    name="Qwen3 8B",
    provider="local",
    tier=ModelTier.LOCAL,
    context_window=32768,
    input_price=Decimal("0"),
    output_price=Decimal("0"),
    humaneval_score=72.0,
    strengths=["Fast", "Privacy", "Multilingual", "No API costs"],
    weaknesses=["Complex reasoning", "Large codebases"],
    recommended_for=[TaskType.SIMPLE_EDIT, TaskType.DOCUMENTATION, TaskType.EXPLANATION],
    not_recommended_for=[TaskType.ARCHITECTURE, TaskType.BUG_FIXING],
    api_model_name="qwen3:8b",
))

register_model(ModelSpec(
    id="gemma3-4b",
    name="Gemma 3 4B",
    provider="local",
    tier=ModelTier.LOCAL,
    context_window=8192,
    input_price=Decimal("0"),
    output_price=Decimal("0"),
    humaneval_score=65.0,
    strengths=["Ultra-fast", "Lightweight", "Good for simple tasks"],
    weaknesses=["Limited context", "Complex code"],
    recommended_for=[TaskType.SIMPLE_EDIT],
    api_model_name="gemma3:4b",
))

register_model(ModelSpec(
    id="deepseek-coder-v2-7b",
    name="DeepSeek Coder V2 7B",
    provider="local",
    tier=ModelTier.LOCAL,
    context_window=16384,
    input_price=Decimal("0"),
    output_price=Decimal("0"),
    humaneval_score=78.0,
    strengths=["Pure coding specialist", "Fast", "Good code completion"],
    weaknesses=["General reasoning", "Documentation"],
    recommended_for=[TaskType.CODE_GENERATION, TaskType.CODE_REFACTORING],
    api_model_name="deepseek-coder-v2:7b",
))


# -----------------------------------------------------------------------------
# CLASS_BALANCED (Speed + Quality) - RECOMMENDED DEFAULT
# -----------------------------------------------------------------------------

register_model(ModelSpec(
    id="deepseek-v3",
    name="DeepSeek V3",
    provider="deepseek",
    tier=ModelTier.BALANCED,
    context_window=65536,
    input_price=Decimal("0.001"),      # $0.001 per 1M input
    output_price=Decimal("0.002"),     # $0.002 per 1M output
    humaneval_score=90.0,
    strengths=["Excellent HumanEval", "Very cheap", "Good reasoning", "Large context"],
    weaknesses=["Newer model, less battle-tested"],
    recommended_for=[TaskType.CODE_GENERATION, TaskType.CODE_REFACTORING, TaskType.BUG_FIXING],
    api_model_name="deepseek-chat",
))

register_model(ModelSpec(
    id="claude-haiku",
    name="Claude 3.5 Haiku",
    provider="anthropic",
    tier=ModelTier.BALANCED,
    context_window=200000,
    input_price=Decimal("0.25"),
    output_price=Decimal("1.25"),
    humaneval_score=85.0,
    strengths=["Fast reasoning", "Good instruction following", "Huge context"],
    weaknesses=["More expensive than DeepSeek"],
    recommended_for=[TaskType.EXPLANATION, TaskType.DOCUMENTATION],
    api_model_name="claude-3-5-haiku-latest",
))

register_model(ModelSpec(
    id="gemini-2-flash",
    name="Gemini 2.0 Flash",
    provider="google",
    tier=ModelTier.BALANCED,
    context_window=1000000,
    input_price=Decimal("0.075"),
    output_price=Decimal("0.30"),
    humaneval_score=82.0,
    strengths=["Massive context", "Fast", "Multimodal"],
    weaknesses=["Code quality slightly below Claude/GPT"],
    recommended_for=[TaskType.DOCUMENTATION, TaskType.EXPLANATION],
    api_model_name="gemini-2.0-flash",
))

register_model(ModelSpec(
    id="gpt-4o-mini",
    name="GPT-4o Mini",
    provider="openai",
    tier=ModelTier.BALANCED,
    context_window=128000,
    input_price=Decimal("0.15"),
    output_price=Decimal("0.60"),
    humaneval_score=80.0,
    strengths=["Good all-rounder", "Reliable", "Function calling"],
    weaknesses=["Slightly less accurate than full GPT-4o"],
    recommended_for=[TaskType.CODE_GENERATION, TaskType.SIMPLE_EDIT],
    api_model_name="gpt-4o-mini",
))


# -----------------------------------------------------------------------------
# CLASS_HIGH_ACCURACY (Complex Logic)
# -----------------------------------------------------------------------------

register_model(ModelSpec(
    id="claude-sonnet",
    name="Claude Sonnet 4",
    provider="anthropic",
    tier=ModelTier.HIGH_ACCURACY,
    context_window=200000,
    input_price=Decimal("3.0"),
    output_price=Decimal("15.0"),
    humaneval_score=92.0,
    strengths=["Excellent coding", "Robust debugging", "Strong reasoning"],
    weaknesses=["Higher cost", "Slower than Haiku"],
    recommended_for=[TaskType.BUG_FIXING, TaskType.CODE_REFACTORING, TaskType.ARCHITECTURE],
    api_model_name="claude-sonnet-4-20250514",
))

register_model(ModelSpec(
    id="gpt-4o",
    name="GPT-4o",
    provider="openai",
    tier=ModelTier.HIGH_ACCURACY,
    context_window=128000,
    input_price=Decimal("2.50"),
    output_price=Decimal("10.0"),
    humaneval_score=90.0,
    strengths=["General purpose strength", "Reliable", "Well-documented"],
    weaknesses=["Cost", "Slightly slower"],
    recommended_for=[TaskType.CODE_GENERATION, TaskType.BUG_FIXING],
    api_model_name="gpt-4o",
))

register_model(ModelSpec(
    id="gemini-2-pro",
    name="Gemini 2.5 Pro",
    provider="google",
    tier=ModelTier.HIGH_ACCURACY,
    context_window=1000000,
    input_price=Decimal("1.25"),
    output_price=Decimal("10.0"),
    humaneval_score=88.0,
    strengths=["Massive context (1M+)", "Good for large codebases"],
    weaknesses=["Slightly behind Claude/GPT on code"],
    recommended_for=[TaskType.ARCHITECTURE, TaskType.DOCUMENTATION],
    api_model_name="gemini-2.5-pro-preview-05-06",
))


# -----------------------------------------------------------------------------
# CLASS_FRONTIER (Novel Problems)
# -----------------------------------------------------------------------------

register_model(ModelSpec(
    id="claude-opus",
    name="Claude Opus 4",
    provider="anthropic",
    tier=ModelTier.FRONTIER,
    context_window=200000,
    input_price=Decimal("15.0"),
    output_price=Decimal("75.0"),
    humaneval_score=95.0,
    strengths=["Best-in-class coding", "Architectural reasoning", "Novel problem solving"],
    weaknesses=["Expensive", "Slower"],
    recommended_for=[TaskType.ARCHITECTURE, TaskType.BUG_FIXING],
    api_model_name="claude-opus-4-20250514",
))

register_model(ModelSpec(
    id="o1",
    name="OpenAI o1",
    provider="openai",
    tier=ModelTier.FRONTIER,
    context_window=200000,
    input_price=Decimal("15.0"),
    output_price=Decimal("60.0"),
    humaneval_score=94.0,
    strengths=["Deep reasoning", "Complex problem solving", "Math/logic"],
    weaknesses=["Very expensive", "Slow"],
    recommended_for=[TaskType.ARCHITECTURE, TaskType.BUG_FIXING],
    api_model_name="o1",
    supports_streaming=False,  # o1 doesn't support streaming
))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model(model_id: str) -> Optional[ModelSpec]:
    """Get a model by ID."""
    return MODEL_CATALOG.get(model_id)


def get_models_by_tier(tier: ModelTier) -> List[ModelSpec]:
    """Get all models in a tier."""
    return [m for m in MODEL_CATALOG.values() if m.tier == tier and m.available]


def get_models_by_provider(provider: str) -> List[ModelSpec]:
    """Get all models from a provider."""
    return [m for m in MODEL_CATALOG.values() if m.provider == provider and m.available]


def get_recommended_model(task_type: TaskType, tier: Optional[ModelTier] = None) -> Optional[ModelSpec]:
    """Get the recommended model for a task type."""
    candidates = []
    
    for model in MODEL_CATALOG.values():
        if not model.available:
            continue
        if tier and model.tier != tier:
            continue
        if task_type in model.not_recommended_for:
            continue
        if task_type in model.recommended_for:
            candidates.append((model, 2))  # Explicitly recommended
        else:
            candidates.append((model, 1))  # Not explicitly against
    
    if not candidates:
        return None
    
    # Sort by: recommendation score desc, humaneval desc, cost asc
    candidates.sort(key=lambda x: (-x[1], -x[0].humaneval_score, x[0].input_price))
    return candidates[0][0]


def get_default_model() -> ModelSpec:
    """Get the default model (DeepSeek V3 per architecture recommendation)."""
    return MODEL_CATALOG.get("deepseek-v3") or list(MODEL_CATALOG.values())[0]


def get_next_tier_model(current_model: ModelSpec) -> Optional[ModelSpec]:
    """Get a model from the next accuracy tier (for auto-upgrade on failure)."""
    tier_order = [ModelTier.LOCAL, ModelTier.BALANCED, ModelTier.HIGH_ACCURACY, ModelTier.FRONTIER]
    
    try:
        current_idx = tier_order.index(current_model.tier)
    except ValueError:
        return None
    
    if current_idx >= len(tier_order) - 1:
        return None  # Already at highest tier
    
    next_tier = tier_order[current_idx + 1]
    next_tier_models = get_models_by_tier(next_tier)
    
    if not next_tier_models:
        return None
    
    # Return highest accuracy model in next tier
    return max(next_tier_models, key=lambda m: m.humaneval_score)


def list_all_models() -> List[Dict[str, Any]]:
    """List all models with their key info."""
    return [
        {
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "tier": m.tier.value,
            "humaneval": m.humaneval_score,
            "input_price": float(m.input_price),
            "output_price": float(m.output_price),
            "context_window": m.context_window,
            "available": m.available
        }
        for m in MODEL_CATALOG.values()
    ]
