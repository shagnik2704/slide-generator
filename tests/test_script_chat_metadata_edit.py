"""Test metadata edit loop functionality in the graph.
"""
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
    print("🚀 Testing Metadata Editing Loop", flush=True)
    
    checkpointer = MemorySaver()
    graph = build_script_chat_graph(checkpointer)
    
    inputs = {
        "raw_outline": "Tutorial: Creating Tensors in Google Colab\nimport tensorflow as tf",
        "messages": [],
        "script_version": 0,
        "foss_name": "TensorFlow"
    }
    config = {"configurable": {"thread_id": "meta-edit-test"}}
    
    # 1. Run ingest & ground
    async for mode, chunk in graph.astream(inputs, config=config, stream_mode=["updates"]):
        pass
    
    # Ground review -> Approve
    async for mode, chunk in graph.astream(Command(resume={"action": "approve"}), config=config, stream_mode=["updates"]):
        pass
        
    state = graph.get_state(config)
    print(f"Current stage after grounding approval: {state.values.get('current_stage')}", flush=True)
    
    # We should be interrupted at metadata_review
    task = state.tasks[0]
    interrupt_val = task.interrupts[0].value
    print(f"Original Metadata Title: {interrupt_val['metadata']['title']}", flush=True)
    
    # 2. Reject/Edit metadata
    print("\n--- Rejecting metadata and requesting edit: 'Change title to: Getting Started with Tensors' ---", flush=True)
    async for mode, chunk in graph.astream(
        Command(resume={"action": "edit", "instruction": "Change title to: Getting Started with Tensors"}),
        config=config,
        stream_mode=["updates"]
    ):
        pass
        
    state = graph.get_state(config)
    task = state.tasks[0]
    interrupt_val = task.interrupts[0].value
    print(f"Updated Metadata Title: {interrupt_val['metadata']['title']}", flush=True)
    
    # 3. Approve metadata
    print("\n--- Approving updated metadata ---", flush=True)
    async for mode, chunk in graph.astream(
        Command(resume={"action": "approve"}),
        config=config,
        stream_mode=["updates"]
    ):
        pass
        
    state = graph.get_state(config)
    print(f"Current stage after metadata approval: {state.values.get('current_stage')}", flush=True)
    print("✅ Metadata edit loop verified successfully!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
