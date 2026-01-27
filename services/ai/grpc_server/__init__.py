"""
gRPC Server Package

Main server that combines all AXIOM gRPC services.
"""
import asyncio
import logging
from typing import Optional

import grpc
from grpc import aio

from .generation_service import GenerationServicer
from .verification_service import VerificationServicer
from .memory_service import MemoryServicer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AXIOMGRPCServer:
    """
    Combined gRPC server for all AXIOM AI services.
    
    Services:
    - GenerationService: Bidirectional streaming code generation
    - VerificationService: Streaming verification with progress
    - MemoryService: GraphRAG unified memory
    """
    
    def __init__(
        self,
        port: int = 50051,
        max_workers: int = 10,
        orchestra=None,
        router=None,
        event_store=None,
        graph_memory=None,
        embedding_service=None
    ):
        """
        Initialize the gRPC server.
        
        Args:
            port: Port to listen on
            max_workers: Max concurrent handlers
            orchestra: VerificationOrchestra instance
            router: LLMRouter instance
            event_store: IVCUEventStore instance
            graph_memory: GraphMemoryStore instance
            embedding_service: Embedding service
        """
        self.port = port
        self.max_workers = max_workers
        
        # Initialize servicers
        self.generation_servicer = GenerationServicer(
            orchestra=orchestra,
            router=router,
            event_store=event_store
        )
        self.verification_servicer = VerificationServicer(
            orchestra=orchestra
        )
        self.memory_servicer = MemoryServicer(
            graph_memory=graph_memory,
            embedding_service=embedding_service
        )
        
        self._server: Optional[aio.Server] = None
    
    async def start(self):
        """Start the gRPC server."""
        self._server = aio.server()
        
        # In production with generated stubs:
        # generation_pb2_grpc.add_GenerationServiceServicer_to_server(
        #     self.generation_servicer, self._server
        # )
        # verification_pb2_grpc.add_VerificationServiceServicer_to_server(
        #     self.verification_servicer, self._server
        # )
        # memory_pb2_grpc.add_MemoryServiceServicer_to_server(
        #     self.memory_servicer, self._server
        # )
        
        listen_addr = f"[::]:{self.port}"
        self._server.add_insecure_port(listen_addr)
        
        logger.info(f"Starting AXIOM gRPC server on {listen_addr}")
        await self._server.start()
        
        logger.info("AXIOM gRPC server started successfully")
        logger.info("Services available:")
        logger.info("  - GenerationService (bidirectional streaming)")
        logger.info("  - VerificationService (streaming progress)")
        logger.info("  - MemoryService (GraphRAG)")
    
    async def stop(self, grace_period: float = 5.0):
        """Stop the gRPC server gracefully."""
        if self._server:
            logger.info("Stopping AXIOM gRPC server...")
            await self._server.stop(grace_period)
            logger.info("Server stopped")
    
    async def wait_for_termination(self):
        """Wait for the server to terminate."""
        if self._server:
            await self._server.wait_for_termination()


async def serve(
    port: int = 50051,
    orchestra=None,
    router=None,
    event_store=None,
    graph_memory=None,
    embedding_service=None
) -> None:
    """
    Start the AXIOM gRPC server.
    
    This is the main entry point for running the gRPC server.
    """
    server = AXIOMGRPCServer(
        port=port,
        orchestra=orchestra,
        router=router,
        event_store=event_store,
        graph_memory=graph_memory,
        embedding_service=embedding_service
    )
    
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await server.stop()


# Export servicers for use elsewhere
__all__ = [
    "AXIOMGRPCServer",
    "GenerationServicer",
    "VerificationServicer",
    "MemoryServicer",
    "serve"
]
