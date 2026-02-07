"""
Graph Memory Service Layer

Handles structured knowledge graph storage and retrieval via Neo4j.
"""
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Try to import Neo4j driver
try:
    from neo4j import GraphDatabase, Driver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    GraphDatabase = None
    Driver = None

from .vector import MemoryConfig


class GraphMemory:
    """
    Graph memory service using Neo4j.
    Stores architectural components and their relationships.
    """
    
    def __init__(self):
        self.driver: Optional[Driver] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Neo4j connection."""
        if not NEO4J_AVAILABLE:
            print("Neo4j driver not available (pip install neo4j)")
            return False

        try:
            self.driver = GraphDatabase.driver(
                MemoryConfig.NEO4J_URI,
                auth=(MemoryConfig.NEO4J_USER, MemoryConfig.NEO4J_PASSWORD)
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            print(f"Connected to Neo4j at {MemoryConfig.NEO4J_URI}")
            
            # Ensure Constraints
            self._create_constraints()
            
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize GraphMemory: {e}")
            return False

    def close(self):
        if self.driver:
            self.driver.close()

    def _create_constraints(self):
        """Create constraints for SDOs and Components."""
        if not self.driver:
            return
            
        with self.driver.session() as session:
            try:
                # SDO ID Uniqueness
                session.run("CREATE CONSTRAINT sdo_id_unique IF NOT EXISTS FOR (s:SDO) REQUIRE s.id IS UNIQUE")
                # Component Name Uniqueness (within project context, maybe?)
                session.run("CREATE CONSTRAINT comp_name_unique IF NOT EXISTS FOR (c:Component) REQUIRE c.name IS UNIQUE")
            except Exception as e:
                print(f"Error creating graph constraints: {e}")

    def add_sdo_node(self, sdo_id: str, intent: str, status: str):
        """Add an SDO node to the graph."""
        if not self.driver:
            return

        with self.driver.session() as session:
            session.run("""
                MERGE (s:SDO {id: $sdo_id})
                SET s.intent = $intent,
                    s.status = $status,
                    s.updated_at = datetime()
            """, sdo_id=sdo_id, intent=intent, status=status)

    def add_component_node(self, name: str, type: str, description: str = ""):
        """Add a software component node."""
        if not self.driver:
            return

        with self.driver.session() as session:
            session.run("""
                MERGE (c:Component {name: $name})
                SET c.type = $type,
                    c.description = $description,
                    c.updated_at = datetime()
            """, name=name, type=type, description=description)

    def add_dependency(self, source_name: str, target_name: str, type: str = "DEPENDS_ON"):
        """Add a dependency edge between components."""
        if not self.driver:
            return

        with self.driver.session() as session:
            session.run("""
                MATCH (a:Component {name: $source})
                MATCH (b:Component {name: $target})
                MERGE (a)-[r:DEPENDS_ON]->(b)
                SET r.type = $type
            """, source=source_name, target=target_name, type=type)

    def link_sdo_to_component(self, sdo_id: str, component_name: str, rel_type: str = "AFFECTS"):
        """Link an SDO to a component it modified."""
        if not self.driver:
            return

        with self.driver.session() as session:
            session.run("""
                MATCH (s:SDO {id: $sdo_id})
                MATCH (c:Component {name: $comp_name})
                MERGE (s)-[r:AFFECTS]->(c)
                SET r.type = $rel_type
            """, sdo_id=sdo_id, comp_name=component_name, rel_type=rel_type)

    def get_related_components(self, sdo_id: str) -> List[Dict[str, Any]]:
        """Get components related to an SDO."""
        if not self.driver:
            return []

        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:SDO {id: $sdo_id})-[r]->(c:Component)
                RETURN c.name as name, c.type as type, type(r) as relationship
            """, sdo_id=sdo_id)
            return [dict(record) for record in result]
            
    def query_subgraph(self, component_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Get the neighborhood of a component."""
        if not self.driver:
            return []
            
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (c:Component {{name: $name}})-[r*1..{depth}]-(n)
                RETURN distinct n.name as name, labels(n) as labels, type(last(r)) as rel
                LIMIT 20
            """, name=component_name)
            return [dict(record) for record in result]
