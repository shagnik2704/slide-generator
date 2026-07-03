import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.script_chat.prompts.metadata import METADATA_SYSTEM_PROMPT

def metadata_node(state: ScriptChatState):
    """Extracts structured metadata from the validated outline."""
    writer = get_stream_writer()
    raw_outline = state.get("raw_outline", "")
    
    writer({"status": "Extracting structured metadata...", "progress": 25})
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        writer({"status": "Error: OPENAI_API_KEY not found", "progress": 100})
        return {"current_stage": "error"}
        
    llm = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.2,
        api_key=api_key
    )
    
    try:
        messages = [
            SystemMessage(content=METADATA_SYSTEM_PROMPT),
            HumanMessage(content=f"=== OUTLINE ===\n{raw_outline}")
        ]
        response = llm.invoke(messages)
        text_response = response.content
        if isinstance(text_response, list):
            text_response = "".join([block.get("text", "") for block in text_response if isinstance(block, dict) and block.get("type") == "text"])
        if "```json" in text_response:
            text_response = text_response.split("```json")[1].split("```")[0]
        elif "```" in text_response:
            text_response = text_response.split("```")[1].split("```")[0]
        metadata_dict = json.loads(text_response.strip())
    except Exception as e:
        writer({"status": f"Metadata extraction failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Metadata extraction complete", "progress": 100})
    
    return {
        "metadata": metadata_dict
    }

def metadata_review_node(state: ScriptChatState):
    """Surfaces metadata results for HITL review."""
    metadata_dict = state.get("metadata")
    
    user_decision = interrupt({
        "type": "metadata_review",
        "metadata": metadata_dict,
        "message": "Review the extracted metadata. Please approve or request changes."
    })
    
    if not user_decision or not isinstance(user_decision, dict):
        return {"current_stage": "error"}

    action = user_decision.get("action")
    if action == "approve":
        return {
            "current_stage": "generate",
            "metadata": user_decision.get("edited_metadata", metadata_dict)
        }
    else:
        # If user requests changes to metadata, set current_stage to edit
        return {
            "current_stage": "metadata_edit",
            "edit_instruction": user_decision.get("instruction", "")
        }
