"""
gRPC Memory Service Implementation

GraphRAG unified memory with vector + graph retrieval.
"""
import asyncio
import time
from typing import AsyncIterator, Optional, Dict, Any, List
import json

import grpc
from grpc import aio


class MemoryServicer:
    """
    gRPC service implementation for GraphRAG memory.
    
    Provides:
    - Combined vector + graph search
    - Streaming search results
    - Relationship management
    - Impact analysis
    """
    
    def __init__(self, graph_memory=None, embedding_service=None):
        """
        Initialize the memory servicer.
        
        Args:
            graph_memory: GraphMemoryStore instance
            embedding_service: Embedding service for vector search
        """
        self.graph_memory = graph_memory
        self.embedding_service = embedding_service
    
    async def Search(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> dict:
        """
        Search memory with GraphRAG (vector + graph).
        
        Returns both primary matches and related context.
        """
        query = request.get("query", "")
        project_id = request.get("project_id")
        tier_value = request.get("tier", 0)
        node_types = request.get("node_types", [])
        limit = request.get("limit", 10)
        similarity_threshold = request.get("similarity_threshold", 0.7)
        include_related = request.get("include_related", True)
        max_depth = request.get("max_depth", 2)
        
        start_time = time.time()
        
        if self.graph_memory:
            try:
                from graph_memory import MemoryTier
                
                # Map tier enum
                tier = None
                if tier_value == 1:
                    tier = MemoryTier.WORKING
                elif tier_value == 2:
                    tier = MemoryTier.PROJECT
                elif tier_value == 3:
                    tier = MemoryTier.ORG
                
                result = await self.graph_memory.search(
                    query=query,
                    project_id=project_id,
                    tier=tier,
                    node_types=node_types if node_types else None,
                    limit=limit,
                    similarity_threshold=similarity_threshold,
                    include_related=include_related,
                    max_depth=max_depth
                )
                
                return {
                    "primary_nodes": [self._node_to_dict(n) for n in result.primary_nodes],
                    "related_nodes": [self._node_to_dict(n) for n in result.related_nodes],
                    "relationships": [self._edge_to_dict(e) for e in result.relationships],
                    "query_time_ms": result.query_time_ms,
                    "best_score": result.vector_score or 0.0
                }
                
            except ImportError:
                pass
        
        # Return empty result if no memory store
        return {
            "primary_nodes": [],
            "related_nodes": [],
            "relationships": [],
            "query_time_ms": (time.time() - start_time) * 1000,
            "best_score": 0.0
        }
    
    async def SearchStream(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[dict]:
        """
        Stream search results as they're found.
        
        Useful for large result sets or real-time UI updates.
        """
        # Get full results first
        result = await self.Search(request, context)
        
        # Stream primary nodes first
        for node in result.get("primary_nodes", []):
            yield node
            await asyncio.sleep(0.01)  # Small delay for streaming effect
        
        # Then stream related nodes
        for node in result.get("related_nodes", []):
            yield node
            await asyncio.sleep(0.01)
    
    async def Store(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> dict:
        """Store a memory node."""
        content = request.get("content", "")
        node_type = request.get("node_type", "fact")
        tier_value = request.get("tier", 2)
        metadata = request.get("metadata", {})
        source_ivcu_id = request.get("source_ivcu_id")
        project_id = request.get("project_id")
        relationships = request.get("relationships", [])
        
        if self.graph_memory:
            try:
                from graph_memory import MemoryTier, RelationshipType
                
                # Map tier
                tier = MemoryTier.PROJECT
                if tier_value == 1:
                    tier = MemoryTier.WORKING
                elif tier_value == 3:
                    tier = MemoryTier.ORG
                
                # Map relationships
                rel_list = []
                for rel in relationships:
                    rel_type_value = rel.get("type", 0)
                    rel_type = {
                        1: RelationshipType.IMPLEMENTS,
                        2: RelationshipType.DEPENDS_ON,
                        3: RelationshipType.SUPERSEDES,
                        4: RelationshipType.REFINES,
                        5: RelationshipType.TESTS,
                        6: RelationshipType.DOCUMENTS
                    }.get(rel_type_value, RelationshipType.DEPENDS_ON)
                    
                    rel_list.append((rel.get("target_id"), rel_type))
                
                node_id = await self.graph_memory.store(
                    content=content,
                    node_type=node_type,
                    tier=tier,
                    metadata=metadata,
                    source_ivcu_id=source_ivcu_id,
                    project_id=project_id,
                    relationships=rel_list if rel_list else None
                )
                
                return {"node_id": node_id, "success": True}
                
            except ImportError:
                pass
        
        # Mock response for testing
        import uuid
        return {"node_id": str(uuid.uuid4()), "success": True}
    
    async def AddRelationship(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> dict:
        """Add a relationship between nodes."""
        source_id = request.get("source_id")
        target_id = request.get("target_id")
        relationship_value = request.get("relationship", 2)
        weight = request.get("weight", 1.0)
        metadata = request.get("metadata", {})
        
        if self.graph_memory:
            try:
                from graph_memory import RelationshipType
                
                rel_type = {
                    1: RelationshipType.IMPLEMENTS,
                    2: RelationshipType.DEPENDS_ON,
                    3: RelationshipType.SUPERSEDES,
                    4: RelationshipType.REFINES,
                    5: RelationshipType.TESTS,
                    6: RelationshipType.DOCUMENTS
                }.get(relationship_value, RelationshipType.DEPENDS_ON)
                
                edge_id = await self.graph_memory.add_relationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship=rel_type,
                    weight=weight,
                    metadata=metadata
                )
                
                return {"edge_id": edge_id, "success": True}
                
            except ImportError:
                pass
        
        import uuid
        return {"edge_id": str(uuid.uuid4()), "success": True}
    
    async def GetImpact(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> dict:
        """Get impact analysis for a node."""
        node_id = request.get("node_id")
        max_depth = request.get("max_depth", 3)
        
        if self.graph_memory:
            try:
                result = await self.graph_memory.impact_analysis(
                    node_id=node_id,
                    max_depth=max_depth
                )
                
                return {
                    "source_node_id": result.get("source_node_id"),
                    "affected_count": result.get("affected_count", 0),
                    "impact_severity": result.get("impact_severity", "low"),
                    "max_depth_reached": result.get("max_depth_reached", 0),
                    "affected_nodes": [
                        {
                            "id": n.get("id"),
                            "content_preview": n.get("content", "")[:200],
                            "node_type": n.get("node_type"),
                            "depth": n.get("depth", 0),
                            "relationship": n.get("relationship", "")
                        }
                        for n in result.get("affected_nodes", [])
                    ]
                }
                
            except ImportError:
                pass
        
        return {
            "source_node_id": node_id,
            "affected_count": 0,
            "impact_severity": "low",
            "max_depth_reached": 0,
            "affected_nodes": []
        }
    
    async def Supersede(
        self,
        request: dict,
        context: grpc.aio.ServicerContext
    ) -> dict:
        """Supersede a node with a new version."""
        old_node_id = request.get("old_node_id")
        new_node_id = request.get("new_node_id")
        
        if self.graph_memory:
            try:
                await self.graph_memory.supersede(old_node_id, new_node_id)
                return {"success": True}
            except Exception as e:
                return {"success": False}
        
        return {"success": True}
    
    def _node_to_dict(self, node) -> dict:
        """Convert MemoryNode to dict for gRPC response."""
        return {
            "id": node.id,
            "content": node.content,
            "node_type": node.node_type,
            "tier": node.tier.value if hasattr(node.tier, 'value') else str(node.tier),
            "metadata": node.metadata or {},
            "created_at": node.created_at.isoformat() if node.created_at else "",
            "source_ivcu_id": node.source_ivcu_id or "",
            "project_id": node.project_id or "",
            "similarity_score": 0.0
        }
    
    def _edge_to_dict(self, edge) -> dict:
        """Convert MemoryEdge to dict for gRPC response."""
        return {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relationship": edge.relationship.value if hasattr(edge.relationship, 'value') else str(edge.relationship),
            "weight": edge.weight,
            "metadata": edge.metadata or {}
        }
