"""Interactive Course Outline chat route for Spoken Tutorials.

This module implements a comprehensive chatbot flow to capture SME input
and convert it into a Spoken Tutorial Course Outline following pedagogy rules.
"""
import json
import os
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from .outline_chat_field_extraction import extract_json_block
from .outline_chat_handlers import (
    handle_approval,
    handle_confirmation_no,
    handle_confirmation_yes,
)
from .outline_chat_llm_utils import (
    friendly_rewrite_question,
    generate_llm_text,
    get_example_answer_hint,
)
from .outline_chat_models import (
    ChatMessage,
    OutlineChatRequest,
    GeneralChatRequest,
)
from .outline_chat_edit import process_field_edit
from .outline_chat_processing import (
    handle_review_phase,
    process_user_input,
)
from .outline_chat_question_flow import determine_next_question, get_question_flow
from .outline_chat_responses import build_confirmation_response
from .outline_chat_session import (
    load_session,
    save_session,
)
from .outline_chat_validation import validate_outline

router = APIRouter(tags=["outline_chat"])


# All models, utility functions, and helpers have been moved to separate modules
# See imports above for the new module structure


@router.post("/outline_chat")
async def outline_chat(request: OutlineChatRequest):
    """Chat endpoint that guides SME through Course Outline creation."""
    try:
        if not request.conversation:
            raise HTTPException(status_code=400, detail="Conversation history is required")
        
        project_id = request.project_id or int(time.time())
        outline_data, phase, pending_confirmation = load_session(project_id, request.phase or "warmup")
        
        # Initialize variables
        assistant_message = None
        next_question = None
        
        # Check for approval command
        last_message = request.conversation[-1] if request.conversation else None
        user_content = last_message.content.lower().strip() if last_message and last_message.role == "user" else ""
        
        # Handle confirmation responses (yes/no)
        if pending_confirmation and user_content in ["yes", "no", "y", "n"]:
            if user_content in ["yes", "y"]:
                handle_confirmation_yes(pending_confirmation, outline_data, project_id)
                pending_confirmation = None
                save_session(project_id, outline_data, phase, None)
                
                # Continue to next question
                phase, next_question = determine_next_question(outline_data, phase, request.conversation)
                outline_type = outline_data.get("outline_type", "FOSS").upper()
                if next_question:
                    rewritten = friendly_rewrite_question(next_question, outline_type, phase)
                    example_hint = get_example_answer_hint(outline_type, phase, next_question)
                    assistant_message = f"{rewritten}\n\nExample answer: {example_hint}" if example_hint else rewritten
                else:
                    assistant_message = "Thank you! All information collected."
                
                return JSONResponse({
                    "project_id": project_id,
                    "assistant_message": assistant_message,
                    "follow_up_question": next_question if phase != "review" else None,
                    "phase": phase,
                    "outline_data": outline_data,
                    "validation_errors": [],
                    "pedagogy_compliance": {},
                    "is_draft_ready": phase == "review",
                    "is_approved": False,
                    "needs_confirmation": False
                })
            else:  # no or n
                phase, next_question = handle_confirmation_no(pending_confirmation, outline_data, phase, request.conversation)
                pending_confirmation = None
                save_session(project_id, outline_data, phase, None)
                
                outline_type = outline_data.get("outline_type", "FOSS").upper()
                if next_question:
                    rewritten = friendly_rewrite_question(next_question, outline_type, phase)
                    example_hint = get_example_answer_hint(outline_type, phase, next_question)
                    assistant_message = f"{rewritten}\n\nExample answer: {example_hint}" if example_hint else rewritten
                else:
                    assistant_message = "Thank you! All information collected."
                
                return JSONResponse({
                    "project_id": project_id,
                    "assistant_message": assistant_message,
                    "follow_up_question": next_question if phase != "review" else None,
                    "phase": phase,
                    "outline_data": outline_data,
                    "validation_errors": [],
                    "pedagogy_compliance": {},
                    "is_draft_ready": phase == "review",
                    "is_approved": False,
                    "needs_confirmation": False
                })
        
        if user_content == "approve" and phase == "review":
            phase, assistant_message = handle_approval(outline_data, phase)
            save_session(project_id, outline_data, phase, None)
                
            return JSONResponse({
                "project_id": project_id,
                "assistant_message": assistant_message,
                "phase": phase,
                "outline_data": outline_data,
                "is_approved": True,
                "is_draft_ready": True
            })
        
        # Track which field was answered (for frontend to store with message)
        answered_field = None
        
        # Process the conversation - extract information from last user message
        if last_message and last_message.role == "user" and user_content and user_content != "approve":
            # Determine which field we're collecting before processing
            outline_type = outline_data.get("outline_type", "FOSS").upper()
            from .outline_chat_extraction import determine_current_field
            answered_field, _ = determine_current_field(phase, outline_data, outline_type)
            
            # Process user input using the extraction module
            outline_data, phase, pending_confirmation, early_response = process_user_input(
                last_message, outline_data, phase, project_id, request.conversation
            )
            
            if early_response:
                # Add answered_field to early_response if it's a JSONResponse
                if isinstance(early_response, JSONResponse):
                    response_body = json.loads(early_response.body.decode())
                    response_body["answered_field"] = answered_field
                    return JSONResponse(response_body)
                return early_response
            
            if pending_confirmation:
                confirmation_response = build_confirmation_response(project_id, pending_confirmation, outline_data, phase)
                confirmation_response["answered_field"] = answered_field
                return JSONResponse(confirmation_response)
        
        # Handle review phase
        if phase == "review":
            phase, review_message = handle_review_phase(outline_data, phase, last_message, user_content)
            if review_message:
                assistant_message = review_message
        
        # Determine next question if we don't have a message yet
        if not assistant_message:
            phase, next_question = determine_next_question(outline_data, phase, request.conversation)
            
            if next_question:
                # Rewrite the base question in a slightly friendlier tone using LLM,
                # and include a concrete example answer where possible.
                outline_type = outline_data.get("outline_type", "FOSS").upper()
                rewritten = friendly_rewrite_question(next_question, outline_type, phase)
                example_hint = get_example_answer_hint(outline_type, phase, next_question)
                if example_hint:
                    assistant_message = f"{rewritten}\n\nExample answer: {example_hint}"
                else:
                    assistant_message = rewritten
            else:
                assistant_message = "Thank you! All information collected."
        
        # Save session
        save_session(project_id, outline_data, phase, pending_confirmation)
        
        # Run validation if we have enough data
        validation_errors = []
        pedagogy_compliance = {}
        if phase in ["review", "approved"]:
            validation_errors, pedagogy_compliance = validate_outline(outline_data)
        
        return JSONResponse({
            "project_id": project_id,
            "assistant_message": assistant_message,
            "follow_up_question": next_question if phase != "review" else None,
            "phase": phase,
            "outline_data": outline_data,
            "validation_errors": validation_errors,
            "pedagogy_compliance": pedagogy_compliance,
            "is_draft_ready": phase == "review",
            "is_approved": phase == "approved",
            "needs_confirmation": pending_confirmation is not None,
            "confirmation_field": pending_confirmation.get("field") if pending_confirmation else None,
            "confirmation_value": str(pending_confirmation.get("value", "")) if pending_confirmation else None,
            "answered_field": answered_field  # Field that was just answered
        })
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.options("/outline_chat")
async def outline_chat_options():
    """Handle CORS preflight for the outline chat endpoint.

    Some deployments were returning 405 for OPTIONS when middleware
    configuration was bypassed. This explicit handler ensures a 200
    with permissive CORS headers so browsers can proceed.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/outline_chat/{project_id}/export")
async def export_outline(project_id: int, format: str = "json"):
    """Export the finalized outline in JSON or PDF-ready format."""
    project_root = Path(__file__).parent.parent.parent
    session_dir = project_root / "output" / "outline_sessions"
    session_path = session_dir / f"outline_{project_id}.json"
    
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Outline not found")
    
    with open(session_path, "r") as f:
        session_data = json.load(f)
        outline_data = session_data.get("outline_data", {})
    
    if format == "json":
        # Return machine-readable JSON
        return JSONResponse({
            "outline_name": outline_data.get("outline_name"),
            "foss_version": outline_data.get("foss_version", "Not Applicable"),
            "target_audience": outline_data.get("target_audience"),
            "entry_behaviour": outline_data.get("entry_behaviour"),
            "purpose": outline_data.get("purpose"),
            "recommended_no_of_tutorials": outline_data.get("recommended_no_of_tutorials", 0),
            "prepared_by": outline_data.get("prepared_by"),
            "domain": outline_data.get("domain", ""),
            "reviewer": outline_data.get("reviewer", "IITB ST Team"),
            "date": outline_data.get("date"),
            "keywords": outline_data.get("keywords", []),
            "about_course": outline_data.get("about_course", ""),
            "course_objectives": outline_data.get("course_objectives", []),
            "topics_included": outline_data.get("topics_included", []),
            "topics_not_included": outline_data.get("topics_not_included", []),
            "core_example": outline_data.get("core_example"),
            "allied_examples": outline_data.get("allied_examples", []),
            "tutorial_rows": outline_data.get("tutorial_rows", [])
        })
    elif format == "pdf":
        # Generate PDF matching the ST Course Outline template
        from src.services.outline_pdf_service import create_outline_pdf
        import os
        
        pdf_path = create_outline_pdf(outline_data)
        pdf_filename = os.path.basename(pdf_path)
        
        return JSONResponse({
            "pdf_url": f"/static/{pdf_filename}",
            "pdf_path": pdf_path,
            "message": "PDF generated successfully"
        })
    elif format == "docx":
        # Generate DOCX matching the ST Course Outline template
        from src.services.outline_docx_service import create_outline_docx
        import os
        
        docx_path = create_outline_docx(outline_data)
        docx_filename = os.path.basename(docx_path)
        
        return JSONResponse({
            "docx_url": f"/static/{docx_filename}",
            "docx_path": docx_path,
            "message": "DOCX generated successfully"
        })
    else:
        raise HTTPException(status_code=400, detail="Format must be 'json', 'pdf', or 'docx'")


@router.post("/outline_chat/{project_id}/edit")
async def edit_outline_field(project_id: int, request: dict):
    """Edit a specific field in the outline data.
    
    Request body:
    {
        "field_name": "outline_name",
        "new_value": "New Course Name",
        "tutorial_number": 1  # Optional, for tutorial fields
    }
    """
    try:
        field_name = request.get("field_name")
        new_value = request.get("new_value")
        tutorial_number = request.get("tutorial_number")
        
        if not field_name or new_value is None:
            raise HTTPException(status_code=400, detail="field_name and new_value are required")
        
        # Load current session
        outline_data, phase, pending_confirmation = load_session(project_id, "warmup")
        
        # Process the edit
        updated_outline_data, new_phase, error_response = process_field_edit(
            field_name=field_name,
            new_value=str(new_value),
            outline_data=outline_data,
            phase=phase,
            project_id=project_id,
            conversation=[],  # Empty conversation for edit endpoint
            tutorial_number=tutorial_number,
        )
        
        if error_response:
            return error_response
        
        # Determine next question after edit
        phase, next_question = determine_next_question(updated_outline_data, new_phase, [])
        
        # Build assistant message
        outline_type = updated_outline_data.get("outline_type", "FOSS").upper()
        field_display = field_name.replace("_", " ").title()
        
        # Format the value for display
        if isinstance(new_value, list):
            value_display = "; ".join(str(v) for v in new_value)
        else:
            value_display = str(new_value)
        
        assistant_message = f"✓ Updated **{field_display}** to: `{value_display}`\n\n"
        
        if next_question:
            from .outline_chat_llm_utils import friendly_rewrite_question, get_example_answer_hint
            rewritten = friendly_rewrite_question(next_question, outline_type, new_phase)
            example_hint = get_example_answer_hint(outline_type, new_phase, next_question)
            if example_hint:
                assistant_message += f"{rewritten}\n\nExample answer: {example_hint}"
            else:
                assistant_message += rewritten
        else:
            assistant_message += "All information collected. Reviewing outline..."
        
        return JSONResponse({
            "project_id": project_id,
            "assistant_message": assistant_message,
            "follow_up_question": next_question if new_phase != "review" else None,
            "phase": new_phase,
            "outline_data": updated_outline_data,
            "validation_errors": [],
            "pedagogy_compliance": {},
            "is_draft_ready": new_phase == "review",
            "is_approved": False,
            "needs_confirmation": False,
        })
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/general_chat")
async def general_chat(request: GeneralChatRequest):
    """General chat endpoint for asking any questions."""
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        
        from .outline_chat_llm_utils import generate_llm_text
        
        # Use a friendly system prompt for general questions
        system_prompt = "You are a helpful AI assistant. Answer questions clearly and concisely. Be friendly and professional."
        
        answer = generate_llm_text(
            question,
            temperature=0.7,
            max_tokens=1024,
            system_prompt=system_prompt,
        )
        
        return JSONResponse({
            "answer": answer,
            "question": question
        })
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outline_chat_stream")
async def outline_chat_stream(request: OutlineChatRequest):
    """Streaming version of outline chat - streams assistant response token by token."""
    
    async def generate():
        try:
            if not request.conversation:
                yield f"data: {json.dumps({'error': 'Conversation history is required'})}\n\n"
                return
            
            project_root = Path(__file__).parent.parent.parent
            session_dir = project_root / "output" / "outline_sessions"
            session_dir.mkdir(parents=True, exist_ok=True)
            
            project_id = request.project_id or int(time.time())
            session_path = session_dir / f"outline_{project_id}.json"
            
            # Load or initialize outline data
            if session_path.exists():
                with open(session_path, "r") as f:
                    session_data = json.load(f)
                    outline_data = session_data.get("outline_data", {})
                    phase = session_data.get("phase", "warmup")
            else:
                outline_data = {}
                phase = request.phase or "warmup"
            
            last_message = request.conversation[-1] if request.conversation else None
            user_content = last_message.content.lower().strip() if last_message and last_message.role == "user" else ""
            
            # Quick approval check
            if user_content == "approve" and phase == "review":
                phase = "approved"
                outline_data["status"] = "approved"
                outline_data["approved_at"] = datetime.now().isoformat()
                
                # Stream approval message
                approval_msg = "✅ Outline approved! Generating final outputs..."
                for char in approval_msg:
                    yield f"data: {json.dumps({'token': char})}\n\n"
                    await asyncio.sleep(0.02)
                
                # Save and send completion
                with open(session_path, "w") as f:
                    json.dump({"project_id": project_id, "outline_data": outline_data, "phase": phase, "updated_at": time.time()}, f, indent=2)
                
                yield f"data: {json.dumps({'done': True, 'project_id': project_id, 'phase': phase, 'outline_data': outline_data, 'is_approved': True})}\n\n"
                return
            
            # Process user input and extract information (non-streaming part)
            if last_message and last_message.role == "user" and user_content and user_content != "approve":
                # Use OpenAI for all LLM calls
                outline_type = outline_data.get("outline_type", "FOSS")
                question_flow = get_question_flow(outline_type)
                current_field = None
                extraction_prompt = ""
                
                # Determine field to extract based on phase (same logic as original)
                if phase == "warmup":
                    for q in question_flow["warmup"]["questions"]:
                        if not outline_data.get(q["field"]):
                            current_field = q["field"]
                            extraction_prompt = f"Extract the {q['field']} from: {last_message.content}. Return only the value."
                            break
                elif phase == "outcomes":
                    for q in question_flow["outcomes"]["questions"]:
                        if not outline_data.get(q["field"]):
                            current_field = q["field"]
                            if q["field"] in ["course_objectives", "topics_included", "topics_not_included"]:
                                extraction_prompt = f"Extract {q['field']} from: {last_message.content}. Return as JSON array."
                            break
                elif phase == "examples":
                    for q in question_flow["examples"]["questions"]:
                        if not outline_data.get(q["field"]):
                            current_field = q["field"]
                            extraction_prompt = f"Extract {q['field']} from: {last_message.content}. Return only the value."
                            break
                elif phase == "structure":
                    if not outline_data.get("recommended_no_of_tutorials"):
                        current_field = "recommended_no_of_tutorials"
                        numbers = re.findall(r'\d+', last_message.content)
                        if numbers:
                            outline_data["recommended_no_of_tutorials"] = int(numbers[0])
                
                # Extract field if needed using OpenAI
                if current_field and extraction_prompt:
                    try:
                        extracted = generate_llm_text(
                            extraction_prompt,
                            temperature=0.2,
                            max_tokens=512,
                            system_prompt="You are a helpful assistant that extracts information from user responses."
                        ).strip()
                        
                        if current_field == "recommended_no_of_tutorials":
                            numbers = re.findall(r'\d+', extracted)
                            if numbers:
                                outline_data["recommended_no_of_tutorials"] = int(numbers[0])
                        elif current_field in ["course_objectives", "topics_included", "topics_not_included", "allied_examples"]:
                            try:
                                outline_data[current_field] = json.loads(extract_json_block(extracted))
                            except:
                                outline_data[current_field] = [extracted]
                        else:
                            outline_data[current_field] = extracted.strip('"\'')
                    except:
                        # Fallback to simple extraction
                        outline_data[current_field] = last_message.content.strip()
            
            # Determine next question
            phase, next_question = determine_next_question(outline_data, phase, request.conversation)
            
            # Build assistant message
            assistant_message = ""
            compliance = {}  # Initialize compliance outside the if block
            errors = []
            
            if phase == "review" and not outline_data.get("draft_shown"):
                # Auto-generate "About the Course" if missing
                if not outline_data.get("about_course"):
                    outline_data["about_course"] = f"This course teaches {outline_data.get('tutorial_name', 'the subject')} to {outline_data.get('target_audience', 'learners')}."
                
                draft = generate_draft_outline(outline_data)
                outline_data["draft"] = draft
                outline_data["draft_shown"] = True
                errors, compliance = validate_outline(outline_data)
                
                assistant_message = f"Here's your draft Course Outline:\n\n{draft}\n\n"
                assistant_message += f"**Pedagogy Compliance:**\n"
                assistant_message += f"- Core Example: {'✓' if compliance['core_example'] else '✗'}\n"
                assistant_message += f"- Demo Content: {compliance['demo_percentage']:.1f}%\n"
                assistant_message += f"- Menu-free: {'✓' if compliance['menu_free'] else '⚠️'}\n\n"
                if errors:
                    assistant_message += "**Issues:**\n" + "\n".join(f"- {e}" for e in errors[:3]) + "\n\n"
                assistant_message += "Please review and suggest edits, or type 'approve' to finalize."
            
            elif next_question:
                assistant_message = next_question
            else:
                assistant_message = "Thank you! All information collected."
            
            # Stream the assistant message token by token
            for char in assistant_message:
                yield f"data: {json.dumps({'token': char})}\n\n"
                await asyncio.sleep(0.015)  # 15ms delay for typing effect
            
            # Save session
            with open(session_path, "w") as f:
                json.dump({"project_id": project_id, "outline_data": outline_data, "phase": phase, "updated_at": time.time()}, f, indent=2)
            
            # Send completion event with full data including pedagogy_compliance
            yield f"data: {json.dumps({'done': True, 'project_id': project_id, 'phase': phase, 'outline_data': outline_data, 'is_draft_ready': phase == 'review', 'is_approved': phase == 'approved', 'pedagogy_compliance': compliance})}\n\n"
        
        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

