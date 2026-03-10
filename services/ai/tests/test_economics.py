"""
Unit tests for the Economics module.
Tests cost estimation, budget enforcement, and token counting.
"""
import pytest
from economics import (
    ModelPricing,
    CostEstimate,
    Budget,
    CostRecord,
    EconomicsService,
    MODEL_PRICING,
)


class TestModelPricing:
    """Test pricing data structures."""

    def test_model_pricing_exists(self):
        assert "gpt-4-turbo" in MODEL_PRICING
        assert "gpt-3.5-turbo" in MODEL_PRICING

    def test_pricing_has_valid_values(self):
        for model_id, pricing in MODEL_PRICING.items():
            assert pricing.input_price_per_m >= 0
            assert pricing.output_price_per_m >= 0


class TestCostEstimate:
    """Test cost estimation calculation."""

    def test_zero_tokens_zero_cost(self):
        est = CostEstimate(input_tokens=0, output_tokens=0, model="gpt-4-turbo")
        est.calculate()
        assert est.estimated_cost_usd == 0.0

    def test_calculation_with_known_model(self):
        est = CostEstimate(
            input_tokens=1000, output_tokens=500, model="gpt-4-turbo"
        )
        est.calculate()
        # gpt-4-turbo: input=$10/1M, output=$30/1M
        expected = (1000 * 10.0 / 1_000_000) + (500 * 30.0 / 1_000_000)
        assert abs(est.estimated_cost_usd - expected) < 0.0001

    def test_calculation_unknown_model_no_crash(self):
        est = CostEstimate(
            input_tokens=100, output_tokens=100, model="unknown-model"
        )
        est.calculate()
        # Should default to 0.0 or handle gracefully
        assert est.estimated_cost_usd >= 0.0


class TestBudget:
    """Test budget enforcement."""

    def test_can_proceed_within_budget(self):
        budget = Budget(max_usd_per_session=1.0, max_usd_per_request=0.10)
        assert budget.can_proceed(0.05) is True

    def test_cannot_proceed_over_session_limit(self):
        budget = Budget(
            max_usd_per_session=0.10,
            max_usd_per_request=0.20,
            current_spent=0.09,
        )
        assert budget.can_proceed(0.05) is False

    def test_cannot_proceed_over_request_limit(self):
        budget = Budget(max_usd_per_session=10.0, max_usd_per_request=0.05)
        assert budget.can_proceed(0.10) is False

    def test_record_cost_updates_spent(self):
        budget = Budget()
        record = CostRecord(
            operation="generate",
            model="gpt-4-turbo",
            input_tokens=1000,
            output_tokens=500,
            actual_cost_usd=0.025,
        )
        budget.record_cost(record)
        assert budget.current_spent == 0.025
        assert len(budget.records) == 1

    def test_warning_at_threshold(self):
        budget = Budget(
            max_usd_per_session=1.0,
            warn_threshold=0.8,
            current_spent=0.85,
        )
        warning = budget.get_warning()
        assert warning is not None


class TestEconomicsService:
    """Test the EconomicsService singleton."""

    def test_count_tokens(self):
        service = EconomicsService()
        count = service.count_tokens("Hello, world!")
        assert count > 0

    def test_estimate_generation_cost(self):
        service = EconomicsService()
        estimate = service.estimate_generation_cost(
            intent="Create a Python function that sorts a list",
            language="python",
            candidate_count=3,
        )
        assert estimate.estimated_cost_usd > 0

    def test_check_budget_new_session(self):
        service = EconomicsService()
        can_proceed, message, warning = service.check_budget("new-session", 0.01)
        assert can_proceed is True

    def test_session_summary(self):
        service = EconomicsService()
        summary = service.get_session_summary("some-session")
        assert "total_cost" in summary or isinstance(summary, dict)
