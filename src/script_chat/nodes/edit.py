import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from src.script_chat.llm import invoke_structured, invoke_text
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


def _needs_search(edit_instruction: str) -> bool:
    lowered = edit_instruction.lower()
    terms = ("latest", "current", "docs", "documentation", "deprecated", "api", "command", "syntax")
    return any(term in lowered for term in terms)

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
    research_section = ""

    if _needs_search(edit_instruction):
        try:
            research_notes = invoke_text(
                [
                    SystemMessage(content=EDITING_SYSTEM_PROMPT),
                    HumanMessage(
                        "Check current technical details relevant to this edit. "
                        "Focus only on commands, APIs, imports, UI names, and deprecated behavior.\n\n"
                        f"=== EDIT INSTRUCTION ===\n{edit_instruction}\n\n"
                        f"=== CURRENT SCRIPT ===\n{script_json}"
                    ),
                ],
                model="gpt-5.4-mini",
                temperature=0.2,
                tools=[{"type": "web_search"}],
            )
            research_section = f"\n\n=== TECHNICAL RESEARCH NOTES ===\n{research_notes}"
        except Exception as e:
            writer({"status": f"Edit research failed: {str(e)}", "progress": 100})
            return {"current_stage": "error"}

    prompt = f"""
=== RECENT CONVERSATION HISTORY ===
{conversation_history or "(No prior conversation)"}

=== CURRENT SCRIPT ===
{script_json}

=== EDIT INSTRUCTION ===
{edit_instruction}{research_section}
"""
    
    writer({"status": "LLM is editing the script...", "progress": 50})
    
    messages = [
        SystemMessage(content=EDITING_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    try:
        result = invoke_structured(
            messages,
            ScriptResult,
            model="gpt-5.4-mini",
            temperature=0.3,
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
