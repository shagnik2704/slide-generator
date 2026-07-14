from langchain_core.messages import SystemMessage, HumanMessage
from src.script_chat.state import ScriptChatState
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from src.script_chat.llm import invoke_structured, invoke_text
from src.script_chat.prompts.grounding import GROUNDING_SYSTEM_PROMPT
from src.script_chat.prompts.ground_edit import GROUND_EDITING_SYSTEM_PROMPT
from src.script_chat.schemas import GroundingReport, dump_model

def ground_node(state: ScriptChatState):
    """Grounds the content using Google Search."""
    if state.get("grounding_report"):
        return {}
        
    writer = get_stream_writer()
    raw_outline = state.get("raw_outline", "")
    foss_name = state.get("foss_name", "Unknown Software")
    
    writer({"status": f"Searching latest docs for {foss_name}...", "progress": 25})
    
    writer({"status": "Validating code snippets against web results...", "progress": 50})
    
    try:
        validation_notes = invoke_text(
            [
                SystemMessage(content=GROUNDING_SYSTEM_PROMPT),
                HumanMessage(content=f"Validate this outline for {foss_name}:\n\n{raw_outline}"),
            ],
            model="gpt-5.4-mini",
            temperature=0.2,
            tools=[{"type": "web_search"}],
        )
        report = invoke_structured(
            [
                SystemMessage(content=GROUNDING_SYSTEM_PROMPT),
                HumanMessage(
                    "Create the final grounding report from this outline and validation notes.\n\n"
                    f"=== OUTLINE ===\n{raw_outline}\n\n"
                    f"=== VALIDATION NOTES ===\n{validation_notes}"
                ),
            ],
            GroundingReport,
            model="gpt-5.4-mini",
            temperature=0.2,
        )
    except Exception as e:
        writer({"status": f"Grounding failed: {str(e)}", "progress": 100})
        fallback_report = GroundingReport(
            validated_content=raw_outline,
            corrections_made=[],
            warnings=[f"Grounding validation failed due to system error: {str(e)}"],
            is_mostly_correct=False,
            error=str(e),
        )
        return {
            "grounding_report": dump_model(fallback_report)
        }

    
    writer({"status": "Validation complete", "progress": 100})
    
    return {
        "grounding_report": dump_model(report)
    }

def ground_review_node(state: ScriptChatState):
    """Surfaces grounding results for HITL review."""
    report_dict = state.get("grounding_report")
    if not report_dict:
        return {"current_stage": "error"}
    
    # The interrupt pauses execution here and sends this payload to the client.
    # The graph will wait until it is invoked again with Command(resume=decision)
    user_decision = interrupt({
        "type": "validation_review",
        "report": report_dict,
        "message": "Review the grounding results. Please approve or provide edits."
    })
    
    # Execution resumes here
    if not user_decision or not isinstance(user_decision, dict):
        return {"current_stage": "error"}

    action = user_decision.get("action")
    if action == "approve":
        final_content = report_dict.get("validated_content")
        return {
            "current_stage": "metadata",
            "raw_outline": final_content
        }
    elif action == "edit":
        instruction = user_decision.get("instruction")
        edited_content = user_decision.get("edited_content")
        
        if instruction:
            # Clear grounding report so the next ground node run recheck doesn't return early
            return {
                "current_stage": "grounding_edit",
                "edit_instruction": instruction,
                "grounding_report": None
            }
        elif edited_content:
            # Direct manual edit - proceed to metadata stage
            return {
                "current_stage": "metadata",
                "raw_outline": edited_content
            }
        else:
            # Fallback
            return {
                "current_stage": "metadata",
                "raw_outline": report_dict.get("validated_content")
            }
            
    return {"current_stage": "error"}

def ground_edit_node(state: ScriptChatState):
    """Applies user's edit instruction to the raw outline."""
    writer = get_stream_writer()
    raw_outline = state.get("raw_outline", "")
    edit_instruction = state.get("edit_instruction")
    
    if not edit_instruction:
        return {}
        
    writer({"status": "Applying outline edits...", "progress": 50})
    
    prompt = f"""
=== CURRENT OUTLINE ===
{raw_outline}

=== EDIT INSTRUCTION ===
{edit_instruction}

Apply the edit instruction and return the full updated outline text.
"""
    messages = [
        SystemMessage(content=GROUND_EDITING_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    try:
        updated_outline = invoke_text(messages, model="gpt-5.4-mini", temperature=0.2)
    except Exception as e:
        writer({"status": f"Outline edit failed: {str(e)}", "progress": 100})
        return {"current_stage": "error"}
        
    writer({"status": "Outline edits applied successfully", "progress": 100})
    
    return {
        "raw_outline": updated_outline,
        "edit_instruction": None,
        "current_stage": "grounding"
    }
