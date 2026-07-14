import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from src.script_chat.llm import invoke_structured
from src.script_chat.prompts.metadata_edit import METADATA_EDITING_SYSTEM_PROMPT
from src.script_chat.schemas import ScriptMetadata, dump_model, parse_metadata

def metadata_edit_node(state: ScriptChatState):
    """Applies user's edit instruction to the metadata."""
    writer = get_stream_writer()
    metadata = state.get("metadata", {})
    edit_instruction = state.get("edit_instruction", "")
    
    if not edit_instruction:
        writer({"status": "No edit instruction provided", "progress": 100})
        return {}
    
    writer({"status": f"Applying metadata edit: '{edit_instruction[:60]}...'", "progress": 25})
    
    try:
        current_metadata = parse_metadata(metadata)
    except Exception as e:
        writer({"status": f"Invalid metadata state: {str(e)}", "progress": 100})
        return {"current_stage": "error"}

    prompt = f"""
=== CURRENT METADATA ===
{json.dumps(dump_model(current_metadata), indent=2)}

=== EDIT INSTRUCTION ===
{edit_instruction}

Apply this edit and return the full updated JSON metadata object.
"""
    
    writer({"status": "LLM is updating the metadata...", "progress": 50})
    
    messages = [
        SystemMessage(content=METADATA_EDITING_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    try:
        updated_metadata = invoke_structured(
            messages,
            ScriptMetadata,
            model="gpt-5.4-mini",
            temperature=0.3,
        )
    except Exception as e:
        writer({"status": f"Metadata edit failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Metadata edit applied successfully", "progress": 100})
    
    return {
        "metadata": dump_model(updated_metadata),
        "edit_instruction": None
    }
