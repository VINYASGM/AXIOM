from typing import Any, Dict, Optional
from .base import BaseAgent, AgentResult
from llm import LLMService
from sdo import SDO

class CodeGenerator(BaseAgent):
    """
    Agent responsible for generating code from SDO specifications.
    Utilizes LLMService and handles reasoning extraction.
    """
    def __init__(self, llm_service: LLMService):
        super().__init__(name="CodeGenerator", role="engineer")
        self.llm = llm_service

    async def run(self, sdo: SDO) -> AgentResult:
        try:
            # Generate code using LLM Service
            result = await self.llm.generate_code(sdo)
            
            if isinstance(result, str):
                # Legacy or mock string return
                return AgentResult(
                    success=True,
                    data={"code": result, "reasoning": []}
                )
            
            return AgentResult(
                success=True,
                data={
                    "code": result.get("code", ""),
                    "reasoning": result.get("reasoning", [])
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
