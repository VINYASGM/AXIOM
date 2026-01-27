"""
Performance Benchmarks for AXIOM AI Services

Focused on validating performance targets:
- Tier 0: <10ms
- State projection: <50ms for 100 events
- Model routing: <1ms
"""
import pytest
import asyncio
import time
import statistics
from typing import List


# ============================================================================
# TIER 0 BENCHMARKS
# ============================================================================

class TestTier0Benchmarks:
    """Benchmark Tier 0 (Tree-sitter) performance."""
    
    ITERATIONS = 10  # Run each test multiple times for accuracy
    TARGET_MS = 10.0  # Target performance
    
    @pytest.fixture
    def code_samples(self):
        """Generate code samples of varying sizes."""
        return {
            "tiny": "x = 1",
            "small": """
def hello(name: str) -> str:
    return f"Hello, {name}!"
""",
            "medium": """
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, value: float) -> float:
        self.result += value
        return self.result
    
    def subtract(self, value: float) -> float:
        self.result -= value
        return self.result
    
    def multiply(self, value: float) -> float:
        self.result *= value
        return self.result
    
    def divide(self, value: float) -> float:
        if value == 0:
            raise ValueError("Cannot divide by zero")
        self.result /= value
        return self.result
    
    def reset(self):
        self.result = 0
""",
            "large": "\n".join([
                f"""
def function_{i}(x: int, y: int) -> int:
    '''Docstring for function {i}'''
    result = x + y + {i}
    if result > 100:
        return result * 2
    else:
        return result
""" for i in range(50)
            ]),
        }
    
    @pytest.mark.asyncio
    async def test_tier0_tiny_code(self, code_samples):
        """Benchmark Tier 0 with tiny code."""
        times = await self._benchmark_tier0(code_samples["tiny"])
        self._report("tiny", times)
        assert statistics.mean(times) < self.TARGET_MS * 2
    
    @pytest.mark.asyncio
    async def test_tier0_small_code(self, code_samples):
        """Benchmark Tier 0 with small code."""
        times = await self._benchmark_tier0(code_samples["small"])
        self._report("small", times)
        assert statistics.mean(times) < self.TARGET_MS * 2
    
    @pytest.mark.asyncio
    async def test_tier0_medium_code(self, code_samples):
        """Benchmark Tier 0 with medium code."""
        times = await self._benchmark_tier0(code_samples["medium"])
        self._report("medium", times)
        assert statistics.mean(times) < self.TARGET_MS * 3
    
    @pytest.mark.asyncio
    async def test_tier0_large_code(self, code_samples):
        """Benchmark Tier 0 with large code (50 functions)."""
        times = await self._benchmark_tier0(code_samples["large"])
        self._report("large", times)
        assert statistics.mean(times) < self.TARGET_MS * 5  # Allow more slack for large files
    
    async def _benchmark_tier0(self, code: str) -> List[float]:
        """Run Tier 0 verification multiple times and collect timings."""
        from grpc_server.verification_service import VerificationServicer
        from unittest.mock import MagicMock
        
        servicer = VerificationServicer()
        times = []
        
        # Warm up
        await servicer.QuickVerify({"code": code, "language": "python"}, MagicMock())
        
        for _ in range(self.ITERATIONS):
            start = time.perf_counter()
            await servicer.QuickVerify({"code": code, "language": "python"}, MagicMock())
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return times
    
    def _report(self, name: str, times: List[float]):
        """Print benchmark report."""
        print(f"\n[Tier 0 Benchmark: {name}]")
        print(f"  Min:    {min(times):.3f}ms")
        print(f"  Max:    {max(times):.3f}ms")
        print(f"  Mean:   {statistics.mean(times):.3f}ms")
        print(f"  Median: {statistics.median(times):.3f}ms")
        if len(times) > 1:
            print(f"  StdDev: {statistics.stdev(times):.3f}ms")


# ============================================================================
# STATE PROJECTION BENCHMARKS
# ============================================================================

