"""Step 6 test: Tests the compliance node using the existing compliance_service.
Uses a mock script and an isolated mini-graph: compliance → compliance_review → END.
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
from src.script_chat.nodes.compliance import compliance_node, compliance_review_node

# Build a MINIMAL graph for testing compliance only
def build_compliance_test_graph(checkpointer):
    builder = StateGraph(ScriptChatState)
    builder.add_node("compliance", compliance_node)
    builder.add_node("compliance_review", compliance_review_node)
    
    builder.add_edge(START, "compliance")
    builder.add_edge("compliance", "compliance_review")
    
    def route_after_review(state):
        stage = state.get("current_stage")
        if stage == "edit":
            return END  # In real graph this would go to edit node
        return END
    
    builder.add_conditional_edges("compliance_review", route_after_review)
    return builder.compile(checkpointer=checkpointer)

# A mock script with some deliberate issues for compliance to catch
MOCK_SCRIPT = [
    {"slide_number": 1, "slide_type": "Title Slide",
     "visual_cue": "Title slide with tutorial name",
     "narration": "Welcome to this spoken tutorial on Creating Tensors in Google Colab."},
    {"slide_number": 2, "slide_type": "Learning Objectives",
     "visual_cue": "Display objectives list",
     "narration": "In this tutorial, we will learn to define what a tensor is and also learn how to create scalar tensors using TensorFlow."},
    {"slide_number": 3, "slide_type": "System Requirements",
     "visual_cue": "Display system info",
     "narration": "To record this tutorial I am using a web browser and Google Colab."},
    {"slide_number": 4, "slide_type": "Demonstration",
     "visual_cue": "Show Google Colab interface. Type import tensorflow as tf.",
     "narration": "Let us open Google Colab. First we will import TensorFlow. Type import tensorflow as tf and press Shift Enter to run this cell, which will load the library."},
    {"slide_number": 5, "slide_type": "Demonstration",
     "visual_cue": "Type scalar = tf.constant(5)",
     "narration": "Now we will create a scalar tensor. Type scalar equals tf.constant(5). To see the value type print(scalar.numpy())."},
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
    print("🚀 Step 6: Compliance Check Test (isolated)", flush=True)
    
    checkpointer = MemorySaver()
    graph = build_compliance_test_graph(checkpointer)
    
    inputs = {
        "messages": [],
        "script": MOCK_SCRIPT,
        "metadata": {"title": "Creating Tensors in Google Colab"},
        "script_version": 1,
        "current_stage": "compliance",
    }
    config = {"configurable": {"thread_id": "compliance-test-1"}}
    
    # ---- Run compliance checks ----
    print("\n--- Running compliance checks ---", flush=True)
    async for chunk in graph.astream(inputs, config=config, stream_mode=["custom", "updates"]):
        if chunk[0] == "custom":
            print(f"  🔄 {chunk[1].get('status', '')}", flush=True)
    
    # ---- Check interrupt ----
    state = graph.get_state(config)
    if getattr(state, 'tasks', None) and len(state.tasks) > 0:
        task = state.tasks[0]
        if hasattr(task, 'interrupts') and task.interrupts:
            interrupt_val = task.interrupts[0].value
            print("\n🛑 GRAPH INTERRUPTED FOR COMPLIANCE REVIEW 🛑", flush=True)
            
            summary = interrupt_val.get("summary", {})
            print(f"   Passed: {summary.get('ai_passed', 0)}/{summary.get('total', 0)}", flush=True)
            
            # Print failed checks
            results = interrupt_val.get("results", {})
            checks = results.get("checks", [])
            failed = [c for c in checks if c.get("ai_review") is False]
            if failed:
                print(f"\n   ❌ Failed checks ({len(failed)}):", flush=True)
                for c in failed:
                    print(f"      - {c['criteria']}: {c['ai_notes'][:80]}...", flush=True)
            
            passed = [c for c in checks if c.get("ai_review") is True]
            if passed:
                print(f"\n   ✅ Passed checks ({len(passed)}):", flush=True)
                for c in passed[:5]:  # Show first 5
                    print(f"      - {c['criteria']}", flush=True)
                if len(passed) > 5:
                    print(f"      ... and {len(passed) - 5} more", flush=True)
    
    # ---- User approves ----
    print("\n--- User approves compliance results ---", flush=True)
    async for chunk in graph.astream(
        Command(resume={"action": "approve"}),
        config=config,
        stream_mode=["custom", "updates"]
    ):
        pass
    
    final_state = graph.get_state(config)
    print(f"\n✅ Final stage: {final_state.values.get('current_stage')}", flush=True)
    print("🎉 Compliance test complete!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
