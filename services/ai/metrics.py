"""
Prometheus Metrics for AXIOM AI Service

Provides metrics for monitoring generation, verification, and cost tracking.
"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
from fastapi import Response
from functools import wraps
import time

# Create a custom registry to avoid conflicts
REGISTRY = CollectorRegistry(auto_describe=True)

# =============================================================================
# COUNTERS
# =============================================================================

generation_requests_total = Counter(
    'axiom_generation_requests_total',
    'Total code generation requests',
    ['provider', 'model', 'language', 'status'],
    registry=REGISTRY
)

verification_requests_total = Counter(
    'axiom_verification_requests_total',
    'Total verification requests',
    ['tier', 'language', 'passed'],
    registry=REGISTRY
)

intent_parse_total = Counter(
    'axiom_intent_parse_total',
    'Total intent parsing requests',
    ['status'],
    registry=REGISTRY
)

llm_api_calls_total = Counter(
    'axiom_llm_api_calls_total',
    'Total LLM API calls by provider',
    ['provider', 'model', 'status'],
    registry=REGISTRY
)

# =============================================================================
# HISTOGRAMS
# =============================================================================

generation_duration_seconds = Histogram(
    'axiom_generation_duration_seconds',
    'Time spent generating code',
    ['provider', 'model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY
)

verification_duration_seconds = Histogram(
    'axiom_verification_duration_seconds',
    'Time spent in verification',
    ['tier'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
    registry=REGISTRY
)

llm_latency_seconds = Histogram(
    'axiom_llm_latency_seconds',
    'LLM API call latency',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY
)

# =============================================================================
# GAUGES
# =============================================================================

active_sdos = Gauge(
    'axiom_active_sdos',
    'Number of SDOs currently in processing',
    registry=REGISTRY
)

memory_entries = Gauge(
    'axiom_memory_entries',
    'Number of entries in vector memory',
    ['collection'],
    registry=REGISTRY
)

session_cost_usd = Gauge(
    'axiom_session_cost_usd',
    'Cumulative cost per session',
    ['session_id'],
    registry=REGISTRY
)

provider_health = Gauge(
    'axiom_provider_health',
    'LLM provider health status (1=healthy, 0=unhealthy)',
    ['provider'],
    registry=REGISTRY
)

# =============================================================================
# INFO
# =============================================================================

service_info = Info(
    'axiom_service',
    'AXIOM AI Service information',
    registry=REGISTRY
)

# Initialize service info
service_info.info({
    'version': '0.5.0',
    'component': 'ai-service',
    'framework': 'fastapi'
})

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def track_generation(provider: str, model: str, language: str, status: str, duration: float):
    """Track a generation request."""
    generation_requests_total.labels(
        provider=provider,
        model=model,
        language=language,
        status=status
    ).inc()
    
    generation_duration_seconds.labels(
        provider=provider,
        model=model
    ).observe(duration)

def track_verification(tier: str, language: str, passed: bool, duration: float):
    """Track a verification request."""
    verification_requests_total.labels(
        tier=tier,
        language=language,
        passed=str(passed).lower()
    ).inc()
    
    verification_duration_seconds.labels(tier=tier).observe(duration)

def track_llm_call(provider: str, model: str, status: str, latency: float):
    """Track an LLM API call."""
    llm_api_calls_total.labels(
        provider=provider,
        model=model,
        status=status
    ).inc()
    
    llm_latency_seconds.labels(
        provider=provider,
        model=model
    ).observe(latency)

def update_provider_health(provider: str, healthy: bool):
    """Update provider health status."""
    provider_health.labels(provider=provider).set(1.0 if healthy else 0.0)

def update_session_cost(session_id: str, cost: float):
    """Update session cost gauge."""
    session_cost_usd.labels(session_id=session_id).set(cost)

# =============================================================================
# DECORATORS
# =============================================================================

def timed_generation(provider: str, model: str, language: str):
    """Decorator to time and track generation."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                track_generation(provider, model, language, 'success', duration)
                return result
            except Exception as e:
                duration = time.time() - start
                track_generation(provider, model, language, 'error', duration)
                raise
        return wrapper
    return decorator

# =============================================================================
# METRICS ENDPOINT
# =============================================================================

def get_metrics():
    """Generate Prometheus metrics response."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )
