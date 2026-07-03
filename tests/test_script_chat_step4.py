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
    print("🚀 Running Step 4: Script Generation and HITL Interrupt")
    
    raw_outline = """
    Tutorial 2: Creating Tensors in Google Colab
    Example
    Open notebook on a Google Colab
    import tensorflow as tf
    scalar = tf.constant(5)
    print(scalar.numpy())
    """
    
    metadata = {
        "title": "Creating Tensors in Google Colab",
        "learning_objectives": [
            "Define what a tensor is",
            "Create scalar tensors"
        ],
        "prerequisites": "Basic computer literacy",
        "system_requirements": {
            "operating_system": "Any (web-based)",
            "software": ["Web Browser", "Google Colab"]
        }
    }
    
    checkpointer = MemorySaver()
    graph = build_script_chat_graph(checkpointer=checkpointer)
    
    inputs = {
        "raw_outline": raw_outline,
        "metadata": metadata, # Skipping directly to step 4 state
        "messages": [],
        "script_version": 0,
        "foss_name": "TensorFlow"
    }
    
    config = {"configurable": {"thread_id": "test-thread-4"}}
    
    print("\n--- Phase 1: Bypassing Steps 1-3 to hit Generate ---")
    
    # Since the graph starts from ingest, we just auto-approve until we hit script_review
    async def run_to_next_interrupt(resume_data=None):
        cmd = Command(resume=resume_data) if resume_data else inputs
        async for chunk in graph.astream(cmd, config=config, stream_mode=["custom", "updates"]):
            if chunk[0] == "custom":
                print(f"🔄 Progress: {chunk[1]}")
    
    # Start graph (hits ground_review)
    await run_to_next_interrupt()
    # Resume ground_review (hits metadata_review)
    await run_to_next_interrupt({"action": "approve"})
    # Resume metadata_review (hits script_review)
    await run_to_next_interrupt({"action": "approve"})
    
    state = graph.get_state(config)
    print("\n--- Pause State ---")
    if getattr(state, 'tasks', None) and len(state.tasks) > 0:
        task = state.tasks[0]
        if hasattr(task, 'interrupts') and task.interrupts:
            interrupt_val = task.interrupts[0].value
            print("🛑 GRAPH INTERRUPTED FOR SCRIPT REVIEW 🛑")
            print(f"Generated {len(interrupt_val['script'])} slides!")
            
            # Print the first and last slide just to verify
            print("\nFirst Slide:")
            print(json.dumps(interrupt_val['script'][0], indent=2))
            print("\nLast Slide:")
            print(json.dumps(interrupt_val['script'][-1], indent=2))

    print("\n--- Phase 2: Human Resumes ---")
    print("User clicks 'Approve' for script...")
    
    await run_to_next_interrupt({"action": "approve"})

    final_state = graph.get_state(config)
    print(f"\nCurrent Stage: {final_state.values.get('current_stage')}")
    print("Graph execution complete.")

if __name__ == "__main__":
    asyncio.run(main())
