"""
Knowledge Service
High-level service for Result Augmented Generation (RAG) and knowledge management.
Wraps the lower-level MemoryService to provide context-aware capabilities to the SDO Engine.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from memory import MemoryService, RetrievalResult

class RetrievedContext(BaseModel):
    """Contains all retrieved context for a generation task"""
    code_chunks: List[RetrievalResult]
    similar_intents: List[RetrievalResult]
    
    def to_prompt_str(self) -> str:
        """Format context for LLM prompt"""
        context_parts = []
        
        if self.code_chunks:
            context_parts.append("## Relevant Codebase Context:")
            for i, chunk in enumerate(self.code_chunks):
                file_path = chunk.metadata.get("file_path", "unknown")
                context_parts.append(f"--- Chunk {i+1} ({file_path}) ---")
                context_parts.append(chunk.content)
                context_parts.append("---")
        
        if self.similar_intents:
            context_parts.append("\n## Similar Past Intents & Solutions:")
            for i, intent in enumerate(self.similar_intents):
                context_parts.append(f"--- Example {i+1} ---")
                context_parts.append(f"Intent: {intent.content}")
                # Ideally we would store the solution code with the intent too
                # For now just showing the intent might help with style/phrasing
                context_parts.append("---")
                
        return "\n".join(context_parts)


class KnowledgeService:
    """
    Orchestrates knowledge retrieval and storage.
    Acts as the bridge between SDO Engine and Memory Service.
    """
    
    def __init__(self, memory_service: MemoryService):
        self.memory = memory_service
        
    async def retrieve_context_for_intent(self, intent: str) -> RetrievedContext:
        """
        Gather all relevant context for a given user intent.
        
        Args:
            intent: The user's raw intent string
            
        Returns:
            RetrievedContext object containing code chunks and similar intents
        """
        # Parallel retrieval could happen here if needed using asyncio.gather
        # For now, sequential is fine
        
        # 1. Get relevant code chunks from the project
        code_chunks = await self.memory.retrieve_relevant_code(
            query=intent,
            limit=5
        )
        
        # 2. Get similar past intents to see how we solved things before
        similar_intents = await self.memory.retrieve_similar_intents(
            intent=intent,
            limit=3
        )
        
        return RetrievedContext(
            code_chunks=code_chunks,
            similar_intents=similar_intents
        )

    async def ingest_sdo_result(self, sdo_id: str, intent: str, code: str, language: str):
        """
        Store a completed SDO verification result back into memory.
        This closes the learning loop.
        
        Args:
            sdo_id: ID of the SDO
            intent: User's intent
            code: The verified code
            language: Programming language
        """
        # Store context/intent link
        await self.memory.store_intent(
            raw_intent=intent,
            sdo_id=sdo_id,
            confidence=1.0 # If we are ingesting it, we trust it
        )
        
        # Store the generated code
        # In a real system, we might chunk this intelligently
        await self.memory.store_code_chunk(
            content=code,
            file_path=f"generated/{sdo_id}.{language}", # Virtual path
            language=language,
            sdo_id=sdo_id
        )