class TestProjectionBenchmarks:
    """Benchmark event sourcing state projection."""
    
    def test_projection_10_events(self):
        """Benchmark projection with 10 events."""
        times = self._benchmark_projection(10)
        self._report(10, times)
        assert statistics.mean(times) < 5.0  # <5ms for 10 events
    
    def test_projection_50_events(self):
        """Benchmark projection with 50 events."""
        times = self._benchmark_projection(50)
        self._report(50, times)
        assert statistics.mean(times) < 25.0  # <25ms for 50 events
    
    def test_projection_100_events(self):
        """Benchmark projection with 100 events."""
        times = self._benchmark_projection(100)
        self._report(100, times)
        assert statistics.mean(times) < 50.0  # <50ms for 100 events
    
    def test_projection_500_events(self):
        """Benchmark projection with 500 events (stress test)."""
        times = self._benchmark_projection(500)
        self._report(500, times)
        assert statistics.mean(times) < 250.0  # <250ms for 500 events
    
    def _benchmark_projection(self, event_count: int, iterations: int = 5) -> List[float]:
        """Run projection benchmark."""
        from ivcu_events import IVCUEventType, IVCUStateProjector, create_event
        
        projector = IVCUStateProjector()
        ivcu_id = f"bench-{event_count}"
        
        # Create events
        events = [
            create_event(ivcu_id, IVCUEventType.INTENT_CREATED, {
                "raw_intent": "Initial intent"
            })
        ]
        
        for i in range(event_count - 1):
            if i % 5 == 0:
                events.append(create_event(ivcu_id, IVCUEventType.INTENT_REFINED, {
                    "refined_intent": f"Refinement {i}"
                }))
            elif i % 5 == 1:
                events.append(create_event(ivcu_id, IVCUEventType.CONTRACT_ADDED, {
                    "contract_type": "precondition",
                    "expression": f"x > {i}"
                }))
            elif i % 5 == 2:
                events.append(create_event(ivcu_id, IVCUEventType.CANDIDATE_GENERATED, {
                    "candidate_id": f"cand-{i}",
                    "code": f"def func_{i}(): pass",
                    "tokens_used": 50,
                    "cost": 0.001
                }))
            elif i % 5 == 3:
                events.append(create_event(ivcu_id, IVCUEventType.VERIFICATION_COMPLETED, {
                    "candidate_id": f"cand-{i-1}",
                    "tier": "tier_1",
                    "passed": True,
                    "confidence": 0.9
                }))
            else:
                events.append(create_event(ivcu_id, IVCUEventType.MODEL_UPGRADED, {
                    "from_model_id": "model-a",
                    "to_model_id": "model-b",
                    "reason": "retry"
                }))
        
        times = []
        
        # Warm up
        projector.project(events)
        
        for _ in range(iterations):
            start = time.perf_counter()
            state = projector.project(events)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        return times
    
    def _report(self, event_count: int, times: List[float]):
        """Print benchmark report."""
        print(f"\n[Projection Benchmark: {event_count} events]")
        print(f"  Min:    {min(times):.3f}ms")
        print(f"  Mean:   {statistics.mean(times):.3f}ms")
        print(f"  Max:    {max(times):.3f}ms")


# ============================================================================
# MODEL ROUTING BENCHMARKS
# ============================================================================

class TestModelRoutingBenchmarks:
    """Benchmark model catalog lookups and routing."""
    
    def test_model_lookup_performance(self):
        """Benchmark model lookup by ID."""
        from models.catalog import get_model
        
        iterations = 1000
        start = time.perf_counter()
        
        for _ in range(iterations):
            get_model("deepseek-v3")
            get_model("claude-sonnet-4")
            get_model("gpt-4o-mini")
        
        elapsed = (time.perf_counter() - start) * 1000
        per_lookup = elapsed / (iterations * 3)
        
        print(f"\n[Model Lookup Benchmark]")
        print(f"  Total:      {elapsed:.3f}ms for {iterations * 3} lookups")
        print(f"  Per lookup: {per_lookup:.4f}ms")
        
        assert per_lookup < 0.1  # <0.1ms per lookup
    
    def test_tier_filtering_performance(self):
        """Benchmark tier filtering."""
        from models.catalog import get_models_by_tier, ModelTier
        
        iterations = 1000
        start = time.perf_counter()
        
        for _ in range(iterations):
            get_models_by_tier(ModelTier.BALANCED)
            get_models_by_tier(ModelTier.HIGH_ACCURACY)
        
        elapsed = (time.perf_counter() - start) * 1000
        per_filter = elapsed / (iterations * 2)
        
        print(f"\n[Tier Filtering Benchmark]")
        print(f"  Total:      {elapsed:.3f}ms for {iterations * 2} filters")
        print(f"  Per filter: {per_filter:.4f}ms")
        
        assert per_filter < 0.1  # <0.1ms per filter
    
    def test_cost_estimation_performance(self):
        """Benchmark cost estimation."""
        from models.cost_oracle import CostOracle
        
        oracle = CostOracle()
        iterations = 100
        
        start = time.perf_counter()
        
        for _ in range(iterations):
            oracle.estimate_cost(
                model_id="deepseek-v3",
                intent_text="Create a function",
                complexity="medium"
            )
        
        elapsed = (time.perf_counter() - start) * 1000
        per_estimate = elapsed / iterations
        
        print(f"\n[Cost Estimation Benchmark]")
        print(f"  Total:       {elapsed:.3f}ms for {iterations} estimates")
        print(f"  Per estimate: {per_estimate:.4f}ms")
        
        assert per_estimate < 1.0  # <1ms per estimate


# ============================================================================
# SUMMARY REPORT
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def benchmark_summary(request):
    """Print summary after all benchmarks."""
    yield
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print("Targets:")
    print("  - Tier 0 verification: <10ms")
    print("  - State projection (100 events): <50ms")
    print("  - Model lookup: <0.1ms")
    print("  - Cost estimation: <1ms")
    print("=" * 60)


# Run with: pytest tests/test_benchmarks.py -v -s
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
