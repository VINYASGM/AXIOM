"""
Knowledge Service
High-level service for Result Augmented Generation (RAG) and knowledge management.
Wraps the lower-level MemoryService to provide context-aware capabilities to the SDO Engine.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from memory import MemoryService, RetrievalResult

class DecisionNode(BaseModel):
    """A single step in the reasoning process"""
    id: str
    type: str  # 'constraint' | 'selection' | 'inference'
    title: str
    description: str
    confidence: float
    alternatives: Optional[List[str]] = None

class ReasoningTrace(BaseModel):
    """Complete explanation of a generation's decision path"""
    ivcu_id: str
    nodes: List[DecisionNode]
    consistent: bool = True

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
    
    def __init__(self, memory_service: MemoryService, neo4j_uri: str = "bolt://neo4j:7687", neo4j_auth: tuple = ("neo4j", "axiom_dev_password")):
        self.memory = memory_service
        self.driver = None
        try:
             from neo4j import GraphDatabase
             self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
        except ImportError:
             print("Neo4j driver not installed. Graph features disabled.")
        except Exception as e:
             print(f"Failed to connect to Neo4j: {e}")
        
    def close(self):
        if self.driver:
            self.driver.close()

    # ... [retrieve_context_for_intent unchanged] ...
    
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
        await self.memory.store_code_chunk(
            content=code,
            file_path=f"generated/{sdo_id}.{language}", # Virtual path
            language=language,
            sdo_id=sdo_id
        )
        
        # 3. Store Graph Relationships (Neo4j)
        if self.driver:
            try:
                def _create_graph_nodes(tx, sdo_id, intent, language):
                    # Create Intent Node
                    tx.run("MERGE (i:Intent {id: $id}) "
                           "ON CREATE SET i.text = $text, i.created_at = timestamp()",
                           id=sdo_id, text=intent)
                    
                    # Create Implementation Node
                    tx.run("MERGE (c:Code {id: $id}) "
                           "ON CREATE SET c.language = $lang",
                           id=sdo_id, lang=language)
                           
                    # Link
                    tx.run("MATCH (i:Intent {id: $id}), (c:Code {id: $id}) "
                           "MERGE (i)-[:IMPLEMENTED_BY]->(c)",
                           id=sdo_id)
                
                with self.driver.session() as session:
                    session.execute_write(_create_graph_nodes, sdo_id, intent, language)
                    
            except Exception as e:
                print(f"Graph ingestion failed: {e}")
