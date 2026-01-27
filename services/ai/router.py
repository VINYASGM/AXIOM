"""
LLM Router

Multi-provider routing with fallback, metrics, and cost-based selection.
Ported from UACP's gateway/internal/llm/router.go

Routes requests to optimal models based on intent complexity and cost constraints.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from threading import Lock


class ProviderStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"


@dataclass
class ChatMessage:
    """A chat message."""
    role: str  # system, user, assistant
    content: str


@dataclass
class ChatRequest:
    """Request to an LLM provider."""
    messages: List[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)  # input_tokens, output_tokens
    latency_ms: float = 0.0
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @property
    @abstractmethod
    def models(self) -> List[str]:
        """Available models."""
        pass
    
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat request."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available."""
        pass


class MockProvider(LLMProvider):
    """Mock provider for testing without API keys."""
    
    def __init__(self, name: str = "mock", latency_ms: float = 100):
        self._name = name
        self._latency = latency_ms
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def models(self) -> List[str]:
        return ["mock-fast", "mock-quality"]
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        await asyncio.sleep(self._latency / 1000)
        
        # Generate mock response based on last message
        last_msg = request.messages[-1].content if request.messages else ""
        
        mock_code = f'''def generated_function():
    """Generated for: {last_msg[:50]}..."""
    # Mock implementation
    pass
'''
        
        return ChatResponse(
            content=mock_code,
            model=request.model,
            provider=self.name,
            usage={"input_tokens": len(last_msg) // 4, "output_tokens": 50},
            latency_ms=self._latency
        )
    
    async def health_check(self) -> bool:
        return True


class OpenAIProvider(LLMProvider):
    """OpenAI provider (wrapper for existing LLMService)."""
    
    def __init__(self, llm_service):
        self._llm = llm_service
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def models(self) -> List[str]:
        return ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.time()
        
        # Use existing LLM service
        response = await self._llm.chat_completion(
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        latency = (time.time() - start) * 1000
        
        return ChatResponse(
            content=response.get("content", ""),
            model=request.model,
            provider=self.name,
            usage=response.get("usage", {}),
            latency_ms=latency
        )
    
    async def health_check(self) -> bool:
        return self._llm.openai_key is not None


@dataclass
class RoutingRule:
    """Rule for selecting a provider."""
    condition: Dict[str, Any]
    provider: str
    priority: int = 0
    
    def matches(self, request: ChatRequest) -> bool:
        """Check if this rule matches the request."""
        # Model prefix match
        if "model_prefix" in self.condition:
            if not request.model.startswith(self.condition["model_prefix"]):
                return False
        
        # Max cost (complexity) match
        if "max_complexity" in self.condition:
            complexity = request.metadata.get("complexity", 0)
            if complexity > self.condition["max_complexity"]:
                return False
        
        # Intent type match
        if "intent_type" in self.condition:
            intent = request.metadata.get("intent_type", "unknown")
            if intent != self.condition["intent_type"]:
                return False
        
        return True


@dataclass
class RouterMetrics:
    """Routing statistics."""
    request_count: Dict[str, int] = field(default_factory=dict)
    error_count: Dict[str, int] = field(default_factory=dict)
    total_latency_ms: Dict[str, float] = field(default_factory=dict)
    
    def record_request(self, provider: str, latency_ms: float):
        self.request_count[provider] = self.request_count.get(provider, 0) + 1
        self.total_latency_ms[provider] = self.total_latency_ms.get(provider, 0) + latency_ms
    
    def record_error(self, provider: str):
        self.error_count[provider] = self.error_count.get(provider, 0) + 1
    
    def get_avg_latency(self, provider: str) -> float:
        count = self.request_count.get(provider, 0)
        if count == 0:
            return 0.0
        return self.total_latency_ms.get(provider, 0) / count
    
    def to_dict(self) -> dict:
        return {
            "requests": dict(self.request_count),
            "errors": dict(self.error_count),
            "avg_latency_ms": {
                p: round(self.get_avg_latency(p), 2)
                for p in self.request_count.keys()
            }
        }


@dataclass
class ModelRoutingPolicy:
    """Policy governing model selection and cost."""
    org_id: str
    allowed_models: List[str]
    denied_models: List[str]
    cost_preference: str = "balanced"  # cheapest, balanced, quality
    default_model: Optional[str] = None

class LLMRouter:
    # ... existing docstring ...
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.rules: List[RoutingRule] = []
        self.policies: Dict[str, ModelRoutingPolicy] = {}  # Key: org_id
        self.fallback: Optional[str] = None
        self.metrics = RouterMetrics()
        self._lock = Lock()
    
    def set_policy(self, policy: ModelRoutingPolicy):
        """Set a routing policy for an organization."""
        with self._lock:
            self.policies[policy.org_id] = policy

    # ... existing methods (register_provider, unregister_provider, set_fallback, add_rule) ...
    def register_provider(self, name: str, provider: LLMProvider):
        """Register an LLM provider."""
        with self._lock:
            self.providers[name] = provider
    
    def unregister_provider(self, name: str):
        """Remove a provider."""
        with self._lock:
            if name in self.providers:
                del self.providers[name]
    
    def set_fallback(self, provider_name: str):
        """Set the fallback provider."""
        self.fallback = provider_name
    
    def add_rule(self, rule: RoutingRule):
        """Add a routing rule."""
        with self._lock:
            self.rules.append(rule)
            self.rules.sort(key=lambda r: r.priority, reverse=True)

    def _apply_policy(self, request: ChatRequest, provider: LLMProvider) -> bool:
        """Check if provider/model complies with policy."""
        org_id = request.metadata.get("org_id")
        if not org_id or org_id not in self.policies:
            return True
        
        policy = self.policies[org_id]
        
        # Check specific model constraints
        if request.model in policy.denied_models:
            return False
            
        if policy.allowed_models and request.model not in policy.allowed_models:
            # If allow list is strict
            return False
            
        return True
    
    def route(self, request: ChatRequest) -> Optional[LLMProvider]:
        """
        Select the best provider for a request.
        
        Returns:
            Selected provider, or None if no provider available
        """
        with self._lock:
            # Check rules in priority order
            # Check rules in priority order
            for rule in self.rules:
                if rule.matches(request):
                    if rule.provider in self.providers:
                        provider = self.providers[rule.provider]
                        if self._apply_policy(request, provider):
                            return provider
            
            # Model-based routing (direct match)
            for name, provider in self.providers.items():
                if request.model in provider.models:
                    if self._apply_policy(request, provider):
                        return provider
            
            # Fallback
            if self.fallback and self.fallback in self.providers:
                return self.providers[self.fallback]
            
            # Any available provider
            if self.providers:
                return next(iter(self.providers.values()))
            
            return None
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Route and execute a chat request.
        
        Includes fallback on failure.
        """
        provider = self.route(request)
        
        if provider is None:
            raise ValueError("No LLM provider available")
        
        start = time.time()
        
        try:
            response = await provider.chat(request)
            latency = (time.time() - start) * 1000
            self.metrics.record_request(provider.name, latency)
            return response
        except Exception as e:
            self.metrics.record_error(provider.name)
            
            # Try fallback
            if self.fallback and self.fallback != provider.name:
                fallback_provider = self.providers.get(self.fallback)
                if fallback_provider:
                    try:
                        response = await fallback_provider.chat(request)
                        self.metrics.record_request(fallback_provider.name, 
                                                     (time.time() - start) * 1000)
                        return response
                    except Exception:
                        self.metrics.record_error(fallback_provider.name)
            
            raise
    
    def list_providers(self) -> List[str]:
        """List registered providers."""
        with self._lock:
            return list(self.providers.keys())
    
    def get_metrics(self) -> dict:
        """Get routing metrics."""
        return self.metrics.to_dict()
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for name, provider in self.providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results


# Global router instance
_global_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Get the global router instance."""
    global _global_router
    if _global_router is None:
        _global_router = LLMRouter()
        # Register mock provider by default
        _global_router.register_provider("mock", MockProvider())
        _global_router.set_fallback("mock")
    return _global_router


def init_router(llm_service=None) -> LLMRouter:
    """Initialize router with all available providers."""
    global _global_router
    _global_router = LLMRouter()
    
    # Always register mock as fallback
    _global_router.register_provider("mock", MockProvider())
    
    # Import real providers
    try:
        from models.providers import (
            create_provider,
            get_available_providers,
            DeepSeekProvider,
            OpenAIEnhancedProvider,
            AnthropicProvider,
            GoogleProvider
        )
        import os
        
        # Register DeepSeek (recommended default - cheap + accurate)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key and deepseek_key != "your-deepseek-api-key":
            provider = DeepSeekProvider(deepseek_key)
            _global_router.register_provider("deepseek", provider)
            _global_router.set_fallback("deepseek")  # Best fallback due to cost
        
        # Register OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your-openai-api-key":
            provider = OpenAIEnhancedProvider(openai_key)
            _global_router.register_provider("openai", provider)
            if not _global_router.fallback or _global_router.fallback == "mock":
                _global_router.set_fallback("openai")
        
        # Register Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key and anthropic_key != "your-anthropic-api-key":
            provider = AnthropicProvider(anthropic_key)
            _global_router.register_provider("anthropic", provider)
        
        # Register Google
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key and google_key != "your-google-api-key":
            provider = GoogleProvider(google_key)
            _global_router.register_provider("google", provider)
        
    except ImportError as e:
        print(f"Warning: Could not import providers: {e}")
    
    # Legacy: Register OpenAI wrapper if llm_service provided
    if llm_service and llm_service.openai_key:
        _global_router.register_provider("openai_legacy", OpenAIProvider(llm_service))
    
    # Set mock as fallback if nothing else available
    if not _global_router.fallback:
        _global_router.set_fallback("mock")
    
    return _global_router

