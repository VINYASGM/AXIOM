"""
AXIOM End-to-End Simulation Test

Comprehensive test covering all phases:
- Phase 1: SDO creation, generation, verification
- Phase 2: Thompson Sampling, undo/redo, adaptive generation
- Phase 3: Semantic cache, LLM router, policy engine

Run: py -3 test_e2e_simulation.py
"""
import asyncio
import sys
import os
import time
import traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all modules
from sdo import SDO, SDOStatus, Candidate
from llm import LLMService
from memory import MemoryService
from sdo_engine import SDOEngine
from verification import VerificationOrchestra
from bandit import ThompsonBandit
from history import SDOHistory
from cache import SemanticCache, get_cache
from router import LLMRouter, MockProvider, ChatRequest, ChatMessage
from policy import PolicyEngine, check_code, check_intent
from knowledge import KnowledgeService


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step: str, status: str = "..."):
    print(f"  → {step}: {status}")


async def test_phase1_foundation():
    """Test Phase 1: Foundation components."""
    print_header("PHASE 1: Foundation")
    results = {"passed": 0, "failed": 0}
    
    # 1. LLM Service initialization
    try:
        llm = LLMService()
        print_step("LLM Service init", "✓")
        results["passed"] += 1
    except Exception as e:
        print_step("LLM Service init", f"✗ {e}")
        traceback.print_exc()
        results["failed"] += 1
        return results
    
    # 2. Memory Service initialization
    try:
        memory = MemoryService(embed_fn=llm.embed_text)
        print_step("Memory Service init", "✓")
        results["passed"] += 1
    except Exception as e:
        print_step("Memory Service init", f"✗ {e}")
        results["failed"] += 1
    
    # 3. SDO Creation
    try:
        sdo = SDO(
            id="test-sdo-001",
            raw_intent="Create a function to calculate factorial",
            language="python",
            status=SDOStatus.DRAFT
        )
        assert sdo.id == "test-sdo-001"
        assert sdo.language == "python"
        print_step("SDO creation", "✓")
        results["passed"] += 1
    except Exception as e:
        print_step("SDO creation", f"✗ {e}")
        traceback.print_exc()
        results["failed"] += 1
    
    # 4. Verification Orchestra
    try:
        orchestra = VerificationOrchestra()
        code = "def factorial(n: int) -> int:\n    return 1 if n <= 1 else n * factorial(n-1)"
        result = await orchestra.verify(code, "test", "python", run_tier2=False)
        assert result.tier_1_passed is not None
        print_step("Verification Orchestra", f"✓ (tier1={result.tier_1_passed})")
        results["passed"] += 1
    except Exception as e:
        print_step("Verification Orchestra", f"✗ {e}")
        results["failed"] += 1
    
    # 5. Knowledge Service
    try:
        knowledge = KnowledgeService(memory)
        print_step("Knowledge Service init", "✓")
        results["passed"] += 1
    except Exception as e:
        print_step("Knowledge Service init", f"✗ {e}")
        results["failed"] += 1
    
    return results


