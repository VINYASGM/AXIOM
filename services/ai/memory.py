"""
Memory Service Layer
Handles vector storage and retrieval via Qdrant for context-aware generation.
"""
from typing import Optional, List, Dict, Any
import os
import uuid
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from pydantic import BaseModel, Field


class MemoryConfig:
    """Configuration for memory service"""
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
    EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small
    
    # Collection names
    CODE_COLLECTION = "code_chunks"
    INTENT_COLLECTION = "intent_history"
    CONTEXT_COLLECTION = "project_context"


class CodeChunk(BaseModel):
    """Represents a stored code chunk"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    file_path: Optional[str] = None
    language: str = "python"
    sdo_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class IntentRecord(BaseModel):
    """Represents a stored intent"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_intent: str
    parsed_intent: Optional[Dict[str, Any]] = None
    sdo_id: Optional[str] = None
    confidence: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RetrievalResult(BaseModel):
    """Result from context retrieval"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}


class MemoryService:
    """
    Vector memory service using Qdrant.
    Provides storage and retrieval for code chunks, intents, and project context.
    """
    
    def __init__(self, embed_fn=None):
        """
        Initialize memory service.
        
        Args:
            embed_fn: Async function to generate embeddings. 
                      Signature: async def embed_fn(text: str) -> List[float]
        """
        self.client: Optional[QdrantClient] = None
        self.embed_fn = embed_fn
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize connection and create collections if needed."""
        try:
            self.client = QdrantClient(url=MemoryConfig.QDRANT_URL)
            
            # Create collections if they don't exist
            await self._ensure_collection(
                MemoryConfig.CODE_COLLECTION,
                MemoryConfig.EMBEDDING_DIM
            )
            await self._ensure_collection(
                MemoryConfig.INTENT_COLLECTION,
                MemoryConfig.EMBEDDING_DIM
            )
            await self._ensure_collection(
                MemoryConfig.CONTEXT_COLLECTION,
                MemoryConfig.EMBEDDING_DIM
            )
            
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize MemoryService: {e}")
            return False
    
    async def _ensure_collection(self, name: str, vector_size: int):
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == name for c in collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"Created collection: {name}")
        except Exception as e:
            print(f"Error ensuring collection {name}: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Qdrant connection health."""
        try:
            if not self.client:
                return {"status": "not_initialized", "connected": False}
            
            # Try to get collections as a health check
            collections = self.client.get_collections()
            return {
                "status": "healthy",
                "connected": True,
                "collections": [c.name for c in collections.collections],
                "url": MemoryConfig.QDRANT_URL
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "error": str(e)
            }
    
    def _fixed_size_chunking(self, text: str, max_tokens: int = 300, overlap_percentage: int = 20) -> List[str]:
        """
        Split text into chunks of fixed size with overlap.
        Simple logic assuming ~4 chars per token for approximation.
        """
        chunk_size_chars = max_tokens * 4
        overlap_chars = int(chunk_size_chars * (overlap_percentage / 100))
        
        chunks = []
        if len(text) <= chunk_size_chars:
            return [text]
            
        start = 0
        while start < len(text):
            end = start + chunk_size_chars
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Move start forward by stride (size - overlap)
            start += (chunk_size_chars - overlap_chars)
            
        return chunks

    async def store_code_chunk(
        self,
        content: str,
        file_path: Optional[str] = None,
        language: str = "python",
        sdo_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Store code content in vector memory with Fixed Size Chunking.
        
        Returns:
            The ID of the first stored chunk, or None on failure.
        """
        if not self.embed_fn:
            print("No embedding function configured")
            return None
            
        try:
            # 1. Chunk the content
            text_chunks = self._fixed_size_chunking(content)
            
            first_id = None
            points = []
            
            # 2. Process each chunk
            for i, chunk_text in enumerate(text_chunks):
                # Generate embedding
                embedding = await self.embed_fn(chunk_text)
                chunk_id = str(uuid.uuid4())
                if i == 0:
                    first_id = chunk_id
                
                # Create record
                points.append(PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload={
                        "content": chunk_text,
                        "file_path": file_path,
                        "language": language,
                        "sdo_id": sdo_id,
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                        "created_at": datetime.utcnow().isoformat()
                    }
                ))
            
            # 3. Batch upsert to Qdrant
            if points:
                self.client.upsert(
                    collection_name=MemoryConfig.CODE_COLLECTION,
                    points=points
                )
            
            print(f"Stored {len(points)} chunks for {file_path or 'content'}")
            return first_id
        except Exception as e:
            print(f"Failed to store code chunk: {e}")
            return None
    
    async def store_intent(
        self,
        raw_intent: str,
        parsed_intent: Optional[Dict[str, Any]] = None,
        sdo_id: Optional[str] = None,
        confidence: float = 0.0
    ) -> Optional[str]:
        """
        Store an intent in vector memory for future retrieval.
        
        Returns:
            The ID of the stored intent, or None on failure.
        """
        if not self.embed_fn:
            print("No embedding function configured")
            return None
            
        try:
            # Generate embedding from raw intent
            embedding = await self.embed_fn(raw_intent)
            
            # Create intent record
            record = IntentRecord(
                raw_intent=raw_intent,
                parsed_intent=parsed_intent,
                sdo_id=sdo_id,
                confidence=confidence
            )
            
            # Store in Qdrant
            self.client.upsert(
                collection_name=MemoryConfig.INTENT_COLLECTION,
                points=[
                    PointStruct(
                        id=record.id,
                        vector=embedding,
                        payload={
                            "raw_intent": record.raw_intent,
                            "parsed_intent": record.parsed_intent,
                            "sdo_id": record.sdo_id,
                            "confidence": record.confidence,
                            "created_at": record.created_at
                        }
                    )
                ]
            )
            
            return record.id
        except Exception as e:
            print(f"Failed to store intent: {e}")
            return None
    
    async def retrieve_context(
        self,
        query: str,
        collection: str = "code_chunks",
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant context for a query using semantic search.
        
        Args:
            query: The search query
            collection: Which collection to search (code_chunks, intent_history)
            limit: Maximum number of results
            
        Returns:
            List of retrieval results with content and scores
        """
        if not self.embed_fn:
            print("No embedding function configured")
            return []
            
        try:
            # Generate query embedding
            query_embedding = await self.embed_fn(query)
            
            # Search in Qdrant
            results = self.client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=limit
            )
            
            # Convert to RetrievalResult
            return [
                RetrievalResult(
                    id=str(r.id),
                    content=r.payload.get("content", r.payload.get("raw_intent", "")),
                    score=r.score,
                    metadata={k: v for k, v in r.payload.items() if k != "content"}
                )
                for r in results
            ]
        except Exception as e:
            print(f"Failed to retrieve context: {e}")
            return []
    
    async def retrieve_similar_intents(
        self,
        intent: str,
        limit: int = 3
    ) -> List[RetrievalResult]:
        """
        Find similar past intents for pattern matching.
        
        Useful for:
        - Suggesting refinements based on past successful intents
        - Learning from previous generations
        """
        return await self.retrieve_context(
            query=intent,
            collection=MemoryConfig.INTENT_COLLECTION,
            limit=limit
        )
    
    async def retrieve_relevant_code(
        self,
        query: str,
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant code chunks for context-aware generation.
        
        Used by the generation flow to provide context to the LLM.
        """
        return await self.retrieve_context(
            query=query,
            collection=MemoryConfig.CODE_COLLECTION,
            limit=limit
        )
