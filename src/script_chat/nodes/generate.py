import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.script_chat.prompts.generation import GENERATION_SYSTEM_PROMPT

def generate_node(state: ScriptChatState):
    """Generates the pedagogical script based on metadata and outline."""
    writer = get_stream_writer()
    metadata = state.get("metadata", {})
    raw_outline = state.get("raw_outline", "")
    
    writer({"status": "Generating pedagogical script...", "progress": 25})
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        writer({"status": "Error: OPENAI_API_KEY not found", "progress": 100})
        return {"current_stage": "error"}
        
    llm = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.4,
        api_key=api_key
    ).bind_tools([{"type": "web_search"}])
    
    prompt = f"""
    === METADATA ===
    {json.dumps(metadata, indent=2)}
    
    === OUTLINE ===
    {raw_outline}
    
    Generate the JSON array for the script slides now. Ensure the output is ONLY a valid JSON array.
    """
    
    writer({"status": "LLM is writing the script...", "progress": 50})
    
    messages = [
        SystemMessage(content=GENERATION_SYSTEM_PROMPT),
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
        script_json = parsed_json.get("script", [])
        agent_message = parsed_json.get("message", "Here is your generated script.")
    except Exception as e:
        writer({"status": f"Script generation failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Script generation complete", "progress": 100})
    
    return {
        "script": script_json,
        "script_version": state.get("script_version", 0) + 1,
        # Append the agent message to the chat history
        "messages": [{"role": "ai", "content": agent_message}]
    }

def script_review_node(state: ScriptChatState):
    """Surfaces generated script for HITL review."""
    script = state.get("script")
    
    # We retrieve the last AI message from the state to display in the UI interrupt
    agent_message = "Review the generated script. Approve to continue, or request edits."
    if state.get("messages"):
        last_msg = state["messages"][-1]
        if getattr(last_msg, "type", "") == "ai" or (isinstance(last_msg, dict) and last_msg.get("role") == "ai"):
            agent_message = getattr(last_msg, "content", last_msg.get("content", agent_message))

    user_decision = interrupt({
        "type": "script_review",
        "script": script,
        "message": agent_message
    })
    
    action = user_decision.get("action")
    
    if action == "approve":
        return {"current_stage": "compliance"}
    else:
        # If user requests an edit, loop back to the edit node and save their instruction
        user_msg = user_decision.get("instruction", "")
        return {
            "current_stage": "edit",
            "edit_instruction": user_msg,
            "messages": [{"role": "user", "content": user_msg}] if user_msg else []
        }