async def test_phase2_adaptive():
    """Test Phase 2: Adaptive generation components."""
    print_header("PHASE 2: Adaptive Generation")
    results = {"passed": 0, "failed": 0}
    
    # 1. Thompson Sampling Bandit
    try:
        bandit = ThompsonBandit()
        arm = bandit.select_arm()
        assert arm is not None
        bandit.update(arm.id, reward=0.8, intent_type="create")
        stats = bandit.get_arm_stats()
        assert len(stats) > 0
        print_step("Thompson Sampling", f"✓ (selected: {arm.id})")
        results["passed"] += 1
    except Exception as e:
        print_step("Thompson Sampling", f"✗ {e}")
        results["failed"] += 1
    
    # 2. SDO History
    try:
        history = SDOHistory()
        sdo = SDO(id="test", raw_intent="test", language="python", status=SDOStatus.DRAFT)
        snap_id = history.snapshot(sdo, "initial")
        assert snap_id is not None
        
        # Update and snapshot again
        sdo.code = "def test(): pass"
        sdo.status = SDOStatus.VERIFIED
        history.snapshot(sdo, "after_generation")
        
        # Undo
        prev = history.undo("test")
        assert prev is not None
        assert prev["code"] is None
        
        # Redo
        next_state = history.redo("test")
        assert next_state is not None
        assert next_state["code"] == "def test(): pass"
        
        print_step("SDO History (undo/redo)", "✓")
        results["passed"] += 1
    except Exception as e:
        print_step("SDO History", f"✗ {e}")
        traceback.print_exc()
        results["failed"] += 1
    
    # 3. SDO Engine with bandit
    try:
        llm = LLMService()
        engine = SDOEngine(llm, enable_cache=False, enable_policy=False)
        assert engine.bandit is not None
        assert engine.history is not None
        print_step("SDO Engine (Phase 2)", "✓")
        results["passed"] += 1
    except Exception as e:
        print_step("SDO Engine (Phase 2)", f"✗ {e}")
        results["failed"] += 1
    
    return results


async def test_phase3_intelligence():
    """Test Phase 3: Intelligence layer components."""
    print_header("PHASE 3: Intelligence Layer")
    results = {"passed": 0, "failed": 0}
    
    # 1. Semantic Cache
    try:
        cache = SemanticCache(max_size=100, enable_cleanup=False)
        
        # Set entry
        key = await cache.set(
            query="Create fibonacci",
            response="def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)",
            model="gpt-4"
        )
        
        # Get entry (exact match)
        entry = await cache.get("Create fibonacci", "gpt-4")
        assert entry is not None
        assert "fib" in entry.response
        
        # Check stats
        stats = cache.stats()
        assert stats["hits"] == 1
        
        print_step("Semantic Cache", f"✓ (hit_rate={stats['hit_rate']})")
        results["passed"] += 1
    except Exception as e:
        print_step("Semantic Cache", f"✗ {e}")
        results["failed"] += 1
    
    # 2. LLM Router
    try:
        router = LLMRouter()
        mock = MockProvider()
        router.register_provider("mock", mock)
        router.set_fallback("mock")
        
        # Route request
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Create a sorting function")],
            model="mock"
        )
        response = await router.chat(request)
        assert response.provider == "mock"
        assert "generated_function" in response.content.lower()
        
        # Check metrics
        metrics = router.get_metrics()
        assert metrics["requests"]["mock"] == 1
        
        print_step("LLM Router", f"✓ ({len(router.list_providers())} providers)")
        results["passed"] += 1
    except Exception as e:
        print_step("LLM Router", f"✗ {e}")
        results["failed"] += 1
    
    # 3. Policy Engine - Safe Code
    try:
        policy = PolicyEngine()
        
        safe_code = '''
def factorial(n: int) -> int:
    """Calculate factorial."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)
'''
        result = policy.check_post_generation(safe_code)
        assert result.passed
        
        print_step("Policy (safe code)", "✓ passed")
        results["passed"] += 1
    except Exception as e:
        print_step("Policy (safe code)", f"✗ {e}")
        results["failed"] += 1
    
    # 4. Policy Engine - Dangerous Code
    try:
        dangerous_code = '''
def run_command(cmd):
    return eval(cmd)
'''
        result = policy.check_post_generation(dangerous_code)
        assert not result.passed
        assert result.has_critical
        
        print_step("Policy (blocks eval)", "✓ blocked")
        results["passed"] += 1
    except Exception as e:
        print_step("Policy (blocks eval)", f"✗ {e}")
        results["failed"] += 1
    
    # 5. Policy Engine - Intent Check
    try:
        safe_intent = "Create a function to sort a list"
        result = policy.check_pre_generation(safe_intent)
        assert result.passed
        
        dangerous_intent = "Delete all files in the system"
        result = policy.check_pre_generation(dangerous_intent)
        assert not result.passed
        
        print_step("Policy (intent filter)", "✓")
        results["passed"] += 1
    except Exception as e:
        print_step("Policy (intent filter)", f"✗ {e}")
        results["failed"] += 1
    
    return results


