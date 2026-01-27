
import asyncio
import os
import signal
from typing import Optional, Dict, Any

from sdo_engine import SDOEngine
from sdo import SDO
from eventbus import EventBus
from economics import get_economics_service
import uuid

class SpeculationWorker:
    """
    Background worker that performs speculative code generation
    when the system is idle or when probable intents are predicted.
    """
    
    def __init__(self, sdo_engine: SDOEngine):
        self.engine = sdo_engine
        self.bus = EventBus()
        self.running = False
        
    async def start(self):
        """Start the worker and subscriptions."""
        await self.bus.connect()
        self.running = True
        
        # Subscribe to speculation triggers
        await self.bus.subscribe("speculation.trigger", self.handle_trigger)
        await self.bus.subscribe("user.intent.predicted", self.handle_prediction)
        
        print("Speculation Worker started. Listening for events...")
        
        # Keep alive
        while self.running:
            await asyncio.sleep(1)
            
    async def stop(self):
        """Stop the worker."""
        self.running = False
        await self.bus.close()
        
    async def handle_trigger(self, msg):
        """Handle manual or system trigger for speculation."""
        try:
            data = msg.data.decode()
            # Simple parsing, assuming JSON-like or just prompt text
            # In real implementations, use properly typed messages
            print(f"Received speculation trigger: {data}")
            
            # Create a speculative SDO
            sdo = SDO(
                id=str(uuid.uuid4()),
                raw_intent=f"Speculative: {data}",
                language="python" # Default
            )
            
            # Run adaptive flow with budget check implicitly handled by engine
            # Note: We might want a lower budget for speculation
            # For now, just run it
            print("Starting speculative generation...")
            result = await self.engine.adaptive_generation_flow(sdo, early_stop_threshold=0.85)
            
            if result.status == "verified":
                print(f"Speculation successful! Generated candidate: {result.selected_candidate_id}")
                # Publish success so main system can cache it
                await self.bus.publish("speculation.success", str(result.model_dump_json()).encode())
            else:
                print("Speculation failed or low confidence.")
                
        except Exception as e:
            print(f"Speculation error: {e}")

    async def handle_prediction(self, msg):
        """Handle ML-predicted user intent."""
        # Similar logic, just different source
        await self.handle_trigger(msg)

if __name__ == "__main__":
    # Bootstrap
    from llm import LLMService
    from knowledge import KnowledgeService
    from memory import MemoryService
    
    # Env vars
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # Init Services
    llm = LLMService(openai_key=openai_key)
    # Mocking memory for worker context if needed, or connecting real one
    # For speculation, we might assume minimal memory dependency or full
    # Let's use real if possible, else None
    
    engine = SDOEngine(llm_service=llm, enable_cache=True)
    
    worker = SpeculationWorker(engine)
    
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(worker.stop())
        
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    
    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        pass
