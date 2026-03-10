"""
Unit tests for the Semantic Cache module.
Tests LRU eviction, TTL expiration, semantic similarity, and thread safety.
"""
import pytest
import time
import math
from cache import (
    CacheEntry,
    SemanticCache,
    _generate_key,
    _cosine_similarity,
)


class TestCacheEntry:
    """Test CacheEntry data class."""

    def test_entry_creation(self):
        entry = CacheEntry(
            key="k1", query="hello", response="world", model="gpt-4"
        )
        assert entry.key == "k1"
        assert entry.hit_count == 0

    def test_touch_increments_hit_count(self):
        entry = CacheEntry(key="k1", query="q", response="r", model="m")
        entry.touch()
        assert entry.hit_count == 1
        entry.touch()
        assert entry.hit_count == 2

    def test_expired_entry(self):
        entry = CacheEntry(
            key="k1", query="q", response="r", model="m", ttl_seconds=0
        )
        time.sleep(0.01)
        assert entry.is_expired() is True

    def test_non_expired_entry(self):
        entry = CacheEntry(
            key="k1", query="q", response="r", model="m", ttl_seconds=3600
        )
        assert entry.is_expired() is False

    def test_to_dict(self):
        entry = CacheEntry(key="k1", query="q", response="r", model="m")
        d = entry.to_dict()
        assert d["key"] == "k1"
        assert d["query"] == "q"


class TestHelperFunctions:
    """Test module-level helper functions."""

    def test_generate_key_deterministic(self):
        k1 = _generate_key("hello", "gpt-4")
        k2 = _generate_key("hello", "gpt-4")
        assert k1 == k2

    def test_generate_key_different_for_different_inputs(self):
        k1 = _generate_key("hello", "gpt-4")
        k2 = _generate_key("world", "gpt-4")
        assert k1 != k2

    def test_cosine_similarity_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 0.001

    def test_cosine_similarity_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 0.001

    def test_cosine_similarity_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert _cosine_similarity(a, b) == 0.0


class TestSemanticCache:
    """Test the SemanticCache class."""

    def test_set_and_get_exact_match(self):
        cache = SemanticCache(max_size=10, enable_cleanup=False)
        cache.set("hello", "world", "gpt-4")
        result = cache.get("hello", "gpt-4")
        assert result is not None
        assert result.response == "world"

    def test_get_miss_returns_none(self):
        cache = SemanticCache(max_size=10, enable_cleanup=False)
        result = cache.get("nonexistent", "gpt-4")
        assert result is None

    def test_lru_eviction(self):
        cache = SemanticCache(max_size=2, enable_cleanup=False)
        cache.set("q1", "r1", "gpt-4")
        cache.set("q2", "r2", "gpt-4")
        cache.set("q3", "r3", "gpt-4")  # Should evict q1
        assert cache.get("q1", "gpt-4") is None
        assert cache.get("q3", "gpt-4") is not None

    def test_delete_entry(self):
        cache = SemanticCache(max_size=10, enable_cleanup=False)
        key = cache.set("q", "r", "gpt-4")
        cache.delete(key)
        assert cache.get("q", "gpt-4") is None

    def test_clear(self):
        cache = SemanticCache(max_size=10, enable_cleanup=False)
        cache.set("q1", "r1", "gpt-4")
        cache.set("q2", "r2", "gpt-4")
        cache.clear()
        stats = cache.stats()
        assert stats["size"] == 0

    def test_stats(self):
        cache = SemanticCache(max_size=10, enable_cleanup=False)
        cache.set("q1", "r1", "gpt-4")
        cache.get("q1", "gpt-4")
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["hits"] >= 1

    def test_semantic_similarity_match(self):
        cache = SemanticCache(
            max_size=10, similarity_threshold=0.9, enable_cleanup=False
        )
        # Use identical embeddings to guarantee a semantic hit
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        cache.set("create login form", "code...", "gpt-4", embedding=embedding)
        result = cache.get(
            "make login page", "gpt-4", embedding=embedding
        )
        # Same embedding → similarity = 1.0 → should be a hit
        assert result is not None
