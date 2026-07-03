import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from src.script_chat.prompts.metadata_edit import METADATA_EDITING_SYSTEM_PROMPT

def metadata_edit_node(state: ScriptChatState):
    """Applies user's edit instruction to the metadata."""
    writer = get_stream_writer()
    metadata = state.get("metadata", {})
    edit_instruction = state.get("edit_instruction", "")
    
    if not edit_instruction:
        writer({"status": "No edit instruction provided", "progress": 100})
        return {}
    
    writer({"status": f"Applying metadata edit: '{edit_instruction[:60]}...'", "progress": 25})
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        writer({"status": "Error: OPENAI_API_KEY not found", "progress": 100})
        return {"current_stage": "error"}
        
    llm = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.3,
        api_key=api_key
    ).bind_tools([{"type": "web_search"}])
    
    prompt = f"""
=== CURRENT METADATA ===
{json.dumps(metadata, indent=2)}

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
        response = llm.invoke(messages)
        text_response = response.content
        if isinstance(text_response, list):
            text_response = "".join([block.get("text", "") for block in text_response if isinstance(block, dict) and block.get("type") == "text"])
        if "```json" in text_response:
            text_response = text_response.split("```json")[1].split("```")[0]
        elif "```" in text_response:
            text_response = text_response.split("```")[1].split("```")[0]
            
        updated_metadata = json.loads(text_response.strip())
    except Exception as e:
        writer({"status": f"Metadata edit failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Metadata edit applied successfully", "progress": 100})
    
    return {
        "metadata": updated_metadata,
        "edit_instruction": None  # Clear after use
    }
