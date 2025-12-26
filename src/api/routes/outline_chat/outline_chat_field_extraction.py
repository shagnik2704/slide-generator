"""Field extraction utilities for outline chat."""
import re
from typing import Dict

from .outline_chat_llm_utils import generate_llm_text


def extract_json_block(text: str) -> str:
    """Extract JSON payload from a response that may contain code fences."""
    cleaned = text.strip()
    if "```" in cleaned:
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[-1]
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[-1]
        cleaned = cleaned.split("```")[0]
    return cleaned.strip()


def transform_menu_instructions(text: str) -> str:
    """Transform menu-based instructions into action steps."""
    # Pattern: "File → Open" or "Go to File → Export"
    pattern = r"(\w+)\s*→\s*(\w+)"
    
    def replace_menu(match):
        menu1, menu2 = match.groups()
        return f"Click {menu1}, then {menu2}. In the dialog that appears, choose your option and confirm."
    
    transformed = re.sub(pattern, replace_menu, text)
    return transformed


def should_ask_confirmation(field: str, value: any, original_response: str = "") -> bool:
    """
    Returns True ONLY if the value is clearly inappropriate or wrong.
    Default behavior: ACCEPT the answer (return False) unless it's obviously wrong.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return False  # Empty values don't need confirmation

    # DEFAULT: Accept all reasonable answers. Only flag clearly inappropriate ones.
    
    # Fields that should NEVER need confirmation - accept any reasonable answer
    auto_accept_fields = [
        "purpose", "target_audience", "entry_behaviour", "platform_name", 
        "os_version", "core_example", "prepared_by", "date", "domain",
        "tutorial_prerequisites", "tutorial_comments", "course_objectives",
        "topics_included", "topics_not_included", "allied_examples", "keywords"
    ]
    
    if field in auto_accept_fields:
        if isinstance(value, str):
            cleaned = value.strip()
            # ONLY reject if it's clearly inappropriate: too short (< 2 chars) or error messages
            if len(cleaned) < 2:
                return True
            # Check for error indicators ONLY
            error_indicators = [
                "could not extract", "not a", "does not specify", "not found",
                "error", "unable to", "i cannot", "i don't", "i'm not sure",
                "placeholder", "test input", "example only"
            ]
            if any(indicator in cleaned.lower() for indicator in error_indicators):
                return True
            # Accept everything else - don't ask for confirmation
            return False
        elif isinstance(value, list):
            # For lists, accept if it has any items
            if len(value) > 0:
                return False
            return True  # Empty list might be inappropriate

    # For platform_name (FOSS / tool name + version), accept normal-looking values
    if field == "platform_name" and isinstance(value, str):
        cleaned = value.strip()
        if 2 <= len(cleaned) <= 100:  # Very permissive length
            return False  # Accept it

    # For course outline name and tutorial title, enforce strict validation:
    # - Max 50 characters
    # - Only letters, numbers, and spaces (no special characters)
    if field in ["outline_name", "tutorial_title"] and isinstance(value, str):
        cleaned = value.strip()
        if len(cleaned) == 0:
            return False  # let normal flow handle empty
        # If invalid format, force confirmation so we can reject and re-ask
        if len(cleaned) > 50 or not re.match(r'^[A-Za-z0-9 ]+$', cleaned):
            return True
        # If valid according to these rules, NEVER ask for confirmation
        return False
    
    # Quick check: ONLY flag obvious error messages
    if isinstance(value, str):
        value_str = value.lower().strip()
        # Only check for error messages - be very strict
        error_indicators = [
            "could not extract", "not a", "does not specify", "not found",
            "error", "unable to", "i cannot", "i don't", "i'm not sure",
            "placeholder", "test input"
        ]
        if any(indicator in value_str for indicator in error_indicators):
            return True
        # For any reasonable string (>= 2 chars), accept without confirmation
        if len(value_str) >= 2:
            return False
        # Very short strings (< 2 chars) might be inappropriate
        return True
    elif isinstance(value, list):
        # Check if any item in the list looks like an error
        for item in value:
            if isinstance(item, str):
                item_lower = item.lower()
                error_indicators = ["could not", "not a", "does not", "error", "unable"]
                if any(indicator in item_lower for indicator in error_indicators):
                    return True
        # If list has any items, accept it
        if len(value) > 0:
            return False
        # Empty list might be inappropriate
        return True
    elif isinstance(value, (int, float)):
        # For numbers, accept reasonable ranges
        if field == "tutorial_time" or field == "time_seconds":
            # Time validation is handled separately, accept here
            return False
        if field == "recommended_no_of_tutorials":
            # Accept any positive number
            if value > 0:
                return False
        # Accept any number
        return False
    
    # Default: ACCEPT the answer (don't ask for confirmation)
    # Only use LLM as a last resort for truly suspicious cases
    try:
        # Format value for display
        if isinstance(value, list):
            display_value = ", ".join(str(v) for v in value[:3])
            if len(value) > 3:
                display_value += f" ... ({len(value)} total)"
        else:
            display_value = str(value)

        prompt = f"""You are validating a user's answer in a course outline system.

