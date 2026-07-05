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
    Tutorial 3: Creating Tensors with PyTorch
    
    Learning Objectives:
    1. Understand how to import PyTorch.
    2. Create tensors on the CPU.
    3. Create tensors on CUDA/GPU.
    
    Example:
    import torch
    
    x = torch.empty(5, 3)
    print(x)
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
