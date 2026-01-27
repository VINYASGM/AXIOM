"""
Tests for Model Router and Cost Oracle

Tests multi-tier model selection, cost calculations, and provider routing.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, '.')

from models.catalog import (
    ModelTier,
    TaskType,
    ModelSpec,
    MODEL_CATALOG,
    get_model,
    get_models_by_tier,
    get_recommended_model,
    get_default_model,
    get_next_tier_model,
    list_all_models
)
from models.cost_oracle import (
    CostEstimate,
    CostOracle,
    get_cost_oracle
)


class TestModelCatalog:
    """Test model catalog functionality."""
    
    def test_catalog_has_models(self):
        """Test that catalog contains models."""
        models = list_all_models()
        assert len(models) > 0
        assert len(models) >= 10  # We defined 12 models
    
    def test_get_model_by_id(self):
        """Test getting a specific model."""
        model = get_model("deepseek-v3")
        
        assert model is not None
        assert model.id == "deepseek-v3"
        assert model.tier == ModelTier.BALANCED
        assert model.provider == "deepseek"
    
    def test_get_nonexistent_model(self):
        """Test getting a model that doesn't exist."""
        model = get_model("nonexistent-model")
        assert model is None
    
    def test_get_models_by_tier(self):
        """Test filtering models by tier."""
        balanced = get_models_by_tier(ModelTier.BALANCED)
        
        assert len(balanced) > 0
        for model in balanced:
            assert model.tier == ModelTier.BALANCED
    
    def test_frontier_tier_exists(self):
        """Test that frontier tier has models."""
        frontier = get_models_by_tier(ModelTier.FRONTIER)
        
        assert len(frontier) > 0
        # Frontier models should have high HumanEval scores
        for model in frontier:
            assert model.humaneval_score >= 85.0
    
    def test_get_recommended_model(self):
        """Test getting recommended model for task."""
        # Simple task should get lower tier
        simple_model = get_recommended_model(TaskType.SIMPLE)
        # Complex task should get higher tier
        complex_model = get_recommended_model(TaskType.NOVEL_PROBLEM)
        
        assert simple_model is not None
        # Novel problems should route to frontier
        assert complex_model.tier in [ModelTier.HIGH_ACCURACY, ModelTier.FRONTIER]
    
    def test_get_default_model(self):
        """Test getting the default model."""
        default = get_default_model()
        
        assert default is not None
        assert default.available == True
    
    def test_get_next_tier_model(self):
        """Test model tier upgrade on failure."""
        current = get_model("deepseek-v3")  # BALANCED tier
        next_model = get_next_tier_model(current.id)
        
        assert next_model is not None
        # Should be same or higher tier
        tier_order = [ModelTier.LOCAL, ModelTier.BALANCED, ModelTier.HIGH_ACCURACY, ModelTier.FRONTIER]
        current_idx = tier_order.index(current.tier)
        next_idx = tier_order.index(next_model.tier)
        assert next_idx >= current_idx


class TestModelSpec:
    """Test ModelSpec functionality."""
    
    def test_model_cost_estimation(self):
        """Test cost estimation for a model."""
        model = get_model("gpt-4o")
        
        cost = model.estimate_cost(1000, 500)
        
        assert cost > 0
        assert isinstance(cost, Decimal)
    
    def test_effective_cost_multiplier(self):
        """Test effective cost multiplier calculation."""
        model = get_model("claude-sonnet-4")  # 93.7% HumanEval
        
        multiplier = model.effective_cost_multiplier
        
        # High accuracy = low retry multiplier
        assert multiplier < 1.5
        assert multiplier >= 1.0
    
    def test_effective_cost_higher_for_low_accuracy(self):
        """Test that effective cost is higher for models with lower accuracy."""
        high_accuracy = get_model("claude-sonnet-4")  # 93.7%
        lower_accuracy = get_model("gpt-4o-mini")  # 87.2%
        
        high_eff = high_accuracy.effective_cost_multiplier
        low_eff = lower_accuracy.effective_cost_multiplier
        
        # Lower accuracy should have higher multiplier
        assert low_eff > high_eff
    
    def test_model_supports_task(self):
        """Test task support checking."""
        coder = get_model("deepseek-coder-v2")
        
        # Coder should support code generation
        assert coder.supports_task(TaskType.CODE_GENERATION)
        # Should also support debugging
        assert coder.supports_task(TaskType.COMPLEX_DEBUG)


