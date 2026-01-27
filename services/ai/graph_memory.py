"""
GraphRAG Unified Memory Layer

Combines vector similarity search with graph traversal for enhanced context retrieval.
Implements the "Find similar code (Vector) AND its dependencies (Graph)" pattern.

Architecture v2.1 compliant with support for:
- pgvectorscale (PostgreSQL extension) for vector storage
- DGraph/Neo4j for graph relationships
- Three-tier memory: Working → Project → Organization
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncpg


class MemoryTier(str, Enum):
    """Memory hierarchy tiers."""
    WORKING = "working"      # Current session context
    PROJECT = "project"      # Project-wide knowledge
    ORGANIZATION = "org"     # Organization-level patterns


class RelationshipType(str, Enum):
    """Types of relationships between memory nodes."""
    IMPLEMENTS = "implements"     # Intent -> Code
    DEPENDS_ON = "depends_on"     # Code -> Dependency
    SUPERSEDES = "supersedes"     # New version -> Old version
    REFINES = "refines"           # Refined intent -> Original
    TESTS = "tests"               # Test -> Implementation
    DOCUMENTS = "documents"       # Doc -> Code


@dataclass
class MemoryNode:
    """A node in the memory graph."""
    id: str
    content: str
    node_type: str  # intent, code, decision, constraint, fact, dependency, convention, bugfix
    tier: MemoryTier
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    source_ivcu_id: Optional[str] = None
    project_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "node_type": self.node_type,
            "tier": self.tier.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_ivcu_id": self.source_ivcu_id,
            "project_id": self.project_id
        }


@dataclass
class MemoryEdge:
    """An edge connecting memory nodes."""
    id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    metadata: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship.value,
            "weight": self.weight,
            "metadata": self.metadata
        }


@dataclass
class GraphRAGResult:
    """Result from a GraphRAG query."""
    primary_nodes: List[MemoryNode]           # Direct vector similarity matches
    related_nodes: List[MemoryNode]           # Graph-traversed related nodes
    relationships: List[MemoryEdge]           # Relationships between nodes
    query_time_ms: float
    vector_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_nodes": [n.to_dict() for n in self.primary_nodes],
            "related_nodes": [n.to_dict() for n in self.related_nodes],
            "relationships": [e.to_dict() for e in self.relationships],
            "query_time_ms": round(self.query_time_ms, 2),
            "vector_score": self.vector_score
        }
    
    def get_context(self) -> str:
        """Get combined context from all nodes."""
        contexts = []
        for node in self.primary_nodes + self.related_nodes:
            contexts.append(f"[{node.node_type}] {node.content}")
        return "\n\n".join(contexts)


class GraphMemoryStore:
    """
    Unified GraphRAG memory store.
    
    Combines:
    - pgvectorscale for vector similarity search
    - Graph structure for relationship traversal
    - Three-tier memory hierarchy
    """
    
    def __init__(self, pool: asyncpg.Pool, embedding_service=None):
        self.pool = pool
        self.embedding_service = embedding_service
        self._embedding_dim = 1536  # OpenAI ada-002 default
    
    async def initialize_schema(self):
        """Create GraphRAG tables using pgvectorscale."""
        async with self.pool.acquire() as conn:
            # Enable pgvector extension if available
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            except Exception as e:
                print(f"pgvector extension not available: {e}")
            
            # Memory nodes table with vector embedding
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    tier TEXT NOT NULL DEFAULT 'project',
                    embedding vector({self._embedding_dim}),
                    metadata JSONB DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    source_ivcu_id UUID,
                    project_id UUID,
                    superseded_by UUID,
                    is_active BOOLEAN DEFAULT TRUE
                );
                
                CREATE INDEX IF NOT EXISTS idx_memory_nodes_type ON memory_nodes(node_type);
                CREATE INDEX IF NOT EXISTS idx_memory_nodes_tier ON memory_nodes(tier);
                CREATE INDEX IF NOT EXISTS idx_memory_nodes_project ON memory_nodes(project_id);
                CREATE INDEX IF NOT EXISTS idx_memory_nodes_active ON memory_nodes(is_active);
            """)
            
            # Create vector index if pgvector available
            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_nodes_embedding 
                    ON memory_nodes 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
            except Exception:
                pass  # Vector index creation may fail without pgvector
            
            # Memory edges table (graph relationships)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_edges (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
                    target_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
                    relationship TEXT NOT NULL,
                    weight FLOAT DEFAULT 1.0,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(source_id, target_id, relationship)
                );
                
                CREATE INDEX IF NOT EXISTS idx_memory_edges_source ON memory_edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_memory_edges_target ON memory_edges(target_id);
                CREATE INDEX IF NOT EXISTS idx_memory_edges_rel ON memory_edges(relationship);
            """)
            
            # Impact tracking view
            await conn.execute("""
                CREATE OR REPLACE VIEW memory_impact_graph AS
                SELECT 
                    n1.id as source_id,
                    n1.content as source_content,
                    n1.node_type as source_type,
                    e.relationship,
                    n2.id as target_id,
                    n2.content as target_content,
                    n2.node_type as target_type
                FROM memory_nodes n1
                JOIN memory_edges e ON n1.id = e.source_id
                JOIN memory_nodes n2 ON e.target_id = n2.id
                WHERE n1.is_active = TRUE AND n2.is_active = TRUE;
            """)
    
    async def store(
        self,
        content: str,
        node_type: str,
        tier: MemoryTier = MemoryTier.PROJECT,
        metadata: Optional[Dict[str, Any]] = None,
        source_ivcu_id: Optional[str] = None,
        project_id: Optional[str] = None,
        relationships: Optional[List[Tuple[str, RelationshipType]]] = None
    ) -> str:
        """
        Store a memory node with optional relationships.
        
        Args:
            content: The content to store
            node_type: Type of node (intent, code, decision, etc.)
            tier: Memory tier (working, project, org)
            metadata: Additional metadata
            source_ivcu_id: Source IVCU if applicable
            project_id: Project ID
            relationships: List of (target_id, relationship_type) tuples
            
        Returns:
            The node ID
        """
        import uuid
        
        # Generate embedding if service available
        embedding = None
        if self.embedding_service:
            try:
                embedding = await self.embedding_service.embed(content)
            except Exception as e:
                print(f"Embedding generation failed: {e}")
        
        node_id = str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Insert node
                if embedding:
                    await conn.execute("""
                        INSERT INTO memory_nodes 
                            (id, content, node_type, tier, embedding, metadata, source_ivcu_id, project_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        uuid.UUID(node_id),
                        content,
                        node_type,
                        tier.value,
                        embedding,
                        json.dumps(metadata or {}),
                        uuid.UUID(source_ivcu_id) if source_ivcu_id else None,
                        uuid.UUID(project_id) if project_id else None
                    )
                else:
                    await conn.execute("""
                        INSERT INTO memory_nodes 
                            (id, content, node_type, tier, metadata, source_ivcu_id, project_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        uuid.UUID(node_id),
                        content,
                        node_type,
                        tier.value,
                        json.dumps(metadata or {}),
                        uuid.UUID(source_ivcu_id) if source_ivcu_id else None,
                        uuid.UUID(project_id) if project_id else None
                    )
                
                # Insert relationships
                if relationships:
                    for target_id, rel_type in relationships:
                        await conn.execute("""
                            INSERT INTO memory_edges (source_id, target_id, relationship)
                            VALUES ($1, $2, $3)
                            ON CONFLICT DO NOTHING
                        """,
                            uuid.UUID(node_id),
                            uuid.UUID(target_id),
                            rel_type.value
                        )
        
        return node_id
    
    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship: RelationshipType,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a relationship between nodes."""
        import uuid
        
        edge_id = str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO memory_edges (id, source_id, target_id, relationship, weight, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (source_id, target_id, relationship) DO UPDATE SET
                    weight = EXCLUDED.weight,
                    metadata = EXCLUDED.metadata
            """,
                uuid.UUID(edge_id),
                uuid.UUID(source_id),
                uuid.UUID(target_id),
                relationship.value,
                weight,
                json.dumps(metadata or {})
            )
        
        return edge_id
    
    async def search(
        self,
        query: str,
        project_id: Optional[str] = None,
        tier: Optional[MemoryTier] = None,
        node_types: Optional[List[str]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        include_related: bool = True,
        max_depth: int = 2
    ) -> GraphRAGResult:
        """
        Unified GraphRAG search.
        
        Combines vector similarity with graph traversal:
        1. Find similar nodes via vector search
        2. Traverse graph to find related context
        
        Args:
            query: Search query
            project_id: Filter by project
            tier: Filter by memory tier
            node_types: Filter by node types
            limit: Max primary results
            similarity_threshold: Min similarity score
            include_related: Whether to include graph-related nodes
            max_depth: Graph traversal depth
            
        Returns:
            GraphRAGResult with primary and related nodes
        """
        import time
        import uuid
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = None
        if self.embedding_service:
            try:
                query_embedding = await self.embedding_service.embed(query)
            except Exception as e:
                print(f"Query embedding failed: {e}")
        
        async with self.pool.acquire() as conn:
            # Vector similarity search
            if query_embedding:
                # Use pgvector cosine similarity
                query_str = """
                    SELECT 
                        id, content, node_type, tier, metadata, created_at,
                        source_ivcu_id, project_id,
                        1 - (embedding <=> $1) as similarity
                    FROM memory_nodes
                    WHERE is_active = TRUE
                """
                params = [query_embedding]
                param_idx = 2
                
                if project_id:
                    query_str += f" AND project_id = ${param_idx}"
                    params.append(uuid.UUID(project_id))
                    param_idx += 1
                
                if tier:
                    query_str += f" AND tier = ${param_idx}"
                    params.append(tier.value)
                    param_idx += 1
                
                if node_types:
                    query_str += f" AND node_type = ANY(${param_idx})"
                    params.append(node_types)
                    param_idx += 1
                
                query_str += f"""
                    AND 1 - (embedding <=> $1) >= ${param_idx}
                    ORDER BY similarity DESC
                    LIMIT ${param_idx + 1}
                """
                params.extend([similarity_threshold, limit])
                
                rows = await conn.fetch(query_str, *params)
            else:
                # Fallback to text search
                query_str = """
                    SELECT 
                        id, content, node_type, tier, metadata, created_at,
                        source_ivcu_id, project_id,
                        ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) as similarity
                    FROM memory_nodes
                    WHERE is_active = TRUE
                    AND to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                """
                params = [query]
                param_idx = 2
                
                if project_id:
                    query_str += f" AND project_id = ${param_idx}"
                    params.append(uuid.UUID(project_id))
                    param_idx += 1
                
                query_str += f" ORDER BY similarity DESC LIMIT ${param_idx}"
                params.append(limit)
                
                rows = await conn.fetch(query_str, *params)
            
            # Convert to MemoryNode objects
            primary_nodes = []
            primary_ids = set()
            best_score = 0.0
            
            for row in rows:
                node = MemoryNode(
                    id=str(row['id']),
                    content=row['content'],
                    node_type=row['node_type'],
                    tier=MemoryTier(row['tier']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    created_at=row['created_at'],
                    source_ivcu_id=str(row['source_ivcu_id']) if row['source_ivcu_id'] else None,
                    project_id=str(row['project_id']) if row['project_id'] else None
                )
                primary_nodes.append(node)
                primary_ids.add(node.id)
                if row['similarity'] > best_score:
                    best_score = row['similarity']
            
            # Graph traversal for related nodes
            related_nodes = []
            relationships = []
            
            if include_related and primary_ids:
                # Get related nodes up to max_depth
                related_rows = await conn.fetch("""
                    WITH RECURSIVE related AS (
                        -- Start with edges from primary nodes
                        SELECT 
                            e.source_id, e.target_id, e.relationship, e.weight,
                            e.metadata as edge_metadata, 1 as depth
                        FROM memory_edges e
                        WHERE e.source_id = ANY($1::uuid[]) OR e.target_id = ANY($1::uuid[])
                        
                        UNION
                        
                        -- Recurse
                        SELECT 
                            e.source_id, e.target_id, e.relationship, e.weight,
                            e.metadata, r.depth + 1
                        FROM memory_edges e
                        JOIN related r ON (e.source_id = r.target_id OR e.target_id = r.source_id)
                        WHERE r.depth < $2
                    )
                    SELECT DISTINCT
                        n.id, n.content, n.node_type, n.tier, n.metadata, n.created_at,
                        n.source_ivcu_id, n.project_id,
                        r.source_id as rel_source, r.target_id as rel_target,
                        r.relationship, r.weight, r.edge_metadata
                    FROM related r
                    JOIN memory_nodes n ON (n.id = r.source_id OR n.id = r.target_id)
                    WHERE n.is_active = TRUE AND n.id != ALL($1::uuid[])
                    LIMIT 50
                """, [uuid.UUID(id) for id in primary_ids], max_depth)
                
                seen_node_ids = set()
                for row in related_rows:
                    node_id = str(row['id'])
                    if node_id not in seen_node_ids and node_id not in primary_ids:
                        node = MemoryNode(
                            id=node_id,
                            content=row['content'],
                            node_type=row['node_type'],
                            tier=MemoryTier(row['tier']),
                            metadata=json.loads(row['metadata']) if row['metadata'] else {},
                            created_at=row['created_at'],
                            source_ivcu_id=str(row['source_ivcu_id']) if row['source_ivcu_id'] else None,
                            project_id=str(row['project_id']) if row['project_id'] else None
                        )
                        related_nodes.append(node)
                        seen_node_ids.add(node_id)
                    
                    # Collect relationship
                    edge = MemoryEdge(
                        id=f"{row['rel_source']}-{row['rel_target']}",
                        source_id=str(row['rel_source']),
                        target_id=str(row['rel_target']),
                        relationship=RelationshipType(row['relationship']),
                        weight=row['weight'],
                        metadata=json.loads(row['edge_metadata']) if row['edge_metadata'] else {}
                    )
                    relationships.append(edge)
        
        query_time = (time.time() - start_time) * 1000
        
        return GraphRAGResult(
            primary_nodes=primary_nodes,
            related_nodes=related_nodes,
            relationships=relationships,
            query_time_ms=query_time,
            vector_score=best_score if best_score > 0 else None
        )
    
    async def impact_analysis(
        self,
        node_id: str,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze the impact of changing a node.
        
        Traverses the graph to find all nodes that depend on the given node.
        
        Args:
            node_id: The node being changed
            max_depth: How deep to traverse
            
        Returns:
            Impact analysis with affected nodes
        """
        import uuid
        
        async with self.pool.acquire() as conn:
            # Find all dependent nodes (things that DEPENDS_ON this node)
            rows = await conn.fetch("""
                WITH RECURSIVE impact AS (
                    SELECT 
                        e.source_id as affected_id,
                        e.target_id as cause_id,
                        e.relationship,
                        1 as depth,
                        ARRAY[e.source_id] as path
                    FROM memory_edges e
                    WHERE e.target_id = $1
                    AND e.relationship = 'depends_on'
                    
                    UNION
                    
                    SELECT 
                        e.source_id,
                        e.target_id,
                        e.relationship,
                        i.depth + 1,
                        i.path || e.source_id
                    FROM memory_edges e
                    JOIN impact i ON e.target_id = i.affected_id
                    WHERE i.depth < $2
                    AND NOT e.source_id = ANY(i.path)  -- Prevent cycles
                )
                SELECT 
                    n.id, n.content, n.node_type, n.tier,
                    i.depth, i.relationship
                FROM impact i
                JOIN memory_nodes n ON n.id = i.affected_id
                WHERE n.is_active = TRUE
                ORDER BY i.depth ASC
            """, uuid.UUID(node_id), max_depth)
            
            affected_nodes = []
            for row in rows:
                affected_nodes.append({
                    "id": str(row['id']),
                    "content": row['content'][:200],
                    "node_type": row['node_type'],
                    "tier": row['tier'],
                    "depth": row['depth'],
                    "relationship": row['relationship']
                })
            
            return {
                "source_node_id": node_id,
                "affected_count": len(affected_nodes),
                "max_depth_reached": max(n["depth"] for n in affected_nodes) if affected_nodes else 0,
                "affected_nodes": affected_nodes,
                "impact_severity": "high" if len(affected_nodes) > 10 else "medium" if len(affected_nodes) > 3 else "low"
            }
    
    async def supersede(self, old_node_id: str, new_node_id: str):
        """Mark a node as superseded by a newer version."""
        import uuid
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Mark old node as superseded
                await conn.execute("""
                    UPDATE memory_nodes 
                    SET superseded_by = $1, is_active = FALSE
                    WHERE id = $2
                """, uuid.UUID(new_node_id), uuid.UUID(old_node_id))
                
                # Add supersedes relationship
                await conn.execute("""
                    INSERT INTO memory_edges (source_id, target_id, relationship)
                    VALUES ($1, $2, 'supersedes')
                    ON CONFLICT DO NOTHING
                """, uuid.UUID(new_node_id), uuid.UUID(old_node_id))


# Singleton instance
_graph_memory: Optional[GraphMemoryStore] = None


async def get_graph_memory(pool: asyncpg.Pool, embedding_service=None) -> GraphMemoryStore:
    """Get or create the global GraphRAG memory store."""
    global _graph_memory
    if _graph_memory is None:
        _graph_memory = GraphMemoryStore(pool, embedding_service)
        await _graph_memory.initialize_schema()
    return _graph_memory
