from .vector import VectorMemory, MemoryConfig

class MemoryService:
    """
    Facade for Memory Systems (Vector, Graph, etc.)
    Currently wraps VectorMemory for easy instantiation in main.py
    """
    def __init__(self, embed_fn):
        config = MemoryConfig()
        self.vector = VectorMemory(embed_fn=embed_fn)

    async def initialize(self):
        return await self.vector.initialize()
    
    async def retrieve_context(self, query: str, limit: int = 5):
        return await self.vector.retrieve_relevant_code(query, limit)
    
    async def store_file_content(self, file_path: str, content: str):
        # Naive chunky storage
        await self.vector.store_code_chunk(file_path, content, {})

    async def health_check(self):
        return await self.vector.health_check()
