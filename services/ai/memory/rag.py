"""
GraphRAG Service Layer

Orchestrates Retrieval Augmented Generation using both Vector and Graph memory.
Strategy:
1. Vector Search: Find relevant code chunks/docs based on semantic similarity.
2. Graph Expansion: Find dependencies and related components of the retrieved items.
3. Synthesis: Combine vector context with structural context.
"""
from typing import List, Dict, Any, Optional
from .vector import VectorMemory, RetrievalResult
from .graph import GraphMemory

class GraphRAG:
    """
    Unified Memory Orchestrator (Tier 3 Memory).
    """
    
    def __init__(self, vector: VectorMemory, graph: GraphMemory):
        self.vector = vector
        self.graph = graph
        
    async def retrieve(
        self, 
        query: str, 
        limit: int = 5,
        graph_depth: int = 1
    ) -> Dict[str, Any]:
        """
        Perform a GraphRAG retrieval.
        
        Args:
            query: User intent/query
            limit: Number of vector results
            graph_depth: How far to traverse in the graph
            
        Returns:
            Dict containing 'vector_results' and 'graph_context'
        """
        # 1. Vector Retrieval (Semantic Search)
        vector_results = await self.vector.retrieve_relevant_code(query, limit=limit)
        
        # 2. Extract Entities/Components from Vector Results
        potential_components = set()
        for res in vector_results:
            # Heuristic: file paths or explicit metadata often hint at component names
            if "file_path" in res.metadata:
                # e.g., "auth/service.py" -> "auth"
                path = res.metadata["file_path"]
                if path:
                     component_name = path.split('/')[0]
                     potential_components.add(component_name)
            
            # TODO: We could also run NER on the content, but that's expensive
        
        # 3. Graph Expansion (Structural Context)
        graph_context = []
        for comp in potential_components:
            subgraph = self.graph.query_subgraph(comp, depth=graph_depth)
            if subgraph:
                graph_context.append({
                    "focus": comp,
                    "related": subgraph
                })
        
        return {
            "vector_results": [r.dict() for r in vector_results],
            "graph_context": graph_context,
            "synthesis": self._synthesize_context(vector_results, graph_context)
        }
    
    def _synthesize_context(self, vector_results: List[RetrievalResult], graph_context: List[Dict]) -> str:
        """
        Create a prompt-ready context string.
        """
        context_parts = []
        
        # Add Code Context
        if vector_results:
            context_parts.append("RELEVANT CODE/DOCS:")
            for r in vector_results:
                meta = f"[{r.metadata.get('file_path', 'unknown')}]"
                context_parts.append(f"{meta}\n{r.content[:500]}...") # Truncate for prompt fit
        
        # Add Graph Context
        if graph_context:
            context_parts.append("\nARCHITECTURAL RELATIONSHIPS:")
            for item in graph_context:
                focus = item['focus']
                relations = []
                for rel in item['related']:
                    relations.append(f"{rel.get('name')} ({rel.get('rel')})")
                
                if relations:
                    context_parts.append(f"Component '{focus}' relates to: {', '.join(relations)}")
        
        return "\n".join(context_parts)
