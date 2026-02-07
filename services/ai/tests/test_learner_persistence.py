
import pytest
import pytest_asyncio
import asyncpg
import json
import os
from unittest.mock import MagicMock
from database import DatabaseService
from learner import LearnerModel

# Mock config
os.environ["DATABASE_URL"] = "postgresql://axiom:axiom@localhost:5432/axiom"

@pytest_asyncio.fixture
async def db_service():
    service = DatabaseService()
    # Assume DB is running for this test. If not, we might need to mock asyncpg.
    # For now, let's try to connect. If it fails, we skip execution or mock.
    try:
        await service.initialize()
        yield service
        await service.close()
    except Exception:
        # Mocking for environment without DB
        service.pool = MagicMock()
        service.pool.acquire = MagicMock()
        service.get_learner_profile = MagicMock(return_value=None)
        service.save_learner_profile = MagicMock()
        yield service

@pytest_asyncio.fixture
async def learner(db_service):
    knowledge = MagicMock()
    llm = MagicMock()
    return LearnerModel(knowledge, llm, db_service)

@pytest.mark.asyncio
async def test_update_skill(learner):
    user_id = "test_user_123"
    
    # Mock DB behavior if needed
    if isinstance(learner.db.pool, MagicMock):
        # Mock get to return empty profile first
        learner.db.get_learner_profile.return_value = {
            "user_id": user_id, 
            "skills": {"verification": 5},
            "learning_style": {},
            "history": []
        }
    
    await learner.update_skill(user_id, "verification", 2)
    
    # Check if save was called
    if isinstance(learner.db.pool, MagicMock):
        learner.db.save_learner_profile.assert_called_once()
        args = learner.db.save_learner_profile.call_args[0][0]
        assert args["skills"]["verification"] == 7 # 5 + 2
    else:
        # Real DB check
        profile = await learner.db.get_learner_profile(user_id)
        assert profile is not None
        assert profile["skills"]["verification"] > 0
