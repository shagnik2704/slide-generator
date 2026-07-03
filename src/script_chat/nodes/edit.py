import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from src.script_chat.prompts.editing import EDITING_SYSTEM_PROMPT

def edit_node(state: ScriptChatState):
    """Applies user's edit instruction to the current script."""
    writer = get_stream_writer()
    current_script = state.get("script", [])
    edit_instruction = state.get("edit_instruction", "")
    
    if not edit_instruction:
        writer({"status": "No edit instruction provided", "progress": 100})
        return {}
    
    writer({"status": f"Applying edit: '{edit_instruction[:60]}...'", "progress": 25})
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        writer({"status": "Error: OPENAI_API_KEY not found", "progress": 100})
        return {"current_stage": "error"}
        
    llm = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.3,
        api_key=api_key
    ).bind_tools([{"type": "web_search"}])
    
    # Build conversation history context (last 10 messages for context window efficiency)
    conversation_history = ""
    raw_messages = state.get("messages", [])
    recent_messages = raw_messages[-10:] if len(raw_messages) > 10 else raw_messages
    if recent_messages:
        history_lines = []
        for msg in recent_messages:
            role = msg.get("role", "unknown") if isinstance(msg, dict) else getattr(msg, "type", "unknown")
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if content:
                history_lines.append(f"{role.upper()}: {content[:200]}")
        if history_lines:
            conversation_history = "\n".join(history_lines)

    prompt = f"""
=== RECENT CONVERSATION HISTORY ===
{conversation_history or "(No prior conversation)"}

=== CURRENT SCRIPT ===
{json.dumps(current_script, indent=2)}

=== EDIT INSTRUCTION ===
{edit_instruction}

Apply this edit and return the full updated JSON object.
"""
    
    writer({"status": "LLM is editing the script...", "progress": 50})
    
    messages = [
        SystemMessage(content=EDITING_SYSTEM_PROMPT),
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
            
        parsed_json = json.loads(text_response.strip())
        updated_script = parsed_json.get("script", [])
        agent_message = parsed_json.get("message", "I have applied your edits.")
    except Exception as e:
        writer({"status": f"Edit failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Edit applied successfully", "progress": 100})
    
    return {
        "script": updated_script,
        "script_version": state.get("script_version", 0) + 1,
        "edit_instruction": None,  # Clear after use
        "messages": [{"role": "ai", "content": agent_message}]
    }
