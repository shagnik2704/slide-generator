"""Processing logic for outline chat - field extraction and user input handling."""
import json
from typing import Dict, Optional, Tuple

from fastapi.responses import JSONResponse

from .outline_chat_draft_generation import generate_draft_outline
from .outline_chat_extraction import (
    build_extraction_prompt,
    determine_current_field,
    extract_and_set_field_value,
    validate_title,
)
from .outline_chat_field_extraction import extract_json_block
from .outline_chat_handlers import handle_approval
from .outline_chat_llm_utils import friendly_rewrite_question, generate_llm_text, get_example_answer_hint
from .outline_chat_models import ChatMessage
from .outline_chat_question_flow import determine_next_question, get_question_flow
from .outline_chat_responses import (
    build_compliance_message,
    build_confirmation_response,
    format_confirmation_value,
)
from .outline_chat_session import save_session
from .outline_chat_validation import validate_outline


def process_user_input(
    last_message: ChatMessage,
    outline_data: Dict,
    phase: str,
    project_id: int,
    conversation: list,
) -> Tuple[Dict, str, Optional[Dict], Optional[JSONResponse]]:
    """
    Process user input and extract field values.
    Returns: (outline_data, phase, pending_confirmation, early_response)
    """
    user_content = last_message.content.lower().strip()
    outline_type = outline_data.get("outline_type", "FOSS").upper()
    
    # Determine which field we're collecting
    current_field, _ = determine_current_field(phase, outline_data, outline_type)
    
    if not current_field:
        return outline_data, phase, None, None
    
    # Build extraction prompt
    extraction_prompt = build_extraction_prompt(
        phase, current_field, last_message.content, outline_type, outline_data
    )
    
    if not extraction_prompt:
        return outline_data, phase, None, None
    
    # Extract using LLM
    try:
        extracted_text = generate_llm_text(
            extraction_prompt,
            temperature=0.0,
            max_tokens=512,
            system_prompt="You are a strict information extraction assistant. Follow the instructions exactly.",
        )
        
        # Extract and set field value
        extracted_value, field_display, needs_confirmation = extract_and_set_field_value(
            current_field, extracted_text, last_message.content, outline_data, outline_type
        )
        
        # Strict validation for titles - reject immediately and re-ask
        if current_field in ["outline_name", "tutorial_title"] and isinstance(extracted_value, str):
            is_valid, error_msg = validate_title(extracted_value)
            if not is_valid:
                # Get the question from the question flow
                question_flow = get_question_flow(outline_type)
                next_question = None
                
                if current_field == "outline_name":
                    # Find the question for outline_name in the current phase
                    if phase == "warmup":
                        for q in question_flow["warmup"]["questions"]:
                            if q["field"] == "outline_name":
                                next_question = q["question"]
                                break
                elif current_field == "tutorial_title":
                    # For tutorial title, construct the question
                    tutorial_rows = outline_data.get("tutorial_rows", [])
                    if tutorial_rows:
                        tutorial_num = tutorial_rows[-1].get("tutorial_number", len(tutorial_rows))
                        next_question = f"Tutorial #{tutorial_num} — please give a short title (under 50 characters, letters/numbers/spaces only)."
                
                # Fallback if question not found
                if not next_question:
                    if current_field == "outline_name":
                        next_question = "What would you like to call this course? The course outline name must be under 50 characters and use only letters, numbers, and spaces (no special characters)."
                    else:
                        tutorial_rows = outline_data.get("tutorial_rows", [])
                        if tutorial_rows:
                            tutorial_num = tutorial_rows[-1].get("tutorial_number", len(tutorial_rows))
                            next_question = f"Tutorial #{tutorial_num} — please give a short title (under 50 characters, letters/numbers/spaces only)."
                
                # Make the question friendlier
                rewritten = friendly_rewrite_question(next_question, outline_type, phase)
                example_hint = get_example_answer_hint(outline_type, phase, next_question)
                if example_hint:
                    question_text = f"{rewritten}\n\nExample answer: {example_hint}"
                else:
                    question_text = rewritten
                
                return outline_data, phase, None, JSONResponse({
                    "project_id": project_id,
                    "assistant_message": f"I'm sorry, I can't accept that value for **{field_display}**: `{extracted_value}`.\n\n{error_msg}\n\n{question_text}",
                    "follow_up_question": next_question,
                    "phase": phase,
                    "outline_data": outline_data,
                    "validation_errors": [error_msg],
                    "pedagogy_compliance": {},
                    "is_draft_ready": False,
                    "is_approved": False,
                    "needs_confirmation": False,
                })
        
        # Handle special case: invalid tutorial time
        if current_field == "tutorial_time" and extracted_value == 0:
            tutorial_rows = outline_data.get("tutorial_rows", [])
            tutorial_title = ""
            if tutorial_rows:
                tutorial_title = tutorial_rows[-1].get("title", "")
            
            question_text = f"Could you please share your estimated time for Tutorial #{len(tutorial_rows) if tutorial_rows else 1} ({tutorial_title if tutorial_title else 'N/A'}) in minutes? Typically, it ranges from 2 to 10 minutes, but feel free to suggest any reasonable duration. You can provide a single number (e.g., '5 minutes') or a range (e.g., '3-4 minutes' or '3 to 4 minutes').\n\nExample answer: 7 minutes or 3-4 minutes"
            
            return outline_data, phase, None, JSONResponse({
                "project_id": project_id,
                "assistant_message": f"Please provide a reasonable estimated time for this tutorial (typically 2-30 minutes). You can provide a single number or a range.\n\n{question_text}",
                "follow_up_question": question_text,
                "phase": phase,
                "outline_data": outline_data,
                "validation_errors": [],
                "pedagogy_compliance": {},
                "is_draft_ready": False,
                "is_approved": False,
            })
        
        if needs_confirmation:
            pending_confirmation = {
                "field": current_field,
                "value": extracted_value,
                "field_display": field_display,
            }
            save_session(project_id, outline_data, phase, pending_confirmation)
            return outline_data, phase, pending_confirmation, JSONResponse(
                build_confirmation_response(project_id, pending_confirmation, outline_data, phase)
            )
        else:
            save_session(project_id, outline_data, phase, None)
            return outline_data, phase, None, None
            
    except Exception:
        # Fallback to regex-based extraction
        if current_field == "recommended_no_of_tutorials":
            import re
            numbers = re.findall(r'\d+', last_message.content)
            if numbers:
                outline_data["recommended_no_of_tutorials"] = int(numbers[0])
        elif current_field == "outline_type":
            user_lower = last_message.content.lower()
            if "foss" in user_lower or "free" in user_lower or "open" in user_lower:
                outline_data["outline_type"] = "FOSS"
            elif "ict" in user_lower or "digital" in user_lower or "skill" in user_lower:
                outline_data["outline_type"] = "ICT"
            elif "other" in user_lower:
                outline_data["outline_type"] = "OTHER"
            else:
                outline_data["outline_type"] = "FOSS"
        else:
            from .outline_chat_field_extraction import extract_field_from_response
            outline_data = extract_field_from_response(current_field, last_message.content, outline_data)
        
        save_session(project_id, outline_data, phase, None)
        return outline_data, phase, None, None


