"""
Temporal Worker for AXIOM

Runs workflow activities and executes workflows.
Start with: python worker.py
"""
import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker

from workflows import WORKFLOWS, ACTIVITIES


TASK_QUEUE = "axiom-task-queue"


async def main():
    """Start the Temporal worker."""
    temporal_host = os.getenv("TEMPORAL_URL", "localhost:7233")
    
    print(f"Connecting to Temporal at {temporal_host}...")
    client = await Client.connect(temporal_host)
    
    print(f"Starting worker on task queue: {TASK_QUEUE}")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=WORKFLOWS,
        activities=ACTIVITIES,
    )
    
    print("Worker ready. Waiting for tasks...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
