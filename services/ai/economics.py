"""
Economic Control Plane
Cost estimation, tracking, and budget management for AI operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
import tiktoken


class ModelPricing(BaseModel):
    """Pricing per 1M tokens for a model"""
    model_id: str
    input_price_per_m: float  # USD per 1M input tokens
    output_price_per_m: float  # USD per 1M output tokens
    

# OpenAI pricing (as of early 2024)
MODEL_PRICING: Dict[str, ModelPricing] = {
    "gpt-4-turbo": ModelPricing(
        model_id="gpt-4-turbo",
        input_price_per_m=10.0,
        output_price_per_m=30.0
    ),
    "gpt-4-turbo-preview": ModelPricing(
        model_id="gpt-4-turbo-preview",
        input_price_per_m=10.0,
        output_price_per_m=30.0
    ),
    "gpt-4o": ModelPricing(
        model_id="gpt-4o",
        input_price_per_m=5.0,
        output_price_per_m=15.0
    ),
    "gpt-4o-mini": ModelPricing(
        model_id="gpt-4o-mini",
        input_price_per_m=0.15,
        output_price_per_m=0.60
    ),
    "gpt-3.5-turbo": ModelPricing(
        model_id="gpt-3.5-turbo",
        input_price_per_m=0.50,
        output_price_per_m=1.50
    ),
    "text-embedding-3-small": ModelPricing(
        model_id="text-embedding-3-small",
        input_price_per_m=0.02,
        output_price_per_m=0.0
    ),
}


class CostEstimate(BaseModel):
    """Estimated cost for an operation"""
    input_tokens: int = 0
    output_tokens: int = 0
    embedding_tokens: int = 0
    model: str = "gpt-4-turbo"
    estimated_cost_usd: float = 0.0
    confidence: float = 0.8  # How confident we are in this estimate
    
    def calculate(self) -> float:
        """Calculate the estimated cost"""
        pricing = MODEL_PRICING.get(self.model, MODEL_PRICING["gpt-4-turbo"])
        
        input_cost = (self.input_tokens / 1_000_000) * pricing.input_price_per_m
        output_cost = (self.output_tokens / 1_000_000) * pricing.output_price_per_m
        
        # Add embedding cost if applicable
        embed_pricing = MODEL_PRICING.get("text-embedding-3-small")
        embed_cost = (self.embedding_tokens / 1_000_000) * embed_pricing.input_price_per_m
        
        self.estimated_cost_usd = input_cost + output_cost + embed_cost
        return self.estimated_cost_usd


class CostRecord(BaseModel):
    """Record of actual cost incurred"""
    id: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    sdo_id: Optional[str] = None
    operation: str  # parse, generate, verify, embed
    model: str
    input_tokens: int
    output_tokens: int
    actual_cost_usd: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Budget(BaseModel):
    """Budget configuration for a session/user"""
    max_usd_per_session: float = 1.0
    max_usd_per_request: float = 0.10
    warn_threshold: float = 0.8  # Warn at 80% of limit
    current_spent: float = 0.0
    records: List[CostRecord] = []
    
    def can_proceed(self, estimated_cost: float) -> tuple[bool, str]:
        """Check if operation can proceed within budget"""
        if estimated_cost > self.max_usd_per_request:
            return False, f"Request cost ${estimated_cost:.4f} exceeds limit ${self.max_usd_per_request:.4f}"
        
        if self.current_spent + estimated_cost > self.max_usd_per_session:
            return False, f"Would exceed session budget (${self.current_spent + estimated_cost:.4f} > ${self.max_usd_per_session:.4f})"
        
        return True, "OK"
    
    def get_warning(self) -> Optional[str]:
        """Check if we should warn about budget usage"""
        usage_ratio = self.current_spent / self.max_usd_per_session if self.max_usd_per_session > 0 else 0
        
        if usage_ratio >= self.warn_threshold:
            remaining = self.max_usd_per_session - self.current_spent
            return f"Budget warning: ${remaining:.4f} remaining ({(1-usage_ratio)*100:.1f}%)"
        
        return None
    
    def record_cost(self, record: CostRecord):
        """Record a cost and update spent"""
        self.records.append(record)
        self.current_spent += record.actual_cost_usd


class EconomicsService:
    """
    Manages cost estimation, tracking, and budget enforcement.
    """
    
    def __init__(self):
        self.encoder = None
        self._init_encoder()
        self.budgets: Dict[str, Budget] = {}  # session_id -> Budget
        self.default_budget = Budget()
    
    def _init_encoder(self):
        """Initialize tokenizer"""
        try:
            self.encoder = tiktoken.encoding_for_model("gpt-4")
        except Exception:
            try:
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self.encoder = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not self.encoder:
            # Rough estimate: 4 chars per token
            return len(text) // 4
        return len(self.encoder.encode(text))
    
    def estimate_generation_cost(
        self,
        intent: str,
        language: str = "python",
        candidate_count: int = 3,
        include_verification: bool = True,
        model: str = "gpt-4-turbo"
    ) -> CostEstimate:
        """
        Estimate cost for a full generation operation.
        
        Args:
            intent: The user's intent
            language: Target language
            candidate_count: Number of candidates to generate
            include_verification: Whether to include verification costs
            model: Model to use
        
        Returns:
            CostEstimate with projected costs
        """
        # Estimate input tokens (system prompt + intent + context)
        base_system_prompt = 200  # ~200 tokens for system prompt
        intent_tokens = self.count_tokens(intent)
        context_estimate = 500  # Average context from memory
        
        input_per_candidate = base_system_prompt + intent_tokens + context_estimate
        
        # Estimate output tokens (generated code)
        avg_code_length = 50 if language in ["python", "javascript"] else 80
        output_per_candidate = self.count_tokens(" " * avg_code_length * 4)  # Rough estimate
        
        # Total for all candidates
        total_input = input_per_candidate * candidate_count
        total_output = output_per_candidate * candidate_count
        
        # Add embedding costs for RAG
        embedding_tokens = intent_tokens + (context_estimate * 2)  # Query + retrieval
        
        estimate = CostEstimate(
            input_tokens=total_input,
            output_tokens=total_output,
            embedding_tokens=embedding_tokens,
            model=model
        )
        estimate.calculate()
        
        return estimate
    
    def estimate_parse_cost(self, intent: str, model: str = "gpt-4-turbo") -> CostEstimate:
        """Estimate cost for parsing an intent"""
        input_tokens = self.count_tokens(intent) + 100  # +100 for system prompt
        output_tokens = 200  # Estimated parsed output
        
        estimate = CostEstimate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model
        )
        estimate.calculate()
        return estimate
    
    def get_budget(self, session_id: str) -> Budget:
        """Get or create budget for session"""
        if session_id not in self.budgets:
            self.budgets[session_id] = Budget()
        return self.budgets[session_id]
    
    def check_budget(
        self,
        session_id: str,
        estimated_cost: float
    ) -> tuple[bool, str, Optional[str]]:
        """
        Check if operation can proceed within budget.
        
        Returns:
            (can_proceed, message, warning)
        """
        budget = self.get_budget(session_id)
        can_proceed, message = budget.can_proceed(estimated_cost)
        warning = budget.get_warning()
        
        return can_proceed, message, warning
    
    def record_usage(
        self,
        session_id: str,
        sdo_id: str,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> CostRecord:
        """Record actual token usage"""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4-turbo"])
        
        cost = (
            (input_tokens / 1_000_000) * pricing.input_price_per_m +
            (output_tokens / 1_000_000) * pricing.output_price_per_m
        )
        
        record = CostRecord(
            sdo_id=sdo_id,
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            actual_cost_usd=cost
        )
        
        budget = self.get_budget(session_id)
        budget.record_cost(record)
        
        return record
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Get cost summary for a session"""
        budget = self.get_budget(session_id)
        
        return {
            "session_id": session_id,
            "total_spent_usd": budget.current_spent,
            "budget_limit_usd": budget.max_usd_per_session,
            "remaining_usd": budget.max_usd_per_session - budget.current_spent,
            "operations_count": len(budget.records),
            "warning": budget.get_warning()
        }