def handle_review_phase(
    outline_data: Dict,
    phase: str,
    last_message: Optional[ChatMessage],
    user_content: str,
) -> Tuple[str, str]:
    """
    Handle review phase logic - generate draft, handle edits, etc.
    Returns: (phase, assistant_message)
    """
    assistant_message = ""
    
    # Handle edits in review phase
    if outline_data.get("draft_shown") and last_message and last_message.role == "user" and user_content and user_content != "approve":
        try:
            edit_prompt = f"""The user wants to edit the course outline. Parse their edit request and return a JSON object with the changes to apply.

Current outline data:
{json.dumps(outline_data, indent=2)}

User's edit request: {last_message.content}

Return JSON with structure:
{{
  "updates": {{
    "field_name": "new_value",
    "tutorial_rows": [
      {{"tutorial_number": 1, "title": "...", "prerequisites": "...", "topics_details": [...], "time_seconds": 300, "comments": "..."}},
      ...
    ]
  }},
  "summary": "Brief description of changes made"
}}

Only include fields that need to be changed. For tutorial_rows, include ALL tutorials (not just changed ones)."""
            
            edit_response = generate_llm_text(
                edit_prompt,
                temperature=0.1,
                max_tokens=1024,
                system_prompt="You are a precise JSON editor for course outlines. Always return valid JSON.",
            )
            edit_json = json.loads(extract_json_block(edit_response))
            
            # Apply updates
            if "updates" in edit_json:
                updates = edit_json["updates"]
                for key, value in updates.items():
                    if key == "tutorial_rows":
                        outline_data["tutorial_rows"] = value
                    else:
                        outline_data[key] = value
                
                # Regenerate draft
                draft = generate_draft_outline(outline_data)
                outline_data["draft"] = draft
                outline_data["draft_shown"] = True
                
                # Run validation
                errors, compliance = validate_outline(outline_data)
                outline_type = outline_data.get("outline_type", "FOSS").upper()
                compliance_text = build_compliance_message(outline_type, compliance, errors)
                
                assistant_message = f"""✓ Applied your edits: {edit_json.get('summary', 'Changes applied')}

Here's your updated draft Course Outline:

{draft}

{compliance_text}
Please review and suggest any more edits, or type 'approve' when ready to finalize."""
            else:
                assistant_message = "I understood your request. Let me apply those changes...\n\n"
        except Exception as e:
            assistant_message = f"I had trouble parsing your edits. Could you rephrase? (Error: {str(e)})\n\n"
    
    # Generate and show draft if not shown yet
    elif not outline_data.get("draft_shown"):
        # Auto-generate "About the Course" if missing
        if not outline_data.get("about_course"):
            try:
                about_prompt = f"""Generate a brief 1-2 paragraph "About the Course" section for a Spoken Tutorial course outline.

Course Outline Name: {outline_data.get('outline_name', 'N/A')}
Purpose: {outline_data.get('purpose', 'N/A')}
Target Audience: {outline_data.get('target_audience', 'N/A')}
Course Objectives: {'; '.join(outline_data.get('course_objectives', []))}

Write 1-2 paragraphs (2-4 sentences total) describing what this course teaches and who it's for. Keep it concise and clear."""
                
                about_text = generate_llm_text(
                    about_prompt,
                    temperature=0.4,
                    max_tokens=256,
                )
                outline_data["about_course"] = about_text.strip()
            except:
                outline_data["about_course"] = f"This course teaches {outline_data.get('outline_name', 'the subject')} to {outline_data.get('target_audience', 'learners')}."
        
        # Generate final draft
        draft = generate_draft_outline(outline_data)
        outline_data["draft"] = draft
        outline_data["draft_shown"] = True
        
        # Run validation
        errors, compliance = validate_outline(outline_data)
        outline_type = outline_data.get("outline_type", "FOSS").upper()
        compliance_text = build_compliance_message(outline_type, compliance, errors)
        
        assistant_message = f"""Here's your final Course Outline:

{draft}

{compliance_text}
Type 'approve' to finalize the outline."""
    elif outline_data.get("draft_shown") and not assistant_message:
        assistant_message = "Please review the draft above and type 'approve' to finalize."
    
    return phase, assistant_message