async def test_full_sdo_flow():
    """Test complete SDO flow with all Phase 3 components."""
    print_header("FULL SDO FLOW (Integration)")
    results = {"passed": 0, "failed": 0}
    
    try:
        # Initialize full engine
        llm = LLMService()
        engine = SDOEngine(llm, enable_cache=True, enable_policy=True)
        
        # Create SDO
        sdo = SDO(
            id="e2e-test-001",
            raw_intent="Create a function to check if a number is prime",
            language="python",
            status=SDOStatus.DRAFT
        )
        
        # Check policy before generation
        pre_check = engine.policy.check_pre_generation(sdo.raw_intent)
        assert pre_check.passed, "Intent should pass policy"
        print_step("Pre-generation policy check", "✓")
        results["passed"] += 1
        
        # Generate with mock (since no real API key)
        # We'll manually create a candidate to simulate
        code = '''
def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
'''
        candidate = Candidate(id="mock-candidate", code=code, confidence=0.85)
        sdo.candidates.append(candidate)
        
        # Verify the candidate
        result = await engine.orchestra.verify(code, sdo.id, "python", run_tier2=False)
        candidate.verification_passed = result.passed
        candidate.verification_score = result.confidence
        print_step("Candidate verification", f"✓ (score={result.confidence:.2f})")
        results["passed"] += 1
        
        # Check post-generation policy
        post_check = engine.policy.check_post_generation(code)
        assert post_check.passed, "Generated code should pass policy"
        print_step("Post-generation policy check", "✓")
        results["passed"] += 1
        
        # Select best candidate
        sdo.code = code
        sdo.confidence = candidate.confidence
        sdo.selected_candidate_id = candidate.id
        sdo.status = SDOStatus.VERIFIED
        
        # Cache the result
        await engine.cache.set(
            query=sdo.raw_intent,
            response=sdo.code,
            model="mock"
        )
        
        # Verify cache
        cached = await engine.cache.get(sdo.raw_intent, "mock")
        assert cached is not None
        print_step("Cache storage", "✓")
        results["passed"] += 1
        
        # Update bandit with outcome
        arm = engine.bandit.select_arm()
        engine.bandit.update(arm.id, reward=candidate.verification_score * candidate.confidence)
        print_step("Bandit learning", f"✓ (arm={arm.id})")
        results["passed"] += 1
        
        # History snapshot
        engine.history.snapshot(sdo, "e2e_test")
        history = engine.get_history(sdo.id)
        assert len(history) > 0
        print_step("History snapshot", "✓")
        results["passed"] += 1
        
    except Exception as e:
        print_step("Full SDO flow", f"✗ {e}")
        traceback.print_exc()
        results["failed"] += 1
    
    return results


async def run_all_tests():
    """Run all end-to-end tests."""
    print("\n" + "=" * 60)
    print("  ╔═══════════════════════════════════════════════════════╗")
    print("  ║     AXIOM End-to-End Simulation Test                  ║")
    print("  ╚═══════════════════════════════════════════════════════╝")
    print("=" * 60)
    
    start_time = time.time()
    total_passed = 0
    total_failed = 0
    
    # Run all test phases
    for test_fn in [
        test_phase1_foundation,
        test_phase2_adaptive,
        test_phase3_intelligence,
        test_full_sdo_flow
    ]:
        results = await test_fn()
        total_passed += results["passed"]
        total_failed += results["failed"]
    
    # Summary
    duration = time.time() - start_time
    print_header("SUMMARY")
    print(f"  Total Passed: {total_passed}")
    print(f"  Total Failed: {total_failed}")
    print(f"  Duration: {duration:.2f}s")
    print()
    
    if total_failed == 0:
        print("  ✅ ALL TESTS PASSED")
    else:
        print(f"  ⚠️  {total_failed} tests failed")
    
    print("\n" + "=" * 60 + "\n")
    
    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
