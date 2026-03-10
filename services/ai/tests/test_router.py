"""
Unit tests for the LLM Router module.
Tests routing logic, fallback, mock providers, and metrics.
"""
import pytest
import asyncio
from router import (
    ProviderStatus,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MockProvider,
    RoutingRule,
    RouterMetrics,
)


class TestMockProvider:
    """Test the MockProvider for correct responses."""

    def test_mock_provider_name(self):
        p = MockProvider(name="test-mock")
        assert p.name == "test-mock"

    def test_mock_provider_models(self):
        p = MockProvider()
        models = p.models
        assert isinstance(models, list)

    @pytest.mark.asyncio
    async def test_mock_provider_chat(self):
        p = MockProvider(latency_ms=10)
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="mock-model",
        )
        resp = await p.chat(req)
        assert isinstance(resp, ChatResponse)
        assert len(resp.content) > 0

    @pytest.mark.asyncio
    async def test_mock_provider_health(self):
        p = MockProvider()
        ok = await p.health_check()
        assert ok is True


class TestRoutingRule:
    """Test routing rule matching."""

    def test_rule_matches_model(self):
        rule = RoutingRule(
            condition={"model": "gpt-4"},
            provider="openai",
            priority=10,
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            model="gpt-4",
        )
        assert rule.matches(req) is True

    def test_rule_does_not_match_different_model(self):
        rule = RoutingRule(
            condition={"model": "gpt-4"},
            provider="openai",
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            model="claude-3",
        )
        assert rule.matches(req) is False


class TestRouterMetrics:
    """Test metrics recording."""

    def test_record_request(self):
        m = RouterMetrics()
        m.record_request("openai", 150.0)
        assert m.request_count.get("openai", 0) == 1

    def test_record_error(self):
        m = RouterMetrics()
        m.record_error("openai")
        assert m.error_count.get("openai", 0) == 1

    def test_avg_latency(self):
        m = RouterMetrics()
        m.record_request("openai", 100.0)
        m.record_request("openai", 200.0)
        avg = m.get_avg_latency("openai")
        assert abs(avg - 150.0) < 0.01

    def test_to_dict(self):
        m = RouterMetrics()
        m.record_request("mock", 50.0)
        d = m.to_dict()
        assert "request_count" in d
        assert "error_count" in d


class TestChatModels:
    """Test chat data models."""

    def test_chat_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"

    def test_chat_request_defaults(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hi")],
            model="gpt-4",
        )
        assert req.temperature == 0.7
        assert req.max_tokens == 2048
        assert req.stream is False

    def test_chat_response(self):
        resp = ChatResponse(
            content="Hello back",
            model="gpt-4",
            provider="openai",
        )
        assert resp.finish_reason == "stop"
