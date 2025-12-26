"""Field extraction logic for outline chat."""
import json
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

from .outline_chat_field_extraction import (
    extract_field_from_response,
    extract_json_block,
    should_ask_confirmation,
    transform_menu_instructions,
)
from .outline_chat_llm_utils import generate_llm_text
from .outline_chat_models import ChatMessage
from .outline_chat_question_flow import get_question_flow


def validate_title(title: str) -> Tuple[bool, Optional[str]]:
    """
    Validate title for outline_name or tutorial_title.
    Returns: (is_valid, error_message)
    """
    if not title or not title.strip():
        return False, "Title cannot be empty."
    
    cleaned = title.strip()
    
    # Check length
    if len(cleaned) > 50:
        return False, f"The title has {len(cleaned)} characters, but it must be 50 characters or less. Please provide a shorter title."
    
    # Check for special characters (only letters, numbers, and spaces allowed)
    if not re.match(r'^[A-Za-z0-9 ]+$', cleaned):
        invalid_chars = set(re.findall(r'[^A-Za-z0-9 ]', cleaned))
        return False, f"The title contains special characters ({', '.join(sorted(invalid_chars))}). Only letters, numbers, and spaces are allowed. Please provide a title without special characters."
    
    return True, None


def build_extraction_prompt(
    phase: str,
    field: str,
    user_response: str,
    outline_type: str,
    outline_data: Dict,
) -> Optional[str]:
    """Build the extraction prompt for a given field."""
    question_flow = get_question_flow(outline_type)
    
    if phase == "warmup":
        for q in question_flow["warmup"]["questions"]:
            if q["field"] == field:
                if field in ["course_objectives", "topics_included", "topics_not_included"]:
                    return f"""Extract {field} from the user's response. Return as a JSON array of strings.

User response: {user_response}
Field: {field}
Return format: ["item1", "item2", "item3"]"""
                else:
                    return f"""Extract the {field} from the user's response. Return only the extracted value as a simple string (no JSON, no explanation).

User response: {user_response}
Field to extract: {field}
Expected format: {q.get('why', 'text string')}"""
    
    elif phase == "outcomes":
        for q in question_flow["outcomes"]["questions"]:
            if q["field"] == field:
                if field in ["course_objectives", "topics_included", "topics_not_included"]:
                    return f"""Extract {field} from the user's response. Return as a JSON array of strings.

User response: {user_response}
Field: {field}
Return format: ["item1", "item2", "item3"]"""
                else:
                    return f"""Extract {field} from the user's response. Return only the value."""
    
    elif phase == "examples":
        for q in question_flow["examples"]["questions"]:
            if q["field"] == field:
                if field == "allied_examples":
                    return f"""Extract allied examples from the user's response. Return as JSON array. If user says 'no' or 'none', return empty array [].

User response: {user_response}
Return format: ["example1", "example2"] or []"""
                else:
                    if outline_type == "ICT":
                        return f"""Extract the core teaching scenario, use case, or practical application from the user's response for an ICT course.

This should be a consistent example that demonstrates concepts across multiple tutorials.
Examples: 'Teaching symmetry with AI drawing tools', 'Data collection for student projects', 'Creating lesson plans with AI assistance'

User response: {user_response}
Return only the scenario description as a string (teaching scenario, use case, or practical application)."""
                    else:
                        return f"""Extract the core example from the user's response. Return the full example description as a string.

User response: {user_response}
Return the complete example description exactly as the user described it."""
    
    elif phase == "structure":
        if field == "recommended_no_of_tutorials":
            return f"""Extract the number of tutorials from the user's response. Return only the number as an integer.

User response: {user_response}
Example: "5" should return 5, "eight" should return 8"""
        elif field == "tutorial_title":
            return f"""Extract the tutorial title from the user's response. Return only the title as a string.

User response: {user_response}"""
        elif field == "tutorial_prerequisites":
            return f"""Extract the prerequisites from the user's response. Return as a string describing what learners need before this tutorial (e.g., "Completion of Tutorial #1" or specific skills). If multiple prerequisites are provided, separate them with semicolons (e.g., "Tutorial #1; Basic Python knowledge; Computer skills").

User response: {user_response}"""
        elif field == "tutorial_steps":
            if outline_type == "ICT":
                return f"""Extract practical steps, activities, or methodologies from the user's response for an ICT course tutorial.

ICT tutorial steps should focus on:
- Teaching methodologies (what learners will teach/guide)
- Skill-building activities (what learners will practice)
- Integration strategies (how learners will combine tools/concepts)
- Practical applications (what learners will create/apply)

User response: {user_response}
Return format: ["step1", "step2", "step3"]
Each step should be actionable and focused on skills, teaching methods, or practical applications."""
            else:
                return f"""Extract demonstrable steps from the user's response. Transform any menu instructions (like "File → Open") into action descriptions. Return as JSON array of strings.

User response: {user_response}
Return format: ["step1", "step2", "step3"]
Example transformation: "File → Open" becomes "Click File, then Open. In the dialog, choose your file and click Open." """
        elif field == "tutorial_time":
            return f"""Extract the estimated time in MINUTES from the user's response. The user may provide a single number or a range (e.g., "3-4", "3 to 4", "3-4 minutes"). If a range is provided, extract both numbers.

User response: {user_response}
Examples:
- "2 minutes" -> return "2" (single value)
- "around 4 min" -> return "4" (single value)
- "5" -> return "5" (single value)
- "3-4" -> return "3-4" (range)
- "3 to 4 minutes" -> return "3-4" (range)
- "4-5 min" -> return "4-5" (range)
Return the time as a string: single number like "5" or range like "3-4"."""
        elif field == "tutorial_comments":
            return f"""Extract any comments or notes from the user's response. Return as a string.

User response: {user_response}"""
    
    elif phase == "metadata":
        if field == "prepared_by":
            return f"""Extract the name of the person who prepared the outline. Return only the name.

User response: {user_response}"""
        elif field == "date":
            return f"""Extract the date from the user's response. Return in YYYY-MM-DD format. If user says "today" or doesn't specify, use {datetime.now().strftime('%Y-%m-%d')}.

User response: {user_response}"""
        elif field == "keywords":
            return f"""Extract keywords from the user's response. Return as JSON array of strings (3-6 keywords).

User response: {user_response}
Return format: ["keyword1", "keyword2", "keyword3"]"""
    
    return None


