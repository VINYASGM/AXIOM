"""
Shared Test Fixtures for AXIOM AI Services
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_response():
    """Create mock LLM response for testing."""
    return {
        "code": "def hello(name):\n    return f'Hello, {name}!'",
        "confidence": 0.92,
        "reasoning": "Simple string formatting function",
        "tokens_used": 45
    }


@pytest.fixture
def sample_contracts():
    """Sample contracts for testing."""
    return [
        {
            "type": "precondition",
            "expression": "isinstance(name, str)",
            "description": "Name must be a string"
        },
        {
            "type": "postcondition",
            "expression": "isinstance(result, str)",
            "description": "Result must be a string"
        }
    ]


@pytest.fixture
def sample_code_python():
    """Sample Python code for verification testing."""
    return '''
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
'''


@pytest.fixture
def sample_code_javascript():
    """Sample JavaScript code for verification testing."""
    return '''
function fibonacci(n) {
    if (n < 0) {
        throw new Error("n must be non-negative");
    }
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}
'''


@pytest.fixture
def mock_db_pool():
    """Create mock database pool."""
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    conn.transaction.return_value.__aenter__.return_value = None
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    return pool


@pytest.fixture
def mock_nats_client():
    """Create mock NATS client."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.publish = AsyncMock()
    client.subscribe = AsyncMock()
    client.flush = AsyncMock()
    client.close = AsyncMock()
    return client
