from typing import Any
from .base import BaseAgent, AgentResult
from llm import LLMService
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class RefactorAgent(BaseAgent):
    """
    Agent responsible for refactoring code.
    """
    def __init__(self, llm_service: LLMService):
        super().__init__(name="RefactorAgent", role="engineer")
        self.llm = llm_service

    async def run(self, input_data: Any) -> AgentResult:
        """
        Input data: 'code', 'language', 'instruction'
        """
        try:
            code = input_data.get("code")
            language = input_data.get("language")
            instruction = input_data.get("instruction")

            if not self.llm.model:
                 return AgentResult(success=True, data={"code": code + "\n// Refactored"})

            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a senior developer. Refactor the code based on the instructions. Do not change behavior unless asked."),
                ("user", "Code ({language}):\n{code}\n\nInstruction: {instruction}\n\nReturn ONLY the refactored code.")
            ])

            chain = prompt | self.llm.model | StrOutputParser()
            refactored_code = await chain.ainvoke({
                "language": language, 
                "code": code,
                "instruction": instruction
            })
            
            return AgentResult(success=True, data={"code": refactored_code})

        except Exception as e:
            return AgentResult(success=False, error=str(e))
