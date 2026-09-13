import logging
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.compliance.workflow import run_admin_script_compliance
from src.script_chat.schemas import dump_models, parse_script

logger = logging.getLogger(__name__)

async def compliance_node(state: ScriptChatState):
    """Runs the 25-criteria evidence-based compliance checks on the approved script."""
    writer = get_stream_writer()
    script = state.get("script", [])
    metadata = state.get("metadata", {})
    raw_outline = state.get("raw_outline", "")
    foss_name = state.get("foss_name")
    
    if not script:
        writer({"status": "Error: No script to check", "progress": 100})
        return {"current_stage": "error"}

    try:
        script_payload = dump_models(parse_script(script))
    except Exception as e:
        writer({"status": f"Invalid script state: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Preparing script for compliance checks...", "progress": 10})
    
    metadata_dict = metadata.model_dump() if hasattr(metadata, "model_dump") else (metadata or {})
    title = metadata_dict.get("title", "Untitled")
    outline_topics = metadata_dict.get("outline_topics", [])
    
    # Full metadata payload expected by run_admin_script_compliance
    json_script = {
        "presentation_title": title,
        "title": title,
        "domain": foss_name or title,
        "tutorial": title,
        "learning_objectives": metadata_dict.get("learning_objectives", []),
        "prerequisites": metadata_dict.get("prerequisites", ""),
        "system_requirements": metadata_dict.get("system_requirements", ""),
        "outline": outline_topics if outline_topics else ([raw_outline] if raw_outline else []),
        "keywords": metadata_dict.get("meta_tags", []),
        "meta_tags": metadata_dict.get("meta_tags", []),
        "slides": script_payload
    }
    
    writer({"status": "Running admin compliance checks (25 criteria)...", "progress": 30})
    
    try:
        results = await run_admin_script_compliance(json_script, tutorial_type="demo")
    except Exception as e:
        logger.exception("Compliance check failed with error: %s", e)
        writer({"status": f"Compliance check failed: {str(e)}", "progress": 100})
        return {
            "current_stage": "error",
            "compliance_results": {"error": str(e)}
        }
    
    # Calculate pass rate and severities for the progress message
    summary = results.get("summary", {})
    passed = summary.get("ai_passed", 0)
    total = summary.get("total", len(results.get("checks", [])))
    blockers = summary.get("blockers", 0)
    major = summary.get("major", 0)
    
    status_suffix = f" ({blockers} blockers, {major} major)" if (blockers or major) else ""
    writer({"status": f"Compliance complete: {passed}/{total} checks passed{status_suffix}", "progress": 100})
    
    return {
        "compliance_results": results
    }

def compliance_review_node(state: ScriptChatState):
    """Surfaces compliance results for HITL review."""
    compliance_results = state.get("compliance_results", {})
    summary = compliance_results.get("summary", {})
    issues = compliance_results.get("issues", [])
    
    user_decision = interrupt({
        "type": "compliance_review",
        "results": compliance_results,
        "summary": summary,
        "issues": issues,
        "message": "Review the compliance results. Approve to finalize, or request edits to resolve issues."
    })
    
    if not user_decision or not isinstance(user_decision, dict):
        return {"current_stage": "error"}

    action = user_decision.get("action")
    
    if action == "approve":
        return {"current_stage": "done"}
    elif action == "edit":
        # User wants to go back and fix issues found by compliance
        user_msg = user_decision.get("instruction") or "Fix the compliance issues found above."
        return {
            "current_stage": "edit",
            "edit_instruction": user_msg,
            "messages": [{"role": "user", "content": user_msg}]
        }

    return {"current_stage": "error"}
