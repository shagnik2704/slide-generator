import sys
from pathlib import Path
import asyncio

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Ensure dotenv is loaded so GOOGLE_API_KEY is available
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.script_chat.graph import build_script_chat_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

async def main():
    print("🚀 Running Step 2: Grounding and HITL Interrupt")
    
    # A slightly outdated snippet to see if grounding catches it
    # We use tf.Session() which is TF1.x, TF2 uses tf.function or eager execution
    raw_outline = """
    Tutorial 2: Creating Tensors in Google colab

    Learning Objectives
    1. Understand tensors.

    Example
    Open note book on a Google colab
    import tensorflow as tf
    sess = tf.Session()
    scalar = tf.constant(5)
    print(sess.run(scalar))
    """
    
    checkpointer = MemorySaver()
    graph = build_script_chat_graph(checkpointer=checkpointer)
    
    inputs = {
        "raw_outline": raw_outline,
        "messages": [],
        "script_version": 0
    }
    
    config = {"configurable": {"thread_id": "test-thread-2"}}
    
    print("\n--- Phase 1: Ingest & Ground ---")
    async for chunk in graph.astream(inputs, config=config, stream_mode=["custom", "updates"]):
        if chunk[0] == "custom":
            print(f"🔄 Progress: {chunk[1]}")
        elif chunk[0] == "updates":
            print(f"📦 State Update from {list(chunk[1].keys())[0]}")
            
    # Check if we are paused
    state = graph.get_state(config)
    print("\n--- Pause State ---")
    if getattr(state, 'tasks', None) and len(state.tasks) > 0:
        task = state.tasks[0]
        if hasattr(task, 'interrupts') and task.interrupts:
            interrupt_val = task.interrupts[0].value
            print("🛑 GRAPH INTERRUPTED FOR HUMAN REVIEW 🛑")
            print("Payload presented to UI:")
            import json
            print(json.dumps(interrupt_val, indent=2))
        else:
            print("No interrupts found.")
    else:
        print("Graph finished without interrupt.")
        return

    # Simulate human approval
    print("\n--- Phase 2: Human Resumes ---")
    print("User clicks 'Approve' in UI...")
    
    decision = {
        "action": "approve"
    }
    
    async for chunk in graph.astream(Command(resume=decision), config=config, stream_mode=["custom", "updates"]):
        if chunk[0] == "custom":
            print(f"🔄 Progress: {chunk[1]}")
        elif chunk[0] == "updates":
            print(f"📦 State Update from {list(chunk[1].keys())[0]}")

    print("\n--- Final State ---")
    final_state = graph.get_state(config)
    print(f"Current Stage: {final_state.values.get('current_stage')}")
    print(f"Final Content snippets snippet:\n{final_state.values.get('raw_outline')[:150]}...")

if __name__ == "__main__":
    asyncio.run(main())
