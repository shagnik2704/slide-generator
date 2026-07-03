from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
import re

def ingest_node(state: ScriptChatState):
    """Parses the raw outline, extracts initial info."""
    writer = get_stream_writer()
    
    raw_outline = state.get("raw_outline", "")
    if not raw_outline:
        writer({"status": "Error: No outline provided", "progress": 100})
        return {"current_stage": "error"}
        
    writer({"status": "Parsing your outline...", "progress": 50})
    
    # Simple extraction for now (we'll improve this with LLM if needed later)
    # Let's try to extract FOSS name if mentioned
    foss_name = None
    first_lines = raw_outline.split('\n')[:5]
    for line in first_lines:
        if "google colab" in line.lower() or "tensorflow" in line.lower():
            foss_name = "TensorFlow"
            break
            
    writer({"status": "Parsing complete", "progress": 100})
    
    return {
        "current_stage": "grounding",
        "foss_name": foss_name
    }
