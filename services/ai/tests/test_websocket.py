import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from main import app, manager

# Mock dependencies to avoid DB/Network calls during tests
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch("main.database_service", new_callable=AsyncMock) as mock_db, \
         patch("main.memory_service", new_callable=AsyncMock) as mock_mem, \
         patch("main.eventbus.init_nats", new_callable=AsyncMock), \
         patch("main.TemporalClient.connect", new_callable=AsyncMock), \
         patch("main.sdo_engine", new_callable=MagicMock):
        
        mock_db.initialize.return_value = True
        mock_mem.initialize.return_value = True
        yield

@pytest.mark.asyncio
async def test_websocket_broadcast():
    # We use TestClient as context manager to trigger lifespan (if supported) 
    # OR we can just test the endpoint if lifespan doesn't fail.
    # With mocks above, lifespan should run fine.
    
    with TestClient(app) as client:
        with client.websocket_connect("/ws/test-client") as websocket:
            # Simulate an event broadcast
            payload = {"test": "data", "ivcu_id": "123"}
            await manager.broadcast(payload)
            
            # Receive
            data = websocket.receive_json()
            assert data == payload
            assert data["ivcu_id"] == "123"

