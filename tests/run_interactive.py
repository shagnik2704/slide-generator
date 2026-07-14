import sys
from pathlib import Path
import asyncio
import json

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.script_chat.graph import build_script_chat_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

async def main():
    print("==============================================")
    print("🤖 Agentic Script Chat - Interactive Terminal")
    print("==============================================\n")
    
    raw_outline = input("Paste your tutorial outline (or press Enter to use a default TensorFlow example):\n> ")
    if not raw_outline.strip():
        raw_outline = """
        Tutorial: Creating Tensors
        Open google colab
        import tensorflow as tf
        scalar = tf.constant(5)
        print(scalar)
        """
        print("Using default outline...\n")

    checkpointer = MemorySaver()
    graph = build_script_chat_graph(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": "interactive-session-1"}}
    inputs = {"raw_outline": raw_outline, "messages": [], "script_version": 0}
    
    command = inputs
    
    while True:
        try:
            async for chunk in graph.astream(command, config=config, stream_mode=["custom", "updates"]):
                if chunk[0] == "custom":
                    print(f"  [Agent]: {chunk[1].get('status')}")
            
            state = graph.get_state(config)
            
            # Check if we are paused at an interrupt
            if getattr(state, 'tasks', None) and len(state.tasks) > 0:
                task = state.tasks[0]
                if hasattr(task, 'interrupts') and task.interrupts:
                    interrupt_val = task.interrupts[0].value
                    interrupt_type = interrupt_val.get("type")
                    
                    print(f"\n--- 🛑 PAUSED FOR REVIEW: {interrupt_type.upper()} ---")
                    
                    if interrupt_type == "validation_review":
                        print("Grounding Report:")
                        print(json.dumps(interrupt_val.get("report"), indent=2))
                        print("\nDo you approve? (y/n): ", end="")
                        decision = input().strip().lower()
                        if decision == 'y':
                            command = Command(resume={"action": "approve"})
                        else:
                            print("Enter your edited content manually:")
                            edited = input("> ")
                            command = Command(resume={"action": "edit", "edited_content": edited})
                            
                    elif interrupt_type == "metadata_review":
                        print("Metadata Extracted:")
                        print(json.dumps(interrupt_val.get("metadata"), indent=2))
                        print("\nDo you approve? (y/n): ", end="")
                        decision = input().strip().lower()
                        if decision == 'y':
                            command = Command(resume={"action": "approve"})
                        else:
                            print("This terminal doesn't support manual dict editing well, auto-approving for now.")
                            command = Command(resume={"action": "approve"})
                            
                    elif interrupt_type == "script_review":
                        script = interrupt_val.get("script")
                        version = state.values.get("script_version", 1)
                        print(f"Script Generated! (Version {version}, {len(script)} slides)")
                        for s in script:
                            print(f"  Slide {s['slide_number']}: [{s['slide_type']}]")
                            print(f"    Visual: {s['visual_cue']}")
                            print(f"    Audio:  {s['narration']}\n")
                            
                        print("What would you like to do?")
                        print("1. Approve")
                        print("2. Ask Agent to Edit (e.g. 'Split slide 3', 'Make audio shorter')")
                        choice = input("> ").strip()
                        if choice == '1':
                            command = Command(resume={"action": "approve"})
                        else:
                            instruction = input("Enter your instruction for the agent:\n> ")
                            command = Command(resume={"action": "edit", "instruction": instruction})
                            
            else:
                print("\n✅ Workflow complete!")
                break
                
        except Exception as e:
            print(f"\n❌ Error during execution: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())
