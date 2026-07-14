"""Step 5 test: Tests ONLY the edit loop (skips grounding/metadata LLM calls).
Directly injects a pre-generated script and tests edit → review → edit → approve.
"""
import sys
from pathlib import Path
import asyncio

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import json
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from src.script_chat.state import ScriptChatState
from src.script_chat.nodes.generate import script_review_node
from src.script_chat.nodes.edit import edit_node

# Build a MINIMAL graph that only has: script_review <-> edit
def build_edit_test_graph(checkpointer):
    builder = StateGraph(ScriptChatState)
    builder.add_node("script_review", script_review_node)
    builder.add_node("edit", edit_node)
    
    builder.add_edge(START, "script_review")
    builder.add_edge("edit", "script_review")
    
    def route_after_review(state):
        stage = state.get("current_stage")
        if stage == "edit":
            return "edit"
        return END
    
    builder.add_conditional_edges("script_review", route_after_review)
    return builder.compile(checkpointer=checkpointer)

# A small pre-generated script to test against
MOCK_SCRIPT = [
    {"slide_number": 1, "slide_type": "Title Slide",
     "visual_cue": "Title slide with tutorial name",
     "narration": "Welcome to this spoken tutorial on Creating Tensors in Google Colab."},
    {"slide_number": 2, "slide_type": "Learning Objectives",
     "visual_cue": "Display objectives list",
     "narration": "In this tutorial, we will learn to define a tensor and create scalar tensors."},
    {"slide_number": 3, "slide_type": "System Requirements",
     "visual_cue": "Display system info",
     "narration": "To record this tutorial I am using a web browser and Google Colab."},
    {"slide_number": 4, "slide_type": "Demonstration",
     "visual_cue": "Show Google Colab interface. Type import tensorflow as tf in a code cell.",
     "narration": "Let us open Google Colab. First we will import TensorFlow. Type import tensorflow as tf. Now press Shift Enter to run this cell."},
    {"slide_number": 5, "slide_type": "Demonstration",
     "visual_cue": "Type scalar = tf.constant(5) and print(scalar.numpy()) in the next cell.",
     "narration": "Now we will create a scalar tensor. Type scalar equals tf dot constant 5. To see the value, type print scalar dot numpy."},
    {"slide_number": 6, "slide_type": "Summary",
     "visual_cue": "Display summary slide",
     "narration": "In this tutorial we have learnt to define a tensor and create scalar tensors."},
    {"slide_number": 7, "slide_type": "Assignment",
     "visual_cue": "Display assignment",
     "narration": "As an assignment, create a vector tensor with your favourite numbers."},
    {"slide_number": 8, "slide_type": "Acknowledgement",
     "visual_cue": "Display acknowledgement",
     "narration": "This Spoken Tutorial is brought to you by EduPyramids. Thanks for joining."}
]

async def main():
    print("🚀 Step 5: Edit Loop Test (isolated)", flush=True)
    
    checkpointer = MemorySaver()
    graph = build_edit_test_graph(checkpointer)
    
    inputs = {
        "messages": [],
        "script": MOCK_SCRIPT,
        "script_version": 1,
        "current_stage": "review",
    }
    config = {"configurable": {"thread_id": "edit-test-1"}}
    
    # ---- Start: hits script_review interrupt ----
    print("\n--- Starting graph (hits script_review interrupt) ---", flush=True)
    async for chunk in graph.astream(inputs, config=config, stream_mode=["custom", "updates"]):
        pass
    
    state = graph.get_state(config)
    task = state.tasks[0]
    interrupt_val = task.interrupts[0].value
    print(f"✅ Interrupted with {len(interrupt_val['script'])} slides (version {state.values['script_version']})", flush=True)
    
    # ---- Edit 1: Split slide 4 ----
    print("\n--- Edit 1: 'Split slide 4 into two slides' ---", flush=True)
    async for chunk in graph.astream(
        Command(resume={"action": "edit", "instruction": "Split slide 4 into two slides. First slide should cover only importing TensorFlow. Second slide should cover running the cell."}),
        config=config,
        stream_mode=["custom", "updates"]
    ):
        if chunk[0] == "custom":
            print(f"  🔄 {chunk[1].get('status', '')}", flush=True)
    
    state = graph.get_state(config)
    task = state.tasks[0]
    interrupt_val = task.interrupts[0].value
    new_count = len(interrupt_val['script'])
    print(f"✅ After edit 1: {new_count} slides (version {state.values['script_version']})", flush=True)
    print(f"   Expected: 9 slides (split 1 → 2)", flush=True)
    
    # ---- Edit 2: Rewrite narration on slide 1 ----
    print("\n--- Edit 2: 'Make slide 1 more engaging' ---", flush=True)
    async for chunk in graph.astream(
        Command(resume={"action": "edit", "instruction": "Make the Title Slide narration more engaging. Add a hook about why tensors are the building blocks of deep learning."}),
        config=config,
        stream_mode=["custom", "updates"]
    ):
        if chunk[0] == "custom":
            print(f"  🔄 {chunk[1].get('status', '')}", flush=True)

    state = graph.get_state(config)
    task = state.tasks[0]
    interrupt_val = task.interrupts[0].value
    slide_1 = interrupt_val['script'][0]
    print(f"✅ After edit 2 (version {state.values['script_version']}):", flush=True)
    print(f"   Slide 1 narration: '{slide_1['narration']}'", flush=True)
    
    # ---- Approve ----
    print("\n--- Approve: User approves the script ---", flush=True)
    async for chunk in graph.astream(
        Command(resume={"action": "approve"}),
        config=config,
        stream_mode=["custom", "updates"]
    ):
        pass

    final_state = graph.get_state(config)
    print(f"\n✅ Final stage: {final_state.values.get('current_stage')}", flush=True)
    print(f"✅ Final version: {final_state.values.get('script_version')}", flush=True)
    print("🎉 Edit loop test complete!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