def determine_current_field(phase: str, outline_data: Dict, outline_type: str) -> Optional[Tuple[str, Dict]]:
    """Determine which field we're currently collecting and create tutorial row if needed."""
    question_flow = get_question_flow(outline_type)
    
    if phase == "warmup":
        for q in question_flow["warmup"]["questions"]:
            if not outline_data.get(q["field"]):
                return q["field"], {}
    
    elif phase == "outcomes":
        for q in question_flow["outcomes"]["questions"]:
            if not outline_data.get(q["field"]):
                return q["field"], {}
    
    elif phase == "examples":
        for q in question_flow["examples"]["questions"]:
            field = q["field"]
            if field == "allied_examples":
                if "allied_examples" not in outline_data:
                    return field, {}
            else:
                field_value = outline_data.get(field)
                if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                    return field, {}
    
    elif phase == "structure":
        if not outline_data.get("recommended_no_of_tutorials"):
            return "recommended_no_of_tutorials", {}
        
        num_tutorials = outline_data.get("recommended_no_of_tutorials", 0)
        tutorial_rows = outline_data.get("tutorial_rows", [])
        
        if not tutorial_rows:
            outline_data["tutorial_rows"] = []
        
        # Check if we need to create a new tutorial row
        if len(tutorial_rows) < num_tutorials:
            if not tutorial_rows or (tutorial_rows and 
                                    tutorial_rows[-1].get("title") and 
                                    tutorial_rows[-1].get("prerequisites") and
                                    tutorial_rows[-1].get("topics_details") and 
                                    len(tutorial_rows[-1].get("topics_details", [])) >= 2 and
                                    tutorial_rows[-1].get("time_seconds")):
                tutorial_rows.append({
                    "tutorial_number": len(tutorial_rows) + 1,
                    "title": "",
                    "prerequisites": [],
                    "topics_details": [],
                    "time_seconds": 0,
                    "comments": ""
                })
                outline_data["tutorial_rows"] = tutorial_rows
        
        if tutorial_rows:
            last_tutorial = tutorial_rows[-1]
            if not last_tutorial.get("title"):
                return "tutorial_title", {}
            elif not last_tutorial.get("prerequisites") or (isinstance(last_tutorial.get("prerequisites"), list) and len(last_tutorial.get("prerequisites", [])) == 0) or (isinstance(last_tutorial.get("prerequisites"), str) and last_tutorial.get("prerequisites", "").strip() == ""):
                return "tutorial_prerequisites", {}
            elif not last_tutorial.get("topics_details") or len(last_tutorial.get("topics_details", [])) < 2:
                return "tutorial_steps", {}
            elif not last_tutorial.get("time_seconds") or last_tutorial.get("time_seconds") == 0:
                return "tutorial_time", {}
            else:
                return "tutorial_comments", {}
    
    elif phase == "metadata":
        if not outline_data.get("prepared_by"):
            return "prepared_by", {}
        elif not outline_data.get("date"):
            return "date", {}
        elif not outline_data.get("keywords"):
            return "keywords", {}
    
    return None, {}


