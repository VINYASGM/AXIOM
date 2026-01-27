"""
Cost Oracle - Effective Cost Calculation

Calculates true costs including verification retry factor.
Implements the accuracy-first economic model from Architecture v2.1.

Key insight: "Model A ($0.05, 50% pass) -> Real Cost $0.10 (2 runs)
              Model B ($0.08, 90% pass) -> Real Cost $0.09 (1.1 runs) -> CHEAPER"
"""
from decimal import Decimal
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

from .catalog import ModelSpec, MODEL_CATALOG, get_model, ModelTier


@dataclass
class CostEstimate:
    """Detailed cost estimate for a generation request."""
    model_id: str
    model_name: str
    tier: str
    
    # Base costs
    estimated_input_tokens: int
    estimated_output_tokens: int
    base_cost: Decimal
    
    # Effective costs (including retry factor)
    effective_cost: Decimal
    retry_multiplier: float
    expected_attempts: float
    
    # Comparison data
    cheaper_alternatives: List[Dict] = field(default_factory=list)
    more_accurate_alternatives: List[Dict] = field(default_factory=list)
    
    # Budget impact
    budget_remaining: Optional[Decimal] = None
    budget_usage_percent: Optional[float] = None
    within_budget: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "tier": self.tier,
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "base_cost_usd": float(self.base_cost),
            "effective_cost_usd": float(self.effective_cost),
            "retry_multiplier": self.retry_multiplier,
            "expected_attempts": self.expected_attempts,
            "cheaper_alternatives": self.cheaper_alternatives,
            "more_accurate_alternatives": self.more_accurate_alternatives,
            "budget_remaining_usd": float(self.budget_remaining) if self.budget_remaining else None,
            "budget_usage_percent": self.budget_usage_percent,
            "within_budget": self.within_budget
        }


@dataclass
class UsageRecord:
    """Record of model usage for tracking."""
    model_id: str
    input_tokens: int
    output_tokens: int
    cost: Decimal
    verification_passed: bool
    attempts: int
    timestamp: datetime


