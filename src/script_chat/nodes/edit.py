import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from src.script_chat.llm import invoke_structured_with_responses_tools
from src.script_chat.prompts.editing import EDITING_SYSTEM_PROMPT
from src.script_chat.schemas import ScriptResult, dump_models, parse_script


def _recent_edit_context(messages: list) -> str:
    history_lines = []
    for msg in messages[-4:]:
        role = msg.get("role", "unknown") if isinstance(msg, dict) else getattr(msg, "type", "unknown")
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        if role in {"user", "ai", "human"} and content:
            history_lines.append(f"{role.upper()}: {content[:240]}")
    return "\n".join(history_lines)


def _compliance_edit_context(compliance_results: dict | None) -> str:
    if not compliance_results:
        return "(No compliance results yet)"

    failed_checks = [
        {
            "id": check.get("id"),
            "criteria": check.get("criteria"),
            "notes": check.get("ai_notes"),
            "severity": check.get("severity"),
        }
        for check in compliance_results.get("checks", [])
        if check.get("ai_review") is False
    ]
    issues = [
        {
            "criteria_id": issue.get("criteria_id"),
            "message": issue.get("message"),
            "suggested_action": issue.get("suggested_action"),
            "evidence": issue.get("evidence", [])[:3],
        }
        for issue in compliance_results.get("issues", [])[:10]
    ]
    return json.dumps({"failed_checks": failed_checks[:10], "issues": issues}, indent=2)


def edit_node(state: ScriptChatState):
    """Applies user's edit instruction to the current script."""
    writer = get_stream_writer()
    current_script = state.get("script", [])
    edit_instruction = state.get("edit_instruction", "")
    
    if not edit_instruction:
        writer({"status": "No edit instruction provided", "progress": 100})
        return {}
    
    writer({"status": f"Applying edit: '{edit_instruction[:60]}...'", "progress": 25})
    
    try:
        script_model = parse_script(current_script)
    except Exception as e:
        writer({"status": f"Invalid script state: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    conversation_history = _recent_edit_context(state.get("messages", []))
    script_json = json.dumps(dump_models(script_model), indent=2)
    metadata_json = json.dumps(state.get("metadata", {}), indent=2)
    raw_outline = state.get("raw_outline") or "(No original outline available)"
    compliance_context = _compliance_edit_context(state.get("compliance_results"))

    prompt = f"""
=== RECENT CONVERSATION HISTORY ===
{conversation_history or "(No prior conversation)"}

=== METADATA ===
{metadata_json}

=== ORIGINAL OUTLINE ===
{raw_outline}

=== COMPLIANCE CONTEXT ===
{compliance_context}

=== CURRENT SCRIPT ===
{script_json}

=== EDIT INSTRUCTION ===
{edit_instruction}
"""
    
    writer({"status": "LLM is editing the script...", "progress": 50})
    
    messages = [
        SystemMessage(content=EDITING_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    try:
        result = invoke_structured_with_responses_tools(
            messages,
            ScriptResult,
            model="gpt-5.4-mini",
            temperature=0.3,
            tools=[{"type": "web_search_preview"}],
        )
    except Exception as e:
        writer({"status": f"Edit failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Edit applied successfully", "progress": 100})
    
    return {
        "script": dump_models(result.script),
        "script_version": state.get("script_version", 0) + 1,
        "edit_instruction": None,
        "messages": [{"role": "ai", "content": result.message}]
    }
