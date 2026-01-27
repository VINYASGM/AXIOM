from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class AgentResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseAgent:
    """
    Base class for all specialized agents in AXIOM.
    """
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
    
    async def run(self, input_data: Any) -> AgentResult:
        """
        Main execution method for the agent.
        """
        raise NotImplementedError("Agents must implement run()")
