"""
Neo4j Graph Client for AXIOM

Provides graph database operations for:
- Storing relationships between SDOs, IVCUs, and code entities
- Querying dependency graphs
- Impact analysis via graph traversal

Uses the official neo4j Python driver.
"""
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncGraphDatabase = None
    AsyncDriver = None


@dataclass
class GraphNode:
    """Represents a node in the graph."""
    id: str
    label: str
    properties: Dict[str, Any]


@dataclass
class GraphRelationship:
    """Represents a relationship between nodes."""
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any]


class Neo4jClient:
    """
    Async Neo4j client for AXIOM graph operations.
    
    Supports:
    - IVCU/SDO node creation
    - Dependency relationship tracking
    - Impact analysis queries
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "axiom_dev_password")
        self._driver: Optional[AsyncDriver] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Connect to Neo4j."""
        if not NEO4J_AVAILABLE:
            print("WARN: neo4j driver not installed, graph features disabled")
            return False
        
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Verify connectivity
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            
            await self._ensure_schema()
            self._initialized = True
            print(f"Neo4j client connected to {self.uri}")
            return True
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
            return False
    
    async def _ensure_schema(self):
        """Create indexes and constraints."""
        if not self._driver:
            return
        
        async with self._driver.session() as session:
            # Create indexes for fast lookups
            await session.run("""
                CREATE INDEX IF NOT EXISTS FOR (n:SDO) ON (n.id)
            """)
            await session.run("""
                CREATE INDEX IF NOT EXISTS FOR (n:IVCU) ON (n.id)
            """)
            await session.run("""
                CREATE INDEX IF NOT EXISTS FOR (n:Intent) ON (n.id)
            """)
            await session.run("""
                CREATE INDEX IF NOT EXISTS FOR (n:Code) ON (n.id)
            """)
    
    async def create_sdo_node(
        self,
        sdo_id: str,
        intent: str,
        language: str,
        status: str,
        confidence: float,
        project_id: Optional[str] = None
    ) -> bool:
        """Create or update an SDO node."""
        if not self._driver:
            return False
        
        async with self._driver.session() as session:
            await session.run("""
                MERGE (s:SDO {id: $id})
                SET s.intent = $intent,
                    s.language = $language,
                    s.status = $status,
                    s.confidence = $confidence,
                    s.project_id = $project_id,
                    s.updated_at = datetime()
            """, 
                id=sdo_id,
                intent=intent,
                language=language,
                status=status,
                confidence=confidence,
                project_id=project_id
            )
        return True
    
    async def create_ivcu_node(
        self,
        ivcu_id: str,
        sdo_id: str,
        code_hash: str,
        status: str,
        confidence: float
    ) -> bool:
        """Create IVCU node and link to SDO."""
        if not self._driver:
            return False
        
        async with self._driver.session() as session:
            await session.run("""
                MERGE (i:IVCU {id: $ivcu_id})
                SET i.code_hash = $code_hash,
                    i.status = $status,
                    i.confidence = $confidence,
                    i.updated_at = datetime()
                WITH i
                MATCH (s:SDO {id: $sdo_id})
                MERGE (s)-[:PRODUCES]->(i)
            """,
                ivcu_id=ivcu_id,
                sdo_id=sdo_id,
                code_hash=code_hash,
                status=status,
                confidence=confidence
            )
        return True
    
    async def add_dependency(
        self,
        source_id: str,
        target_id: str,
        dependency_type: str = "DEPENDS_ON",
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a dependency relationship between nodes."""
        if not self._driver:
            return False
        
        props = properties or {}
        
        async with self._driver.session() as session:
            # Dynamic relationship type via APOC or string interpolation
            # Using parameterized properties for safety
            await session.run(f"""
                MATCH (source {{id: $source_id}})
                MATCH (target {{id: $target_id}})
                MERGE (source)-[r:{dependency_type}]->(target)
                SET r += $props
            """,
                source_id=source_id,
                target_id=target_id,
                props=props
            )
        return True
    
    async def get_dependencies(
        self,
        node_id: str,
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Get all dependencies of a node up to max_depth."""
        if not self._driver:
            return []
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH path = (n {id: $node_id})-[:DEPENDS_ON*1..$max_depth]->(dep)
                RETURN dep.id as id, 
                       labels(dep)[0] as label,
                       length(path) as depth
                ORDER BY depth
            """,
                node_id=node_id,
                max_depth=max_depth
            )
            
            dependencies = []
            async for record in result:
                dependencies.append({
                    "id": record["id"],
                    "label": record["label"],
                    "depth": record["depth"]
                })
            return dependencies
    
    async def impact_analysis(
        self,
        node_id: str,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze what would be impacted by changing a node.
        
        Returns nodes that depend ON the given node (reverse traversal).
        """
        if not self._driver:
            return {"affected": [], "count": 0}
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH path = (affected)-[:DEPENDS_ON*1..$max_depth]->(n {id: $node_id})
                RETURN affected.id as id,
                       labels(affected)[0] as label,
                       length(path) as depth,
                       affected.intent as intent
                ORDER BY depth
            """,
                node_id=node_id,
                max_depth=max_depth
            )
            
            affected = []
            async for record in result:
                affected.append({
                    "id": record["id"],
                    "label": record["label"],
                    "depth": record["depth"],
                    "intent": record.get("intent", "")[:100] if record.get("intent") else ""
                })
            
            return {
                "source_node": node_id,
                "affected": affected,
                "count": len(affected),
                "severity": "high" if len(affected) > 10 else "medium" if len(affected) > 3 else "low"
            }
    
    async def get_project_graph(
        self,
        project_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get the full graph for a project."""
        if not self._driver:
            return {"nodes": [], "edges": []}
        
        async with self._driver.session() as session:
            # Get nodes
            node_result = await session.run("""
                MATCH (n)
                WHERE n.project_id = $project_id OR n:SDO OR n:IVCU
                RETURN n.id as id, labels(n)[0] as label, properties(n) as props
                LIMIT $limit
            """,
                project_id=project_id,
                limit=limit
            )
            
            nodes = []
            node_ids = set()
            async for record in node_result:
                nodes.append({
                    "id": record["id"],
                    "label": record["label"],
                    "properties": dict(record["props"]) if record["props"] else {}
                })
                node_ids.add(record["id"])
            
            # Get edges between these nodes
            edge_result = await session.run("""
                MATCH (a)-[r]->(b)
                WHERE a.id IN $node_ids AND b.id IN $node_ids
                RETURN a.id as source, b.id as target, type(r) as type
            """,
                node_ids=list(node_ids)
            )
            
            edges = []
            async for record in edge_result:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["type"]
                })
            
            return {"nodes": nodes, "edges": edges}
    
    async def close(self):
        """Close the driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None


# Global singleton
_neo4j_client: Optional[Neo4jClient] = None


async def get_neo4j_client() -> Neo4jClient:
    """Get or create the global Neo4j client."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        await _neo4j_client.initialize()
    return _neo4j_client


async def init_neo4j_client(
    uri: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Neo4jClient:
    """Initialize the global Neo4j client with custom settings."""
    global _neo4j_client
    _neo4j_client = Neo4jClient(uri, username, password)
    await _neo4j_client.initialize()
    return _neo4j_client
