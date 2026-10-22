import logging
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.script_chat.llm import invoke_structured
from src.script_chat.prompts.metadata import METADATA_SYSTEM_PROMPT
from src.script_chat.schemas import ScriptMetadata, dump_model, parse_metadata

logger = logging.getLogger(__name__)

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
        err_msg = f"Metadata extraction failed: {str(e)}"
        logger.error(err_msg, exc_info=True)
        writer({"status": err_msg, "progress": 100})
        return {"current_stage": "error", "error_message": err_msg}
    
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
        err_msg = "Invalid metadata review decision format"
        logger.error(err_msg)
        return {"current_stage": "error", "error_message": err_msg}

    action = user_decision.get("action")
    if action == "approve":
        edited_metadata = user_decision.get("edited_metadata", metadata_dict)
        try:
            metadata = parse_metadata(edited_metadata)
        except Exception as e:
            err_msg = f"Approved metadata validation failed: {str(e)}"
            logger.error(err_msg, exc_info=True)
            return {"current_stage": "error", "error_message": err_msg}
        return {
            "current_stage": "generate",
            "metadata": dump_model(metadata)
        }
    if action == "edit":
        return {
            "current_stage": "metadata_edit",
            "edit_instruction": user_decision.get("instruction", "")
        }

    err_msg = f"Unsupported metadata review action: {action}"
    logger.error(err_msg)
    return {"current_stage": "error", "error_message": err_msg}