class CostOracle:
    """
    Oracle for estimating and tracking generation costs.
    
    Features:
    - Effective cost calculation with retry factors
    - Budget tracking and enforcement
    - Historical usage analysis
    - Cost comparison across models
    """
    
    # Average tokens per character for estimation
    TOKENS_PER_CHAR = 0.25
    
    # Average output tokens by task complexity
    OUTPUT_TOKENS_BY_COMPLEXITY = {
        "simple": 200,
        "medium": 500,
        "complex": 1500,
        "very_complex": 3000
    }
    
    def __init__(self):
        self.usage_history: List[UsageRecord] = []
        self.daily_budgets: Dict[str, Decimal] = {}  # user_id -> daily budget
        self.daily_usage: Dict[str, Decimal] = {}    # user_id -> today's usage
        self._last_reset: datetime = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    def estimate_cost(
        self,
        model_id: str,
        intent_text: str,
        complexity: str = "medium",
        user_id: Optional[str] = None,
        include_alternatives: bool = True
    ) -> CostEstimate:
        """
        Estimate the cost of a generation request.
        
        Args:
            model_id: Model to use
            intent_text: The user's intent text
            complexity: Estimated complexity (simple, medium, complex, very_complex)
            user_id: User ID for budget tracking
            include_alternatives: Whether to include cheaper/better alternatives
            
        Returns:
            Detailed cost estimate
        """
        model = get_model(model_id)
        if not model:
            raise ValueError(f"Unknown model: {model_id}")
        
        # Estimate tokens
        input_tokens = int(len(intent_text) * self.TOKENS_PER_CHAR) + 500  # +500 for system prompt
        output_tokens = self.OUTPUT_TOKENS_BY_COMPLEXITY.get(complexity, 500)
        
        # Calculate costs
        base_cost = model.estimate_cost(input_tokens, output_tokens)
        effective_cost = model.estimate_effective_cost(input_tokens, output_tokens)
        retry_multiplier = model.effective_cost_multiplier
        expected_attempts = retry_multiplier
        
        # Find alternatives
        cheaper_alternatives = []
        more_accurate_alternatives = []
        
        if include_alternatives:
            for other_id, other_model in MODEL_CATALOG.items():
                if other_id == model_id or not other_model.available:
                    continue
                
                other_effective = other_model.estimate_effective_cost(input_tokens, output_tokens)
                
                # Cheaper effective cost
                if other_effective < effective_cost:
                    cheaper_alternatives.append({
                        "model_id": other_id,
                        "model_name": other_model.name,
                        "tier": other_model.tier.value,
                        "effective_cost_usd": float(other_effective),
                        "savings_usd": float(effective_cost - other_effective),
                        "humaneval": other_model.humaneval_score
                    })
                
                # More accurate (higher HumanEval)
                if other_model.humaneval_score > model.humaneval_score:
                    more_accurate_alternatives.append({
                        "model_id": other_id,
                        "model_name": other_model.name,
                        "tier": other_model.tier.value,
                        "effective_cost_usd": float(other_effective),
                        "humaneval": other_model.humaneval_score,
                        "accuracy_gain": other_model.humaneval_score - model.humaneval_score
                    })
            
            # Sort alternatives
            cheaper_alternatives.sort(key=lambda x: x["effective_cost_usd"])
            more_accurate_alternatives.sort(key=lambda x: -x["humaneval"])
            
            # Limit to top 3
            cheaper_alternatives = cheaper_alternatives[:3]
            more_accurate_alternatives = more_accurate_alternatives[:3]
        
        # Check budget
        budget_remaining = None
        budget_usage_percent = None
        within_budget = True
        
        if user_id:
            self._maybe_reset_daily()
            budget = self.daily_budgets.get(user_id)
            if budget:
                current_usage = self.daily_usage.get(user_id, Decimal("0"))
                budget_remaining = budget - current_usage
                budget_usage_percent = float((current_usage + effective_cost) / budget * 100)
                within_budget = (current_usage + effective_cost) <= budget
        
        return CostEstimate(
            model_id=model_id,
            model_name=model.name,
            tier=model.tier.value,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            base_cost=base_cost,
            effective_cost=effective_cost,
            retry_multiplier=retry_multiplier,
            expected_attempts=expected_attempts,
            cheaper_alternatives=cheaper_alternatives,
            more_accurate_alternatives=more_accurate_alternatives,
            budget_remaining=budget_remaining,
            budget_usage_percent=budget_usage_percent,
            within_budget=within_budget
        )
    
    def record_usage(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        verification_passed: bool,
        attempts: int,
        user_id: Optional[str] = None
    ):
        """Record actual usage for tracking and learning."""
        model = get_model(model_id)
        if not model:
            return
        
        cost = model.estimate_cost(input_tokens, output_tokens) * attempts
        
        record = UsageRecord(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            verification_passed=verification_passed,
            attempts=attempts,
            timestamp=datetime.utcnow()
        )
        
        self.usage_history.append(record)
        
        # Update daily usage
        if user_id:
            self._maybe_reset_daily()
            current = self.daily_usage.get(user_id, Decimal("0"))
            self.daily_usage[user_id] = current + cost
    
    def set_daily_budget(self, user_id: str, budget: Decimal):
        """Set daily budget for a user."""
        self.daily_budgets[user_id] = budget
    
    def get_daily_usage(self, user_id: str) -> Dict:
        """Get daily usage summary for a user."""
        self._maybe_reset_daily()
        usage = self.daily_usage.get(user_id, Decimal("0"))
        budget = self.daily_budgets.get(user_id)
        
        return {
            "user_id": user_id,
            "daily_usage_usd": float(usage),
            "daily_budget_usd": float(budget) if budget else None,
            "budget_remaining_usd": float(budget - usage) if budget else None,
            "usage_percent": float(usage / budget * 100) if budget else None
        }
    
    def get_usage_stats(self, since: Optional[datetime] = None) -> Dict:
        """Get aggregate usage statistics."""
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        relevant = [r for r in self.usage_history if r.timestamp >= since]
        
        if not relevant:
            return {"total_cost": 0, "total_requests": 0}
        
        by_model: Dict[str, Dict] = {}
        for record in relevant:
            if record.model_id not in by_model:
                by_model[record.model_id] = {
                    "requests": 0,
                    "total_cost": Decimal("0"),
                    "total_attempts": 0,
                    "passed": 0
                }
            
            by_model[record.model_id]["requests"] += 1
            by_model[record.model_id]["total_cost"] += record.cost
            by_model[record.model_id]["total_attempts"] += record.attempts
            if record.verification_passed:
                by_model[record.model_id]["passed"] += 1
        
        return {
            "total_cost_usd": float(sum(r.cost for r in relevant)),
            "total_requests": len(relevant),
            "by_model": {
                model_id: {
                    "requests": stats["requests"],
                    "total_cost_usd": float(stats["total_cost"]),
                    "avg_attempts": stats["total_attempts"] / stats["requests"],
                    "success_rate": stats["passed"] / stats["requests"] * 100
                }
                for model_id, stats in by_model.items()
            }
        }
    
    def recommend_model(
        self,
        intent_text: str,
        complexity: str = "medium",
        max_cost: Optional[Decimal] = None,
        min_accuracy: Optional[float] = None
    ) -> Optional[str]:
        """
        Recommend the best model based on constraints.
        
        Returns model_id of recommended model.
        """
        input_tokens = int(len(intent_text) * self.TOKENS_PER_CHAR) + 500
        output_tokens = self.OUTPUT_TOKENS_BY_COMPLEXITY.get(complexity, 500)
        
        candidates = []
        
        for model_id, model in MODEL_CATALOG.items():
            if not model.available:
                continue
            
            effective_cost = model.estimate_effective_cost(input_tokens, output_tokens)
            
            # Apply constraints
            if max_cost and effective_cost > max_cost:
                continue
            
            if min_accuracy and model.humaneval_score < min_accuracy:
                continue
            
            # Score: prioritize accuracy, then cost efficiency
            score = model.humaneval_score - float(effective_cost) * 10
            candidates.append((model_id, score, effective_cost))
        
        if not candidates:
            return None
        
        # Return highest scoring model
        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0]
    
    def _maybe_reset_daily(self):
        """Reset daily counters if it's a new day."""
        now = datetime.utcnow().replace(hour=0, minute=0, second=0)
        if now > self._last_reset:
            self.daily_usage.clear()
            self._last_reset = now


# Singleton instance
_cost_oracle: Optional[CostOracle] = None


def get_cost_oracle() -> CostOracle:
    """Get the global cost oracle instance."""
    global _cost_oracle
    if _cost_oracle is None:
        _cost_oracle = CostOracle()
    return _cost_oracle
