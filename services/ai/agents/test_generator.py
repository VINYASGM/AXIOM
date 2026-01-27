from typing import Any
from .base import BaseAgent, AgentResult
from llm import LLMService
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class TestGenerator(BaseAgent):
    """
    Agent responsible for generating unit tests.
    """
    def __init__(self, llm_service: LLMService):
        super().__init__(name="TestGenerator", role="tester")
        self.llm = llm_service

    async def run(self, input_data: Any) -> AgentResult:
        """
        Input data should be a dict with: 'code', 'language', 'contracts'
        """
        try:
            code = input_data.get("code")
            language = input_data.get("language")
            contracts = input_data.get("contracts", [])
            
            if not self.llm.model:
                 # Mock Response
                mock_tests = f"// Test Suite for {language}\n// Generated tests..."
                if language == "python":
                     mock_tests = "import pytest\ndef test_feature():\n    assert True"
                return AgentResult(success=True, data={"tests": mock_tests})

            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert QA engineer. Write comprehensive unit tests for the following code.\nLanguage: {language}"),
                ("user", "Code:\n{code}\n\nContracts/Constraints:\n{contracts}\n\nReturn ONLY the test code.")
            ])

            chain = prompt | self.llm.model | StrOutputParser()
            
            tests = await chain.ainvoke({
                "language": language,
                "code": code,
                "contracts": "\n".join([str(c) for c in contracts])
            })
            
            return AgentResult(success=True, data={"tests": tests})

        except Exception as e:
            return AgentResult(success=False, error=str(e))