Field: {field}
Extracted value: {display_value}

ONLY return "yes" if the value is CLEARLY INAPPROPRIATE or WRONG:
- Single character or extremely short (< 2 chars)
- Contains error messages like "could not extract" or "not found"
- Looks like placeholder/test text like "test" or "placeholder"
- Completely unrelated gibberish

If the value is reasonable, complete, and makes sense for the field, return "no".

Be VERY PERMISSIVE. Only flag obviously wrong answers.

Return ONLY "yes" or "no" (lowercase, no quotes)."""

        result = generate_llm_text(
            prompt,
            temperature=0.0,
            max_tokens=4,
            system_prompt="You are a permissive validator. Default to accepting answers. Only flag clearly wrong ones.",
        ).strip().lower()

        # Only return True if LLM explicitly says "yes" (clearly inappropriate)
        return result == "yes"

    except Exception:
        # If LLM call fails, DEFAULT TO ACCEPTING (be permissive)
        # Only reject if it's obviously too short
        if isinstance(value, str) and len(value.strip()) < 2:
            return True
        # Otherwise, accept it
        return False


def extract_field_from_response(field: str, response: str, outline_data: Dict) -> Dict:
    """Extract and transform field value from SME response."""
    updated = outline_data.copy()
    
    if field == "course_objectives":
        # Extract bullet points or numbered list
        objectives = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', response, re.MULTILINE)
        if not objectives:
            # Try semicolon-separated, then comma-separated, then line-separated
            if ';' in response:
                objectives = [item.strip() for item in response.split(';') if item.strip()]
            elif ',' in response:
                objectives = [item.strip() for item in response.split(',') if item.strip()]
            else:
                objectives = [line.strip() for line in response.split('\n') if line.strip()]
        updated["course_objectives"] = objectives[:6]  # Max 6
    
    elif field == "topics_included" or field == "topics_not_included":
        topics = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', response, re.MULTILINE)
        if not topics:
            # Try semicolon-separated, then comma-separated, then line-separated
            if ';' in response:
                topics = [item.strip() for item in response.split(';') if item.strip()]
            elif ',' in response:
                topics = [item.strip() for item in response.split(',') if item.strip()]
            else:
                topics = [line.strip() for line in response.split('\n') if line.strip()]
        updated[field] = topics
    
    elif field == "allied_examples":
        examples = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', response, re.MULTILINE)
        if not examples:
            # Try semicolon-separated, then comma-separated, then line-separated
            if ';' in response:
                raw_items = response.split(';')
            elif ',' in response:
                raw_items = response.split(',')
            else:
                raw_items = response.split('\n')

            examples = [
                item.strip() for item in raw_items
                if item.strip() and item.strip().lower() not in ['no', 'none', 'n/a']
            ]
        updated["allied_examples"] = examples[:2]  # Max 2
    
    elif field == "keywords":
        # Support semicolon- or comma-separated keywords
        if ';' in response:
            raw_keywords = response.split(';')
        else:
            raw_keywords = response.split(',')
        keywords = [k.strip() for k in raw_keywords if k.strip()]
        updated["keywords"] = keywords[:6]  # Max 6
    
    elif field == "tutorial_prerequisites":
        # Support semicolon-separated prerequisites
        if ';' in response:
            prerequisites_list = [item.strip() for item in response.split(';') if item.strip()]
            # Join with semicolon and space for readability
            updated["tutorial_prerequisites"] = "; ".join(prerequisites_list)
        else:
            # Single prerequisite or comma-separated
            updated["tutorial_prerequisites"] = response.strip()
    
    elif field == "recommended_no_of_tutorials":
        # Extract number
        numbers = re.findall(r'\d+', response)
        if numbers:
            updated["recommended_no_of_tutorials"] = int(numbers[0])
    
    elif field == "tutorial_rows":
        # This is handled separately in the tutorial collection logic
        pass
    
    else:
        # Simple string field
        updated[field] = response.strip()
    
    return updated

