"""Edit processing logic for outline chat - allows editing previous answers."""
import re
from typing import Dict, Optional, Tuple

from fastapi.responses import JSONResponse

from .outline_chat_extraction import (
    determine_current_field,
    extract_and_set_field_value,
    validate_title,
)
from .outline_chat_field_extraction import extract_field_from_response, should_ask_confirmation
from .outline_chat_llm_utils import friendly_rewrite_question, get_example_answer_hint
from .outline_chat_question_flow import determine_next_question, get_question_flow
from .outline_chat_session import save_session


def process_field_edit(
    field_name: str,
    new_value: str,
    outline_data: Dict,
    phase: str,
    project_id: int,
    conversation: list,
    tutorial_number: Optional[int] = None,
) -> Tuple[Dict, str, Optional[JSONResponse]]:
    """
    Process editing a field value.
    Returns: (outline_data, phase, error_response)
    """
    outline_type = outline_data.get("outline_type", "FOSS").upper()
    
    # Handle tutorial-specific fields
    tutorial_fields = ["tutorial_title", "tutorial_prerequisites", "tutorial_steps", "tutorial_time", "tutorial_comments"]
    
    if field_name in tutorial_fields:
        tutorial_rows = outline_data.get("tutorial_rows", [])
        if tutorial_number is None:
            # Default to last tutorial if not specified
            if tutorial_rows:
                tutorial_number = len(tutorial_rows)
            else:
                return outline_data, phase, JSONResponse({
                    "error": "No tutorials available to edit",
                    "status_code": 400
                }, status_code=400)
        
        # Ensure tutorial_rows exists and has the tutorial
        if tutorial_number > len(tutorial_rows):
            return outline_data, phase, JSONResponse({
                "error": f"Tutorial #{tutorial_number} does not exist",
                "status_code": 400
            }, status_code=400)
        
        # Create tutorial row if it doesn't exist
        while len(tutorial_rows) < tutorial_number:
            tutorial_rows.append({
                "tutorial_number": len(tutorial_rows) + 1,
                "title": "",
                "prerequisites": [],
                "topics_details": [],
                "time_seconds": 0,
                "comments": ""
            })
        
        # Get the tutorial to edit (index is tutorial_number - 1)
        tutorial_index = tutorial_number - 1
        if tutorial_index < 0:
            tutorial_index = 0
        
        # Temporarily set the last tutorial to the one we're editing
        original_last = tutorial_rows[-1] if tutorial_rows else None
        if tutorial_index < len(tutorial_rows):
            # Temporarily move the tutorial to edit to the end for processing
            tutorial_to_edit = tutorial_rows[tutorial_index]
            if tutorial_index != len(tutorial_rows) - 1:
                tutorial_rows[tutorial_index] = tutorial_rows[-1]
                tutorial_rows[-1] = tutorial_to_edit
        
        # Process the field edit
        try:
            extracted_value, field_display, needs_confirmation = extract_and_set_field_value(
                field_name, new_value, new_value, outline_data, outline_type
            )
            
            # Restore tutorial order if we swapped
            if tutorial_index < len(tutorial_rows) - 1 and original_last:
                tutorial_rows[-1], tutorial_rows[tutorial_index] = tutorial_rows[tutorial_index], tutorial_rows[-1]
            
            # Update the correct tutorial
            if tutorial_index < len(tutorial_rows):
                if field_name == "tutorial_title":
                    tutorial_rows[tutorial_index]["title"] = extracted_value
                elif field_name == "tutorial_prerequisites":
                    tutorial_rows[tutorial_index]["prerequisites"] = extracted_value if isinstance(extracted_value, list) else [extracted_value]
                elif field_name == "tutorial_steps":
                    tutorial_rows[tutorial_index]["topics_details"] = extracted_value if isinstance(extracted_value, list) else [extracted_value]
                elif field_name == "tutorial_time":
                    tutorial_rows[tutorial_index]["time_seconds"] = extracted_value
                elif field_name == "tutorial_comments":
                    tutorial_rows[tutorial_index]["comments"] = extracted_value
            
            outline_data["tutorial_rows"] = tutorial_rows
            
            # Validate title if needed
            if field_name == "tutorial_title" and isinstance(extracted_value, str):
                is_valid, error_msg = validate_title(extracted_value)
                if not is_valid:
                    return outline_data, phase, JSONResponse({
                        "error": error_msg,
                        "field": field_name,
                        "status_code": 400
                    }, status_code=400)
        
        except Exception as e:
            return outline_data, phase, JSONResponse({
                "error": f"Failed to process edit: {str(e)}",
                "status_code": 500
            }, status_code=500)
    
    # Handle list fields
    elif field_name in ["course_objectives", "topics_included", "topics_not_included", "allied_examples", "keywords"]:
        outline_data = extract_field_from_response(field_name, new_value, outline_data)
    
    # Handle special fields
    elif field_name == "recommended_no_of_tutorials":
        numbers = re.findall(r'\d+', new_value)
        if numbers:
            new_count = int(numbers[0])
            old_count = outline_data.get("recommended_no_of_tutorials", 0)
            outline_data["recommended_no_of_tutorials"] = new_count
            
            # Adjust tutorial_rows if count changed
            tutorial_rows = outline_data.get("tutorial_rows", [])
            if new_count < old_count:
                # Remove excess tutorials
                outline_data["tutorial_rows"] = tutorial_rows[:new_count]
            elif new_count > old_count:
                # Add empty tutorials if needed
                for i in range(old_count, new_count):
                    tutorial_rows.append({
                        "tutorial_number": i + 1,
                        "title": "",
                        "prerequisites": [],
                        "topics_details": [],
                        "time_seconds": 0,
                        "comments": ""
                    })
                outline_data["tutorial_rows"] = tutorial_rows
    
    elif field_name == "outline_type":
        user_lower = new_value.lower()
        if "foss" in user_lower or "free" in user_lower or "open" in user_lower:
            outline_data["outline_type"] = "FOSS"
        elif "ict" in user_lower or "digital" in user_lower or "skill" in user_lower:
            outline_data["outline_type"] = "ICT"
        elif "other" in user_lower:
            outline_data["outline_type"] = "OTHER"
        else:
            outline_data["outline_type"] = "FOSS"
    
    # Handle regular text fields
    else:
        # Use extract_and_set_field_value for consistency
        try:
            extracted_value, field_display, needs_confirmation = extract_and_set_field_value(
                field_name, new_value, new_value, outline_data, outline_type
            )
            
            # Validate title if needed
            if field_name == "outline_name" and isinstance(extracted_value, str):
                is_valid, error_msg = validate_title(extracted_value)
                if not is_valid:
                    return outline_data, phase, JSONResponse({
                        "error": error_msg,
                        "field": field_name,
                        "status_code": 400
                    }, status_code=400)
            
            # Store the value (extract_and_set_field_value may have already stored it)
            if not needs_confirmation:
                outline_data[field_name] = extracted_value
        
        except Exception as e:
            return outline_data, phase, JSONResponse({
                "error": f"Failed to process edit: {str(e)}",
                "status_code": 500
            }, status_code=500)
    
    # Recalculate phase and next question after edit
    # We need to determine what the current phase should be based on the updated data
    new_phase, next_question = determine_next_question(outline_data, phase, conversation)
    
    # Save the updated session
    save_session(project_id, outline_data, new_phase, None)
    
    return outline_data, new_phase, None
