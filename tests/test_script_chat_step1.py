import sys
from pathlib import Path
import asyncio

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.script_chat.graph import build_script_chat_graph
from langgraph.checkpoint.memory import MemorySaver

async def main():
    print("🚀 Running Step 1: Ingestion")
    
    raw_outline = """
    Tutorial 2: Creating Tensors in Google colab

    Learning Objectives
    After completing this tutorial, the learner will be able to:
    1. Understand what a tensor is.
    2. Create scalar tensors.
    3. Create vectors.
    4. Create matrices.

    Example
    Open note book on a Google colab
    Let us import tensorflow first
    import tensorflow as tf

    Now we will create scalar tensors
    scalar = tf.constant(5)
    """
    
    # Build graph with in-memory checkpointer
    checkpointer = MemorySaver()
    graph = build_script_chat_graph(checkpointer=checkpointer)
    
    # Setup initial state
    inputs = {
        "raw_outline": raw_outline,
        "messages": [],
        "script_version": 0
    }
    
    config = {"configurable": {"thread_id": "test-thread-1"}}
    
    print("\n--- Streaming Output ---")
    async for chunk in graph.astream(inputs, config=config, stream_mode=["custom", "updates"]):
        if chunk[0] == "custom":
            print(f"🔄 Progress: {chunk[1]}")
        elif chunk[0] == "updates":
            print(f"📦 State Update: {chunk[1]}")
            
    print("\n--- Final State ---")
    final_state = graph.get_state(config)
    print(f"FOSS Name extracted: {final_state.values.get('foss_name')}")
    print(f"Current Stage: {final_state.values.get('current_stage')}")

if __name__ == "__main__":
    asyncio.run(main())