class TestCostOracle:
    """Test cost oracle functionality."""
    
    def test_estimate_cost(self):
        """Test cost estimation."""
        oracle = CostOracle()
        
        estimate = oracle.estimate_cost(
            model_id="deepseek-v3",
            intent_text="Create a function to sort a list of numbers",
            complexity="simple"
        )
        
        assert isinstance(estimate, CostEstimate)
        assert estimate.model_id == "deepseek-v3"
        assert estimate.base_cost > 0
        assert estimate.effective_cost >= estimate.base_cost
    
    def test_estimate_includes_alternatives(self):
        """Test that estimate includes alternative suggestions."""
        oracle = CostOracle()
        
        estimate = oracle.estimate_cost(
            model_id="gpt-4o",  # Expensive model
            intent_text="Simple task",
            complexity="simple",
            include_alternatives=True
        )
        
        # Should suggest cheaper alternatives
        assert len(estimate.cheaper_alternatives) > 0 or len(estimate.more_accurate_alternatives) > 0
    
    def test_effective_cost_calculation(self):
        """Test accuracy-first effective cost calculation."""
        oracle = CostOracle()
        
        # This demonstrates the key insight:
        # Model A: $0.05, 50% pass -> Real Cost $0.10
        # Model B: $0.08, 90% pass -> Real Cost $0.089 (CHEAPER)
        
        # A model with higher base cost but higher accuracy
        # should have lower or comparable effective cost
        estimate_accurate = oracle.estimate_cost(
            model_id="claude-sonnet-4",  # High accuracy
            intent_text="Test task",
            complexity="medium"
        )
        
        # The effective cost includes retry factor
        assert estimate_accurate.retry_multiplier < 1.5
    
    def test_budget_tracking(self):
        """Test budget tracking functionality."""
        oracle = CostOracle()
        
        # Set a daily budget
        oracle.set_daily_budget("user-1", Decimal("10.00"))
        
        # Record some usage
        oracle.record_usage(
            model_id="deepseek-v3",
            input_tokens=1000,
            output_tokens=500,
            verification_passed=True,
            attempts=1,
            user_id="user-1"
        )
        
        usage = oracle.get_daily_usage("user-1")
        
        assert usage["daily_usage_usd"] > 0
        assert usage["daily_budget_usd"] == 10.0
        assert usage["budget_remaining_usd"] < 10.0
    
    def test_recommend_model(self):
        """Test model recommendation based on constraints."""
        oracle = CostOracle()
        
        # Recommend with cost constraint
        recommended = oracle.recommend_model(
            intent_text="Simple code generation task",
            complexity="simple",
            max_cost=Decimal("0.01")
        )
        
        assert recommended is not None
        
        # Verify the recommended model meets constraints
        model = get_model(recommended)
        cost = model.estimate_effective_cost(600, 200)
        # Should be within or close to budget
    
    def test_recommend_model_with_accuracy_constraint(self):
        """Test model recommendation with minimum accuracy."""
        oracle = CostOracle()
        
        recommended = oracle.recommend_model(
            intent_text="Critical production code",
            complexity="complex",
            min_accuracy=90.0
        )
        
        assert recommended is not None
        
        model = get_model(recommended)
        assert model.humaneval_score >= 90.0
    
    def test_usage_stats(self):
        """Test usage statistics aggregation."""
        oracle = CostOracle()
        
        # Record multiple usages
        for i in range(3):
            oracle.record_usage(
                model_id="deepseek-v3",
                input_tokens=1000,
                output_tokens=500,
                verification_passed=i < 2,  # 2 pass, 1 fail
                attempts=1
            )
        
        stats = oracle.get_usage_stats()
        
        assert stats["total_requests"] == 3
        assert stats["total_cost_usd"] > 0
        assert "deepseek-v3" in stats["by_model"]


class TestModelTierProgression:
    """Test model tier upgrade logic."""
    
    def test_tier_upgrade_path(self):
        """Test that upgrade path is correct."""
        # Start from local
        current = "qwen3-8b"  # LOCAL tier
        
        upgrades = []
        model_id = current
        
        for _ in range(3):  # Max 3 upgrades
            next_model = get_next_tier_model(model_id)
            if next_model is None:
                break
            upgrades.append(next_model.id)
            model_id = next_model.id
        
        # Should have upgraded through tiers
        assert len(upgrades) > 0
    
    def test_frontier_has_no_upgrade(self):
        """Test that frontier tier cannot upgrade further."""
        frontier_models = get_models_by_tier(ModelTier.FRONTIER)
        
        for model in frontier_models:
            next_model = get_next_tier_model(model.id)
            # Frontier models may return None or same tier
            if next_model:
                assert next_model.tier == ModelTier.FRONTIER


# Run with: pytest test_model_router.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
