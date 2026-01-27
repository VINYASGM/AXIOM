"""
LLM Service Layer
Handles interactions with OpenAI/Anthropic via LangChain.
Includes embedding generation for vector memory.
"""
from typing import Optional, Dict, List, Any
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from sdo import SDO

class IntentParsingResult(BaseModel):
    action: str = Field(description="The primary action (create, modify, delete, test)")
    entity: str = Field(description="The entity type being acted upon (function, class, api, component)")
    description: str = Field(description="A refined description of the intent")
    constraints: List[str] = Field(description="List of technical constraints extracted from intent")
    suggested_refinements: List[str] = Field(description="Questions to ask the user to clarify ambiguity")


class LLMService:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Initialize models if keys are present
        self.model = None
        self.embeddings = None
        
        if self.openai_key:
            self.model = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.1)
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Fallback or alternative could be Anthropic
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for text using OpenAI's text-embedding-3-small.
        Used for vector memory storage and retrieval.
        
        Args:
            text: The text to embed
            
        Returns:
            1536-dimensional embedding vector
        """
        if not self.embeddings:
            # Return zero vector as fallback (for testing without API key)
            return [0.0] * 1536
            
        try:
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return [0.0] * 1536
        
    async def parse_intent(self, raw_intent: str) -> Dict[str, Any]:
        """
        Parse raw natural language intent into structured format.
        """
        if not self.model:
            # Fallback to deterministic logic if no LLM
            return self._mock_parse_intent(raw_intent)
            
        parser = JsonOutputParser(pydantic_object=IntentParsingResult)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a senior software architect. Analyze the user's intent and extract structured requirements. \n{format_instructions}"),
            ("user", "{intent}")
        ])
        
        chain = prompt | self.model | parser
        
        try:
            result = await chain.ainvoke({
                "intent": raw_intent,
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"LLM Parsing failed: {e}")
            return self._mock_parse_intent(raw_intent)

class ReasoningStep(BaseModel):
    step: str = Field(description="Title of the reasoning step")
    explanation: str = Field(description="Detailed explanation of the decision")
    confidence: float = Field(description="Confidence in this step (0.0-1.0)")

class CodeGenerationResult(BaseModel):
    code: str = Field(description="The generated code")
    reasoning: List[ReasoningStep] = Field(description="Chain of thought leading to this code")

    async def generate_code(self, sdo: SDO) -> Dict[str, Any]:
        """
        Generate code and reasoning trace based on the SDO state.
        Uses RAG context if available for better generation.
        """
        if not self.model:
            return self._mock_generate_code(sdo)
        
        # Extract RAG context if present
        rag_context = ""
        if sdo.parsed_intent and isinstance(sdo.parsed_intent, dict):
            rag_context = sdo.parsed_intent.get("_rag_context", "")
        
        parser = JsonOutputParser(pydantic_object=CodeGenerationResult)

        # Build system prompt with optional context
        system_prompt = "You are an expert developer in {language}. Write high-quality, production-ready code based on the following requirements.\n{format_instructions}"
        if rag_context:
            system_prompt += "\n\nUse the following codebase context to inform your implementation:\n{context}"
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", """
Human: You are an expert developer AI system, providing production-ready code based on verified intent.
Use the following pieces of information to provide a concise answer to the question enclosed in <question> tags.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

<context>
{context}
</context>

<question>
Target Language: {language}
Description: {description}
Constraints: {constraints}

Contracts:
{contracts}
</question>

The response must be a JSON object containing the code and a reasoning trace.
Assistant:""")
        ])
        
        chain = prompt | self.model | parser
        
        try:
            result = await chain.ainvoke({
                "language": sdo.language,
                "description": sdo.parsed_intent.get("description", sdo.raw_intent) if sdo.parsed_intent else sdo.raw_intent,
                "constraints": ", ".join(sdo.constraints),
                "contracts": "\n".join([f"- {c.type}: {c.description}" for c in sdo.contracts]),
                "context": rag_context,
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"LLM Generation failed: {e}")
            return self._mock_generate_code(sdo)

    def _mock_parse_intent(self, intent: str) -> Dict[str, Any]:
        """Fallback deterministic parser"""
        intent_lower = intent.lower()
        return {
            "action": "create", # Simplified
            "entity": "function" if "function" in intent_lower else "component",
            "description": intent,
            "constraints": ["mock_constraint"] if "mock" in intent_lower else [],
            "suggested_refinements": ["Did you mean standard implementation?"]
        }

    def _mock_generate_code(self, sdo: SDO) -> Dict[str, Any]:
        """Fallback template generator"""
        lang = sdo.language.lower()
        intent_lower = sdo.raw_intent.lower()
        
        code = f"// Generated from: {sdo.raw_intent}"
        if lang == "python":
            code = f"def generated_function():\n    # Generated from: {sdo.raw_intent}\n    pass"

        # Mock Unit Tests Generation
        if "test" in intent_lower or "pytest" in intent_lower:
            code = """
import pytest
from solution import *

def test_fibonacci_simple():
    # Assuming code has fibonacci function
    # Mocking pass for integration test
    assert True

def test_fibonacci_edge():
    assert True
"""

        return {
            "code": code,
            "reasoning": [
                {"step": "Initial Analysis", "explanation": "Analyzed intent and identified key requirements.", "confidence": 0.9},
                {"step": "Implementation", "explanation": "Implemented core logic using standard patterns.", "confidence": 0.85}
            ]
        }
