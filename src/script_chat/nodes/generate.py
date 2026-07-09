import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.script_chat.llm import invoke_structured_with_responses_tools
from src.script_chat.prompts.generation import GENERATION_SYSTEM_PROMPT
from src.script_chat.schemas import ScriptResult, dump_models, parse_metadata, parse_script

def generate_node(state: ScriptChatState):
    """Generates the pedagogical script based on metadata and outline."""
    writer = get_stream_writer()
    metadata = state.get("metadata", {})
    raw_outline = state.get("raw_outline", "")
    
    writer({"status": "Generating pedagogical script...", "progress": 25})
    
    try:
        metadata_model = parse_metadata(metadata)
    except Exception as e:
        writer({"status": f"Invalid metadata state: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    metadata_json = json.dumps(metadata_model.model_dump(), indent=2)
    
    writer({"status": "LLM is writing the script...", "progress": 50})

    try:
        result = invoke_structured_with_responses_tools(
            [
                SystemMessage(content=GENERATION_SYSTEM_PROMPT),
                HumanMessage(
                    f"=== METADATA ===\n{metadata_json}\n\n"
                    f"=== OUTLINE ===\n{raw_outline}"
                ),
            ],
            ScriptResult,
            model="gpt-5.4-mini",
            temperature=0.4,
            tools=[{"type": "web_search_preview"}],
        )
    except Exception as e:
        writer({"status": f"Script generation failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Script generation complete", "progress": 100})
    
    return {
        "script": dump_models(result.script),
        "script_version": state.get("script_version", 0) + 1,
        "messages": [{"role": "ai", "content": result.message}]
    }

def script_review_node(state: ScriptChatState):
    """Surfaces generated script for HITL review."""
    script = state.get("script")
    try:
        script_payload = dump_models(parse_script(script or []))
    except Exception:
        return {"current_stage": "error"}
    
    # We retrieve the last AI message from the state to display in the UI interrupt
    agent_message = "Review the generated script. Approve to continue, or request edits."
    if state.get("messages"):
        last_msg = state["messages"][-1]
        if getattr(last_msg, "type", "") == "ai" or (isinstance(last_msg, dict) and last_msg.get("role") == "ai"):
            agent_message = getattr(last_msg, "content", last_msg.get("content", agent_message))

    user_decision = interrupt({
        "type": "script_review",
        "script": script_payload,
        "message": agent_message
    })
    
    action = user_decision.get("action")
    
    if action == "approve":
        return {"current_stage": "compliance"}
    if action == "edit":
        user_msg = user_decision.get("instruction", "")
        return {
            "current_stage": "edit",
            "edit_instruction": user_msg,
            "messages": [{"role": "user", "content": user_msg}] if user_msg else []
        }

    return {"current_stage": "error"}
