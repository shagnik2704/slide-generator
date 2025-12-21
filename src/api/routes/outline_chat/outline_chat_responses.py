"""Response building utilities for outline chat."""
import re
from typing import Dict, List, Optional


def build_compliance_message(outline_type: str, compliance: Dict, errors: List[str]) -> str:
    """Build the compliance message based on outline type."""
    if outline_type == "ICT":
        compliance_text = f"""**Pedagogy Compliance:**
- Core Teaching Scenario: {'✓' if compliance.get('core_example', False) else '⚠️ Recommended'}
- Practical Content: {compliance.get('practical_content', 0):.1f}% {'✓' if compliance.get('practical_content', 0) >= 60 else '⚠️ Need ≥60%'}
- Time checks: {'✓' if compliance.get('time_checks', True) else '⚠️'}
- No repetition: {'✓' if compliance.get('no_repetition', True) else '⚠️'}
- Skill-focused: {'✓' if compliance.get('skill_focused', True) else '⚠️'}

"""
    else:
        compliance_text = f"""**Pedagogy Compliance:**
- Core Example: {'✓' if compliance.get('core_example', False) else '✗'}
- Demo Content: {compliance.get('demo_percentage', 0):.1f}% {'✓' if compliance.get('demo_percentage', 0) >= 75 else '⚠️ Need ≥75%'}
- Menu-free: {'✓' if compliance.get('menu_free', True) else '⚠️ Rewritten'}
- Time checks: {'✓' if compliance.get('time_checks', True) else '⚠️'}
- No repetition: {'✓' if compliance.get('no_repetition', True) else '⚠️'}

"""
    
    errors_text = ""
    if errors:
        errors_text = f"\n**Issues to address:**\n" + "\n".join(f"- {e}" for e in errors) + "\n"
    
    return compliance_text + errors_text


def format_confirmation_value(value: any) -> str:
    """Format a value for display in confirmation messages."""
    if isinstance(value, list):
        if len(value) > 0:
            display_value = ", ".join(str(v) for v in value[:3])
            if len(value) > 3:
                display_value += f" ... ({len(value)} total)"
            return display_value
        else:
            return "(empty list)"
    else:
        return str(value)


def build_confirmation_response(
    project_id: int,
    pending_confirmation: Dict,
    outline_data: Dict,
    phase: str,
) -> Dict:
    """Build a confirmation response."""
    display_value = format_confirmation_value(pending_confirmation["value"])
    field_display = pending_confirmation.get("field_display", pending_confirmation["field"])
    
    # For titles, validate and reject invalid values immediately
    if pending_confirmation["field"] in ["outline_name", "tutorial_title"]:
        value = pending_confirmation.get("value", "")
        if isinstance(value, str):
            cleaned = value.strip()
            # Check if invalid
            is_invalid = False
            error_msg = ""
            
            if len(cleaned) > 50:
                is_invalid = True
                error_msg = f"The title has {len(cleaned)} characters, but it must be 50 characters or less. Please provide a shorter title."
            elif not re.match(r'^[A-Za-z0-9 ]+$', cleaned):
                invalid_chars = set(re.findall(r'[^A-Za-z0-9 ]', cleaned))
                is_invalid = True
                error_msg = f"The title contains special characters ({', '.join(sorted(invalid_chars))}). Only letters, numbers, and spaces are allowed. Please provide a title without special characters."
            
            if is_invalid:
                return {
                    "project_id": project_id,
                    "assistant_message": f"I'm sorry, I can't accept that value for **{field_display}**: `{display_value}`.\n\n{error_msg}\n\nCould you please provide it again following these rules?",
                    "follow_up_question": None,
                    "phase": phase,
                    "outline_data": outline_data,
                    "validation_errors": [error_msg],
                    "pedagogy_compliance": {},
                    "is_draft_ready": False,
                    "is_approved": False,
                    "needs_confirmation": False,
                    "confirmation_field": None,
                    "confirmation_value": None
                }
    else:
        return {
            "project_id": project_id,
            "assistant_message": f"I took this value for **{field_display}**: `{display_value}`\n\nAre you sure you want to continue with it?",
            "follow_up_question": None,
            "phase": phase,
            "outline_data": outline_data,
            "validation_errors": [],
            "pedagogy_compliance": {},
            "is_draft_ready": False,
            "is_approved": False,
            "needs_confirmation": True,
            "confirmation_field": pending_confirmation["field"],
            "confirmation_value": display_value
        }