def extract_and_set_field_value(
    field: str,
    extracted_text: str,
    user_response: str,
    outline_data: Dict,
    outline_type: str,
) -> Tuple[Optional[any], str, bool]:
    """
    Extract and set field value from extracted text.
    Returns: (extracted_value, field_display, needs_confirmation)
    """
    field_display = field.replace("_", " ").title()
    
    # Clean up extracted text
    if "could not extract" in extracted_text.lower() or "not a" in extracted_text.lower() or "does not specify" in extracted_text.lower() or "not a title" in extracted_text.lower():
        extracted_text = user_response.strip()
    
    if field == "outline_type":
        extracted_type = extracted_text.strip().upper()
        if extracted_type in ["FOSS", "ICT", "OTHER"]:
            outline_data["outline_type"] = extracted_type
        elif "foss" in extracted_text.lower() or "free" in extracted_text.lower() or "open" in extracted_text.lower():
            outline_data["outline_type"] = "FOSS"
        elif "ict" in extracted_text.lower() or "digital" in extracted_text.lower() or "skill" in extracted_text.lower():
            outline_data["outline_type"] = "ICT"
        elif "other" in extracted_text.lower():
            outline_data["outline_type"] = "OTHER"
        else:
            outline_data["outline_type"] = "FOSS"
        return None, field_display, False
    
    elif field == "outline_name":
        extracted_value = user_response.strip()
        field_display = "Outline Name"
        needs_confirmation = should_ask_confirmation(field, extracted_value, user_response)
        if not needs_confirmation:
            outline_data["outline_name"] = extracted_value
        return extracted_value, field_display, needs_confirmation
    
    elif field == "recommended_no_of_tutorials":
        numbers = re.findall(r'\d+', extracted_text)
        if numbers:
            outline_data["recommended_no_of_tutorials"] = int(numbers[0])
        else:
            numbers = re.findall(r'\d+', user_response)
            if numbers:
                outline_data["recommended_no_of_tutorials"] = int(numbers[0])
        return None, field_display, False
    
    elif field == "tutorial_title":
        extracted_value = extracted_text.strip('"\'')
        field_display = "Tutorial Title"
        needs_confirmation = should_ask_confirmation(field, extracted_value, user_response)
        if not needs_confirmation:
            tutorial_rows = outline_data.get("tutorial_rows", [])
            if tutorial_rows:
                tutorial_rows[-1]["title"] = extracted_value
        return extracted_value, field_display, needs_confirmation
    
    elif field == "tutorial_prerequisites":
        extracted_value = extracted_text.strip('"\'')
        # Support semicolon-separated prerequisites - store as list
        if ';' in extracted_value:
            prerequisites_list = [item.strip() for item in extracted_value.split(';') if item.strip()]
        elif ',' in extracted_value:
            # Also support comma-separated
            prerequisites_list = [item.strip() for item in extracted_value.split(',') if item.strip()]
        else:
            # Single prerequisite
            prerequisites_list = [extracted_value] if extracted_value.strip() else []
        
        field_display = "Prerequisites"
        # For confirmation, join with semicolon for display
        extracted_value_display = "; ".join(prerequisites_list) if prerequisites_list else ""
        needs_confirmation = should_ask_confirmation(field, extracted_value_display, user_response)
        if not needs_confirmation:
            tutorial_rows = outline_data.get("tutorial_rows", [])
            if tutorial_rows:
                tutorial_rows[-1]["prerequisites"] = prerequisites_list
        return extracted_value_display, field_display, needs_confirmation
    
    elif field == "tutorial_steps":
        tutorial_rows = outline_data.get("tutorial_rows", [])
        try:
            steps = json.loads(extract_json_block(extracted_text))
        except:
            steps = re.findall(r'[•\-\d+\.]\s*(.+?)(?:\n|$)', user_response, re.MULTILINE)
            if not steps:
                if ';' in user_response:
                    steps = [item.strip() for item in user_response.split(';') if item.strip()]
                elif ',' in user_response:
                    steps = [item.strip() for item in user_response.split(',') if item.strip()]
                else:
                    steps = [line.strip() for line in user_response.split('\n') if line.strip()]
        
        if outline_type == "FOSS":
            steps = [transform_menu_instructions(s) for s in steps if s.strip()]
        else:
            steps = [s.strip() for s in steps if s.strip()]
        
        extracted_value = steps
        field_display = "Tutorial Steps"
        needs_confirmation = should_ask_confirmation(field, extracted_value, user_response)
        if not needs_confirmation:
            if tutorial_rows:
                tutorial_rows[-1]["topics_details"] = extracted_value
        return extracted_value, field_display, needs_confirmation
    
    elif field == "tutorial_time":
        # Extract time range or single value
        # Patterns: "3-4", "3 to 4", "3-4 minutes", "3 to 4 min", etc.
        range_pattern = r'(\d+)\s*[-–—to]\s*(\d+)'
        
        # First try extracted text
        range_match = re.search(range_pattern, extracted_text, re.IGNORECASE)
        if range_match:
            min_minutes = int(range_match.group(1))
            max_minutes = int(range_match.group(2))
        else:
            # Try user response
            range_match = re.search(range_pattern, user_response, re.IGNORECASE)
            if range_match:
                min_minutes = int(range_match.group(1))
                max_minutes = int(range_match.group(2))
            else:
                # Single value - extract from extracted_text first, then user_response
                numbers = re.findall(r'\d+', extracted_text)
                if numbers:
                    min_minutes = int(numbers[0])
                    max_minutes = int(numbers[0])  # Same value for single number
                else:
                    numbers = re.findall(r'\d+', user_response)
                    if numbers:
                        min_minutes = int(numbers[0])
                        max_minutes = int(numbers[0])
                    else:
                        return 0, "Time (minutes)", False  # Will trigger error response
        
        # Validate range
        if min_minutes < 1 or min_minutes > 30 or max_minutes < 1 or max_minutes > 30:
            return 0, "Time (minutes)", False  # Will trigger error response
        
        if min_minutes > max_minutes:
            # Swap if reversed
            min_minutes, max_minutes = max_minutes, min_minutes
        
        # Store as dict with min_seconds and max_seconds
        time_range = {
            "min_seconds": min_minutes * 60,
            "max_seconds": max_minutes * 60
        }
        
        # For backward compatibility, also store time_seconds as min_seconds
        extracted_value = time_range["min_seconds"]
        field_display = f"Time ({min_minutes}-{max_minutes} minutes)" if min_minutes != max_minutes else f"Time ({min_minutes} minutes)"
        needs_confirmation = should_ask_confirmation(field, extracted_value, user_response)
        if not needs_confirmation:
            tutorial_rows = outline_data.get("tutorial_rows", [])
            if tutorial_rows:
                tutorial_rows[-1]["time_seconds"] = extracted_value
                tutorial_rows[-1]["time_range"] = time_range  # Store range
        return extracted_value, field_display, needs_confirmation
    
    elif field == "tutorial_comments":
        extracted_value = extracted_text.strip('"\'')
        field_display = "Comments"
        needs_confirmation = should_ask_confirmation(field, extracted_value, user_response)
        if not needs_confirmation:
            tutorial_rows = outline_data.get("tutorial_rows", [])
            if tutorial_rows:
                tutorial_rows[-1]["comments"] = extracted_value
        return extracted_value, field_display, needs_confirmation
    
    elif field in ["course_objectives", "topics_included", "topics_not_included", "allied_examples", "keywords"]:
        try:
            extracted_value = json.loads(extract_json_block(extracted_text))
        except:
            outline_data = extract_field_from_response(field, user_response, outline_data)
            extracted_value = outline_data.get(field)
        
        field_display = field.replace("_", " ").title()
        needs_confirmation = should_ask_confirmation(field, extracted_value, user_response)
        if not needs_confirmation:
            outline_data[field] = extracted_value
        return extracted_value, field_display, needs_confirmation
    
    else:
        # For core_example and other text fields
        extracted_value = extracted_text.strip('"\'')
        if not extracted_value or len(extracted_value) < 3:
            if field == "core_example" and user_response:
                extracted_value = user_response.strip()
            elif "could not extract" in extracted_text.lower() or "not a" in extracted_text.lower():
                extracted_value = user_response.strip()
        
        field_display = field.replace("_", " ").title()
        needs_confirmation = should_ask_confirmation(field, extracted_value, user_response)
        if not needs_confirmation:
            outline_data[field] = extracted_value
        return extracted_value, field_display, needs_confirmation

