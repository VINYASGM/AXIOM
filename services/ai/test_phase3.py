"""
Test suite for Phase 3 components: Cache, Router, Policy.
"""
import unittest
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cache import SemanticCache, CacheEntry, _cosine_similarity
from router import LLMRouter, MockProvider, ChatRequest, ChatMessage, RoutingRule
from policy import PolicyEngine, PolicyPhase, PolicySeverity


class TestSemanticCache(unittest.TestCase):
    """Test the SemanticCache class."""
    
    def setUp(self):
        self.cache = SemanticCache(max_size=10, enable_cleanup=False)
    
    def test_cache_set_get(self):
        """Test basic set and get."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            key = await self.cache.set(
                query="Create fibonacci function",
                response="def fib(n): return n",
                model="gpt-4"
            )
            self.assertIsNotNone(key)
            
            entry = await self.cache.get("Create fibonacci function", "gpt-4")
            self.assertIsNotNone(entry)
            self.assertEqual(entry.response, "def fib(n): return n")
        
        loop.run_until_complete(run())
        loop.close()
    
    def test_cache_miss(self):
        """Test cache miss."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            entry = await self.cache.get("Unknown query", "gpt-4")
            self.assertIsNone(entry)
        
        loop.run_until_complete(run())
        loop.close()
    
    def test_cache_stats(self):
        """Test cache statistics."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            await self.cache.set("q1", "r1", "model")
            await self.cache.get("q1", "model")  # Hit
            await self.cache.get("q2", "model")  # Miss
            
            stats = self.cache.stats()
            self.assertEqual(stats["hits"], 1)
            self.assertEqual(stats["misses"], 1)
            self.assertGreater(stats["hit_rate"], 0)
        
        loop.run_until_complete(run())
        loop.close()
    
    def test_cache_eviction(self):
        """Test LRU eviction."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            # Fill cache to max
            for i in range(12):  # Max is 10
                await self.cache.set(f"query{i}", f"response{i}", "model")
            
            # Should have evicted oldest
            stats = self.cache.stats()
            self.assertLessEqual(stats["size"], 10)
        
        loop.run_until_complete(run())
        loop.close()
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(_cosine_similarity(a, b), 1.0)
        
        c = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(_cosine_similarity(a, c), 0.0)


class TestLLMRouter(unittest.TestCase):
    """Test the LLMRouter class."""
    
    def setUp(self):
        self.router = LLMRouter()
        self.mock = MockProvider()
        self.router.register_provider("mock", self.mock)
        self.router.set_fallback("mock")
    
    def test_register_provider(self):
        """Test provider registration."""
        self.assertIn("mock", self.router.list_providers())
    
    def test_route_to_mock(self):
        """Test routing to mock provider."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="mock-fast"
        )
        provider = self.router.route(request)
        self.assertEqual(provider.name, "mock")
    
    def test_chat_request(self):
        """Test actual chat request through router."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Create a function")],
                model="mock-fast"
            )
            response = await self.router.chat(request)
            self.assertEqual(response.provider, "mock")
            self.assertIn("generated_function", response.content.lower())
        
        loop.run_until_complete(run())
        loop.close()
    
    def test_routing_rules(self):
        """Test routing rules."""
        rule = RoutingRule(
            condition={"model_prefix": "mock"},
            provider="mock",
            priority=10
        )
        self.router.add_rule(rule)
        
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="mock-quality"
        )
        provider = self.router.route(request)
        self.assertEqual(provider.name, "mock")
    
    def test_metrics_tracking(self):
        """Test metrics are tracked."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Test")],
                model="mock"
            )
            await self.router.chat(request)
            
            metrics = self.router.get_metrics()
            self.assertIn("mock", metrics["requests"])
            self.assertEqual(metrics["requests"]["mock"], 1)
        
        loop.run_until_complete(run())
        loop.close()


class TestPolicyEngine(unittest.TestCase):
    """Test the PolicyEngine class."""
    
    def setUp(self):
        self.engine = PolicyEngine()
    
    def test_safe_code_passes(self):
        """Test that safe code passes policies."""
        code = '''
def fibonacci(n: int) -> int:
    """Calculate fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''
        result = self.engine.check_post_generation(code)
        self.assertTrue(result.passed)
    
    def test_eval_blocked(self):
        """Test that eval() is blocked."""
        code = '''
def dangerous():
    user_input = input("Enter code: ")
    return eval(user_input)
'''
        result = self.engine.check_post_generation(code)
        self.assertFalse(result.passed)
        self.assertTrue(result.has_critical)
        self.assertTrue(any("eval" in v.message for v in result.violations))
    
    def test_exec_blocked(self):
        """Test that exec() is blocked."""
        code = '''
def run_code(code_str):
    exec(code_str)
'''
        result = self.engine.check_post_generation(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("exec" in v.message for v in result.violations))
    
    def test_os_system_blocked(self):
        """Test that os.system() is blocked."""
        code = '''
import os
def run_command(cmd):
    os.system(cmd)
'''
        result = self.engine.check_post_generation(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("os.system" in v.message for v in result.violations))
    
    def test_type_hint_warning(self):
        """Test warning for missing type hints."""
        code = '''
def add(a, b):
    return a + b
'''
        result = self.engine.check_post_generation(code)
        # Should pass (warning only) but have violations
        self.assertTrue(result.passed)
        self.assertGreater(result.warning_count, 0)
    
    def test_dangerous_intent_blocked(self):
        """Test that dangerous intents are blocked."""
        intent = "Create a function to delete all files in the system"
        result = self.engine.check_pre_generation(intent)
        self.assertFalse(result.passed)
        self.assertTrue(result.has_critical)
    
    def test_safe_intent_passes(self):
        """Test that safe intents pass."""
        intent = "Create a fibonacci function"
        result = self.engine.check_pre_generation(intent)
        self.assertTrue(result.passed)


if __name__ == "__main__":
    print("=" * 60)
    print("  AXIOM Phase 3 - Intelligence Layer Tests")
    print("=" * 60)
    print()
    
    unittest.main(verbosity=2)
