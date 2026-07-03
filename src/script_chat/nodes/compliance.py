import json
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.services.compliance_service import check_compliance

async def compliance_node(state: ScriptChatState):
    """Runs the existing compliance checks on the approved script."""
    writer = get_stream_writer()
    script = state.get("script", [])
    metadata = state.get("metadata", {})
    
    if not script:
        writer({"status": "Error: No script to check", "progress": 100})
        return {"current_stage": "error"}
    
    writer({"status": "Preparing script for compliance checks...", "progress": 10})
    
    # The existing check_compliance expects a dict with a "slides" key
    # and optionally other metadata fields
    json_script = {
        "presentation_title": metadata.get("title", "Untitled"),
        "slides": script
    }
    
    writer({"status": "Running admin compliance checks (16 criteria)...", "progress": 30})
    
    try:
        results = await check_compliance(json_script, tutorial_type="demo")
    except Exception as e:
        writer({"status": f"Compliance check failed: {str(e)}", "progress": 100})
        return {
            "current_stage": "error",
            "compliance_results": {"error": str(e)}
        }
    
    # Calculate pass rate for the progress message
    summary = results.get("summary", {})
    passed = summary.get("ai_passed", 0)
    total = summary.get("total", 0)
    
    writer({"status": f"Compliance complete: {passed}/{total} checks passed", "progress": 100})
    
    return {
        "compliance_results": results
    }

def compliance_review_node(state: ScriptChatState):
    """Surfaces compliance results for HITL review."""
    compliance_results = state.get("compliance_results", {})
    summary = compliance_results.get("summary", {})
    
    user_decision = interrupt({
        "type": "compliance_review",
        "results": compliance_results,
        "summary": summary,
        "message": "Review the compliance results. Approve to finalize, or go back to edit the script."
    })
    
    action = user_decision.get("action")
    
    if action == "approve":
        return {"current_stage": "done"}
    elif action == "edit":
        # User wants to go back and fix issues found by compliance
        return {
            "current_stage": "edit",
            "edit_instruction": user_decision.get("instruction", "Fix the compliance issues found above.")
        }
    else:
        return {"current_stage": "done"}
