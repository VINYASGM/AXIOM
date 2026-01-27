from typing import Any
from .base import BaseAgent, AgentResult
from llm import LLMService
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class DocGenerator(BaseAgent):
    """
    Agent responsible for generating documentation.
    """
    def __init__(self, llm_service: LLMService):
        super().__init__(name="DocGenerator", role="technical_writer")
        self.llm = llm_service

    async def run(self, input_data: Any) -> AgentResult:
        """
        Input data: 'code', 'language'
        """
        try:
            code = input_data.get("code")
            language = input_data.get("language")

            if not self.llm.model:
                 return AgentResult(success=True, data={"docs": "# Documentation\n\nAutomatically generated."})

            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a technical writer. Write clear, markdown-formatted documentation for the code."),
                ("user", "Code ({language}):\n{code}\n\nReturn the documentation in Markdown.")
            ])

            chain = prompt | self.llm.model | StrOutputParser()
            docs = await chain.ainvoke({"language": language, "code": code})
            
            return AgentResult(success=True, data={"docs": docs})

        except Exception as e:
            return AgentResult(success=False, error=str(e))
