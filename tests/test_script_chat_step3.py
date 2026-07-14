import sys
from pathlib import Path
import asyncio

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.script_chat.graph import build_script_chat_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
import json

async def main():
    print("🚀 Running Step 3: Metadata Extraction and HITL Interrupt")
    
    # Simulating the validated content from Step 2
    raw_outline = """
    Tutorial 2: Creating Tensors in Google Colab

    Learning Objectives
    1. Define what a tensor is.
    2. Create scalar tensors.
    3. Create vectors.
    4. Create matrices.

    Example
    Open notebook on a Google Colab
    import tensorflow as tf
    
    scalar = tf.constant(5)
    print(scalar.numpy())
    """
    
    checkpointer = MemorySaver()
    graph = build_script_chat_graph(checkpointer=checkpointer)
    
    inputs = {
        "raw_outline": raw_outline,
        "messages": [],
        "script_version": 0,
        "foss_name": "TensorFlow"
    }
    
    config = {"configurable": {"thread_id": "test-thread-3"}}
    
    print("\n--- Phase 1: Ingest, Ground, Review ---")
    async for chunk in graph.astream(inputs, config=config, stream_mode=["custom", "updates"]):
        pass # Silence the output for step 1 & 2
        
    print("User approves grounding...")
    decision = {"action": "approve"}
    
    print("\n--- Phase 2: Metadata Extraction ---")
    async for chunk in graph.astream(Command(resume=decision), config=config, stream_mode=["custom", "updates"]):
        if chunk[0] == "custom":
            print(f"🔄 Progress: {chunk[1]}")
        elif chunk[0] == "updates":
            print(f"📦 State Update from {list(chunk[1].keys())[0]}")
            
    state = graph.get_state(config)
    print("\n--- Pause State ---")
    if getattr(state, 'tasks', None) and len(state.tasks) > 0:
        task = state.tasks[0]
        if hasattr(task, 'interrupts') and task.interrupts:
            interrupt_val = task.interrupts[0].value
            print("🛑 GRAPH INTERRUPTED FOR METADATA REVIEW 🛑")
            print("Payload presented to UI:")
            print(json.dumps(interrupt_val, indent=2))

    print("\n--- Phase 3: Human Resumes ---")
    print("User clicks 'Approve' for metadata...")
    decision = {"action": "approve"}
    
    async for chunk in graph.astream(Command(resume=decision), config=config, stream_mode=["custom", "updates"]):
        if chunk[0] == "custom":
            print(f"🔄 Progress: {chunk[1]}")
        elif chunk[0] == "updates":
            print(f"📦 State Update from {list(chunk[1].keys())[0]}")

    final_state = graph.get_state(config)
    print(f"\nCurrent Stage: {final_state.values.get('current_stage')}")
    print(f"Final Metadata Title: {final_state.values.get('metadata', {}).get('title')}")

if __name__ == "__main__":
    asyncio.run(main())
