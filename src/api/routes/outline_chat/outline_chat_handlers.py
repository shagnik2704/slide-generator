"""Handlers for confirmation and approval in outline chat."""
from datetime import datetime
from typing import Dict, Optional

from fastapi.responses import JSONResponse

from .outline_chat_draft_generation import generate_draft_outline
from .outline_chat_extraction import validate_title
from .outline_chat_llm_utils import generate_llm_text
from .outline_chat_question_flow import determine_next_question, get_question_flow
from .outline_chat_responses import build_compliance_message
from .outline_chat_validation import validate_outline


def handle_confirmation_yes(
    pending_confirmation: Dict,
    outline_data: Dict,
    project_id: int,
) -> None:
    """Handle confirmation 'yes' - accept the pending value."""
    field = pending_confirmation.get("field")
    value = pending_confirmation.get("value")
    
    # Final validation check for titles (safety measure)
    if field in ["outline_name", "tutorial_title"] and isinstance(value, str):
        is_valid, _ = validate_title(value)
        if not is_valid:
            # This shouldn't happen since validation happens earlier, but as a safety measure
            # we'll just not set the value (it will be re-asked)
            return
    
    if field == "tutorial_title":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["title"] = value
    elif field == "tutorial_prerequisites":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["prerequisites"] = value
    elif field == "tutorial_steps":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["topics_details"] = value
    elif field == "tutorial_time":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["time_seconds"] = value
    elif field == "tutorial_comments":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["comments"] = value
    else:
        outline_data[field] = value


def handle_confirmation_no(
    pending_confirmation: Dict,
    outline_data: Dict,
    phase: str,
    conversation: list,
) -> tuple[str, Optional[str]]:
    """Handle confirmation 'no' - reject the pending value and find the question to re-ask."""
    field = pending_confirmation.get("field")
    
    # Clear the field value
    if field == "tutorial_title":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["title"] = ""
    elif field == "tutorial_prerequisites":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["prerequisites"] = ""
    elif field == "tutorial_steps":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["topics_details"] = []
    elif field == "tutorial_time":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["time_seconds"] = 0
    elif field == "tutorial_comments":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            tutorial_rows[-1]["comments"] = ""
    else:
        outline_data[field] = ""
    
    # Find the question for this field
    outline_type = outline_data.get("outline_type", "FOSS").upper()
    question_flow = get_question_flow(outline_type)
    next_question = None
    
    if phase == "warmup":
        for q in question_flow["warmup"]["questions"]:
            if q["field"] == field:
                next_question = q["question"]
                break
    elif phase == "outcomes":
        for q in question_flow["outcomes"]["questions"]:
            if q["field"] == field:
                next_question = q["question"]
                break
    elif phase == "examples":
        for q in question_flow["examples"]["questions"]:
            if q["field"] == field:
                next_question = q["question"]
                break
    elif phase == "structure":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_rows:
            last_tutorial = tutorial_rows[-1]
            if field == "tutorial_title":
                next_question = f"Tutorial #{last_tutorial.get('tutorial_number', len(tutorial_rows))} — please give a short title."
            elif field == "tutorial_prerequisites":
                next_question = f"For Tutorial #{last_tutorial.get('tutorial_number', len(tutorial_rows))}, what are the prerequisites?"
            elif field == "tutorial_steps":
                next_question = f"For Tutorial #{last_tutorial.get('tutorial_number', len(tutorial_rows))}, list 3–6 demonstrable steps."
            elif field == "tutorial_time":
                next_question = f"Could you please share your estimated time for Tutorial #{last_tutorial.get('tutorial_number', len(tutorial_rows))} ({last_tutorial.get('title', 'N/A')}) in minutes? Typically, it ranges from 2 to 10 minutes, but feel free to suggest any reasonable duration. You can provide a single number (e.g., '5 minutes') or a range (e.g., '3-4 minutes' or '3 to 4 minutes').\n\nExample answer: 7 minutes or 3-4 minutes"
    elif phase == "metadata":
        if field == "prepared_by":
            next_question = "Who prepared the outline? (Name)"
        elif field == "date":
            today = datetime.now().strftime("%Y-%m-%d")
            next_question = f"Preferred date for the outline? (default: {today})"
        elif field == "keywords":
            next_question = "Any keywords or tags to help search (3-6 words, comma-separated)?"
    
    if not next_question:
        phase, next_question = determine_next_question(outline_data, phase, conversation)
    
    return phase, next_question


def handle_approval(
    outline_data: Dict,
    phase: str,
) -> tuple[str, str]:
    """Handle approval command - generate draft and mark as approved."""
    # Generate draft if not shown yet
    if not outline_data.get("draft_shown"):
        # Auto-generate "About the Course" if missing
        if not outline_data.get("about_course"):
            try:
                about_prompt = f"""Generate a brief 1-2 paragraph "About the Course" section for a Spoken Tutorial course outline.

Course Outline Name: {outline_data.get('outline_name', 'N/A')}
Purpose: {outline_data.get('purpose', 'N/A')}
Target Audience: {outline_data.get('target_audience', 'N/A')}
Course Objectives: {', '.join(outline_data.get('course_objectives', []))}

Write 1-2 paragraphs (2-4 sentences total) describing what this course teaches and who it's for. Keep it concise and clear."""
                
                about_text = generate_llm_text(
                    about_prompt,
                    temperature=0.4,
                    max_tokens=256,
                )
                outline_data["about_course"] = about_text.strip()
            except:
                outline_data["about_course"] = f"This course teaches {outline_data.get('outline_name', 'the subject')} to {outline_data.get('target_audience', 'learners')}."
        
        # Generate draft
        draft = generate_draft_outline(outline_data)
        outline_data["draft"] = draft
        outline_data["draft_shown"] = True
        
        # Run validation
        errors, compliance = validate_outline(outline_data)
        outline_type = outline_data.get("outline_type", "FOSS").upper()
        
        # Build compliance message
        compliance_text = build_compliance_message(outline_type, compliance, errors)
        
        assistant_message = f"""Here's your final draft Course Outline:

{draft}

{compliance_text}
Outline approved! Generating final outputs..."""
    else:
        assistant_message = "Outline approved! Generating final outputs..."
    
    # Mark as approved
    phase = "approved"
    outline_data["status"] = "approved"
    outline_data["approved_at"] = datetime.now().isoformat()
    
    return phase, assistant_message

