from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.script_chat.llm import invoke_structured
from src.script_chat.prompts.metadata import METADATA_SYSTEM_PROMPT
from src.script_chat.schemas import ScriptMetadata, dump_model, parse_metadata

def metadata_node(state: ScriptChatState):
    """Extracts structured metadata from the validated outline."""
    writer = get_stream_writer()
    raw_outline = state.get("raw_outline", "")
    
    writer({"status": "Extracting structured metadata...", "progress": 25})
    
    try:
        metadata = invoke_structured(
            [
                SystemMessage(content=METADATA_SYSTEM_PROMPT),
                HumanMessage(content=f"=== OUTLINE ===\n{raw_outline}"),
            ],
            ScriptMetadata,
            model="gpt-5.4-mini",
            temperature=0.2,
        )
    except Exception as e:
        writer({"status": f"Metadata extraction failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Metadata extraction complete", "progress": 100})
    
    return {
        "metadata": dump_model(metadata)
    }

def metadata_review_node(state: ScriptChatState):
    """Surfaces metadata results for HITL review."""
    metadata_dict = state.get("metadata")
    
    user_decision = interrupt({
        "type": "metadata_review",
        "metadata": metadata_dict,
        "foss_name": state.get("foss_name"),
        "message": "Review the extracted metadata. Please approve or request changes."
    })
    
    if not user_decision or not isinstance(user_decision, dict):
        return {"current_stage": "error"}

    action = user_decision.get("action")
    if action == "approve":
        edited_metadata = user_decision.get("edited_metadata", metadata_dict)
        try:
            metadata = parse_metadata(edited_metadata)
        except Exception:
            return {"current_stage": "error"}
        return {
            "current_stage": "generate",
            "metadata": dump_model(metadata)
        }
    if action == "edit":
        return {
            "current_stage": "metadata_edit",
            "edit_instruction": user_decision.get("instruction", "")
        }

    return {"current_stage": "error"}
