"""
FastAPI routes for the Script Chat flow.
Uses Server-Sent Events (SSE) to stream LangGraph events to the frontend.

Event types sent to client:
  event: progress  — StreamWriter status updates (progress bar)
  event: token     — LLM token-by-token streaming (chat typing effect)
  event: interrupt  — HITL gate payload (review data + approve/edit buttons)
  event: state     — Node completion (stage transitions)
  event: error     — Error messages
  event: done      — Graph execution complete
"""
import json
import uuid
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from src.script_chat.graph import build_script_chat_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/script-chat", tags=["Script Chat"])

# We'll instantiate _graph dynamically once the async lifespan context yields the saver.
# Using a helper property so that other routes can import it.
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        raise RuntimeError("Graph is not initialized. Make sure server lifespan started.")
    return _graph

async def init_script_chat_graph():
    global _graph
    db_dir = Path(__file__).parent.parent.parent / "data"
    db_dir.mkdir(exist_ok=True)
    db_path = str(db_dir / "script_chat.db")
    
    # Instantiate AsyncSqliteSaver and compile graph
    context_manager = AsyncSqliteSaver.from_conn_string(db_path)
    # __aenter__() returns the actual checkpointer object
    saver = await context_manager.__aenter__()
    router.state_saver = context_manager
    _graph = build_script_chat_graph(checkpointer=saver)
    logger.info("✅ Script Chat graph initialized with AsyncSqliteSaver")

async def close_script_chat_graph():
    saver = getattr(router, "state_saver", None)
    if saver:
        await saver.__aexit__(None, None, None)
        logger.info("🔒 Script Chat AsyncSqliteSaver connection closed")


# ──────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────

class StartRequest(BaseModel):
    outline: str
    foss_name: Optional[str] = None

class StartResponse(BaseModel):
    thread_id: str
    message: str

class ResumeRequest(BaseModel):
    """Payload to resume from an interrupt.
    action: 'approve' | 'edit'
    instruction: (optional) edit instruction text
    edited_content: (optional) manually edited content
    edited_metadata: (optional) manually edited metadata
    """
    action: str
    instruction: Optional[str] = None
    edited_content: Optional[str] = None
    edited_metadata: Optional[dict] = None

class ManualEditRequest(BaseModel):
    """Direct manual edit to a slide (zero LLM tokens)."""
    slide_number: int
    field: str  # 'narration' or 'visual_cue'
    value: str

class RevertRequest(BaseModel):
    checkpoint_id: str

class JumpRequest(BaseModel):
    target_stage: str

# ──────────────────────────────────────────────
# SSE Streaming Helper
# ──────────────────────────────────────────────

def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def _stream_graph(config: dict, input_data=None):
    """
    Core SSE generator. Runs graph.astream() with multiple stream modes
    and maps LangGraph events to our SSE event types.
    
    Uses stream_mode=["custom", "updates"] which captures:
      - "custom": StreamWriter progress events from nodes
      - "updates": Node completion state updates
    """
    try:
        stream_input = input_data if input_data is not None else None
        graph = get_graph()
        
        async for mode, chunk in graph.astream(
            stream_input,
            config=config,
            stream_mode=["custom", "updates"]
        ):
            # ── Channel 1: Custom progress from StreamWriter ──
            if mode == "custom":
                yield _sse_event("progress", chunk)
            
            # ── Channel 4: Node completion updates ──
            elif mode == "updates":
                # chunk is a dict like {"node_name": {state_updates}}
                for node_name, updates in chunk.items():
                    if node_name == "__interrupt__":
                        continue  # We handle interrupts after the stream ends
                    yield _sse_event("state", {
                        "node": node_name,
                        "status": "completed"
                    })
        
        # After stream ends, check if we're at an interrupt
        state = await graph.aget_state(config)
        if getattr(state, 'tasks', None) and len(state.tasks) > 0:
            task = state.tasks[0]
            if hasattr(task, 'interrupts') and task.interrupts:
                interrupt_payload = task.interrupts[0].value
                yield _sse_event("interrupt", interrupt_payload)
            else:
                yield _sse_event("done", {
                    "stage": state.values.get("current_stage", "unknown")
                })
        else:
            yield _sse_event("done", {
                "stage": state.values.get("current_stage", "unknown")
            })
    
    except Exception as e:
        logger.error(f"SSE stream error: {e}", exc_info=True)
        yield _sse_event("error", {"message": str(e)})


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/start", response_model=StartResponse)
async def start_session(req: StartRequest):
    """Start a new script chat session.
    
    Returns a thread_id. Client should immediately connect to 
    GET /script-chat/stream/{thread_id} to receive SSE events.
    """
    thread_id = str(uuid.uuid4())
    
    # Store initial state in the checkpointer by running the graph
    config = {"configurable": {"thread_id": thread_id}}
    initial_input = {
        "raw_outline": req.outline,
        "foss_name": req.foss_name,
        "messages": [],
        "script_version": 0,
    }
    
    # Don't run the graph yet — just return the thread_id.
    # The client will connect to /stream/{thread_id} which triggers the run.
    # We store the initial input in a simple in-memory dict for now.
    _pending_inputs[thread_id] = initial_input
    
    return StartResponse(
        thread_id=thread_id,
        message="Session created. Connect to /script-chat/stream/{thread_id} to begin."
    )


# Simple in-memory store for pending inputs (thread_id -> initial input)
_pending_inputs: dict = {}


@router.get("/stream/{thread_id}")
async def stream_events(thread_id: str):
    """SSE endpoint. Streams LangGraph events for the given thread.
    
    On first connection (pending input exists): starts the graph from scratch.
    On subsequent connections: streams the current state (useful for reconnects).
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Check if this is a fresh start or a reconnect
    input_data = _pending_inputs.pop(thread_id, None)
    
    if input_data is None:
        graph = get_graph()
        state = await graph.aget_state(config)
        if state.values:
            # Check if genuinely paused at an interrupt
            is_interrupted = False
            if getattr(state, 'tasks', None) and len(state.tasks) > 0:
                task = state.tasks[0]
                if hasattr(task, 'interrupts') and task.interrupts:
                    is_interrupted = True
                    
            # If we have pending tasks to run and we are NOT interrupted, we must run the graph!
            if state.next and not is_interrupted:
                # Fall through to _stream_graph
                pass
            else:
                async def reconnect_stream():
                    if is_interrupted:
                        yield _sse_event("interrupt", state.tasks[0].interrupts[0].value)
                    else:
                        yield _sse_event("state", {
                            "stage": state.values.get("current_stage", "unknown"),
                            "script_version": state.values.get("script_version", 0)
                        })
                return StreamingResponse(
                    reconnect_stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    }
                )
    
    return StreamingResponse(
        _stream_graph(config, input_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/resume/{thread_id}")
async def resume_session(thread_id: str, req: ResumeRequest):
    """Resume from an interrupt (HITL gate).
    
    Returns an SSE stream of events as the graph continues executing.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Verify the graph is actually paused
    graph = get_graph()
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # In LangGraph, if state.next is not empty, the graph is interrupted and waiting for input
    if not state.next:
        tasks_debug = []
        if getattr(state, 'tasks', None):
            for t in state.tasks:
                tasks_debug.append({
                    "name": t.name,
                    "interrupts": [i.value for i in t.interrupts] if getattr(t, 'interrupts', None) else []
                })
        detail_msg = f"Graph is not paused at an interrupt. State next: {state.next}. Tasks: {tasks_debug}. Current stage: {state.values.get('current_stage')}"
        raise HTTPException(status_code=400, detail=detail_msg)
    
    # Build the resume payload
    resume_data = {"action": req.action}
    if req.instruction:
        resume_data["instruction"] = req.instruction
    if req.edited_content:
        resume_data["edited_content"] = req.edited_content
    if req.edited_metadata:
        resume_data["edited_metadata"] = req.edited_metadata
    
    return StreamingResponse(
        _stream_graph(config, Command(resume=resume_data)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.put("/edit/{thread_id}")
async def manual_edit(thread_id: str, req: ManualEditRequest):
    """Direct manual edit to a slide — zero LLM tokens (Approach B).
    
    Updates the script in the graph state directly without invoking the LLM.
    Only works when the graph is paused at a script_review interrupt.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    graph = get_graph()
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    script = state.values.get("script", [])
    if not script:
        raise HTTPException(status_code=400, detail="No script in state")
    
    # Find and update the target slide
    updated = False
    for slide in script:
        if slide.get("slide_number") == req.slide_number:
            if req.field in ("narration", "visual_cue"):
                slide[req.field] = req.value
                updated = True
            else:
                raise HTTPException(status_code=400, detail=f"Invalid field: {req.field}")
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail=f"Slide {req.slide_number} not found")
    
    # Update the graph state directly via the checkpointer
    await graph.aupdate_state(config, {"script": script})
    
    return {
        "success": True,
        "slide_number": req.slide_number,
        "field": req.field,
        "message": "Slide updated (zero tokens used)"
    }


@router.get("/history/{thread_id}")
async def get_history(thread_id: str):
    """Retrieve the current state and conversation history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    
    graph = get_graph()
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    values = state.values
    
    # Check if currently interrupted
    is_interrupted = False
    interrupt_payload = None
    if getattr(state, 'tasks', None) and len(state.tasks) > 0:
        task = state.tasks[0]
        if hasattr(task, 'interrupts') and task.interrupts:
            is_interrupted = True
            interrupt_payload = task.interrupts[0].value
    
    return {
        "thread_id": thread_id,
        "current_stage": values.get("current_stage", "unknown"),
        "foss_name": values.get("foss_name"),
        "script_version": values.get("script_version", 0),
        "script": values.get("script"),
        "metadata": values.get("metadata"),
        "grounding_report": values.get("grounding_report"),
        "compliance_results": values.get("compliance_results"),
        "is_interrupted": is_interrupted,
        "interrupt_payload": interrupt_payload,
    }


@router.get("/checkpoints/{thread_id}")
async def get_checkpoints(thread_id: str):
    """Retrieve the list of past state snapshots (edits/versions)."""
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()
    
    # aget_state_history returns an async generator
    checkpoints = []
    async for state_snapshot in graph.aget_state_history(config):
        # We only care about snapshots that represent a distinct script generation or edit
        # Filter to keep snapshots where a script_version exists
        version = state_snapshot.values.get("script_version")
        if version is not None:
            checkpoints.append({
                "checkpoint_id": state_snapshot.config["configurable"]["checkpoint_id"],
                "version": version,
                "stage": state_snapshot.values.get("current_stage"),
                "timestamp": state_snapshot.created_at if hasattr(state_snapshot, "created_at") else None
            })
            
    # Deduplicate by version number (keep the latest checkpoint for each version)
    seen_versions = set()
    unique_checkpoints = []
    for cp in checkpoints:
        if cp["version"] not in seen_versions:
            seen_versions.add(cp["version"])
            unique_checkpoints.append(cp)
            
    return {"checkpoints": unique_checkpoints}


@router.post("/revert/{thread_id}")
async def revert_state(thread_id: str, req: RevertRequest):
    """Reverts the thread's state back to a past checkpoint's values."""
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()
    
    # 1. Fetch the exact past state snapshot using the provided checkpoint_id
    past_config = {"configurable": {"thread_id": thread_id, "checkpoint_id": req.checkpoint_id}}
    past_state = await graph.aget_state(past_config)
    
    if not past_state or not past_state.values:
        raise HTTPException(status_code=404, detail="Past checkpoint not found")
        
    # 2. Re-write the past values to the CURRENT head of the thread
    # This acts like a 'git revert' - we move forward but with old values
    await graph.aupdate_state(config, past_state.values)
    
    return {"success": True, "message": f"Successfully reverted to script version {past_state.values.get('script_version')}"}


@router.post("/jump/{thread_id}")
async def jump_stage(thread_id: str, req: JumpRequest):
    """Forcefully updates the current_stage state variable to route backwards."""
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()
    
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    # Overwrite the state. We use as_node to dictate where the flow continues from.
    # To force the router to re-evaluate, we simulate an update coming from the current active node
    # Since we are paused at script_review, we use that node.
    await graph.aupdate_state(
        config, 
        {"current_stage": req.target_stage}, 
        as_node="script_review"
    )
    
    return {"success": True, "message": f"Successfully jumped to {req.target_stage}"}


@router.get("/export-docx/{thread_id}")
async def export_docx_file(thread_id: str):
    """Retrieve the current script state and export it to a Word document (.docx)."""
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()
    
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    metadata = state.values.get("metadata", {})
    script = state.values.get("script", [])
    
    # Map graph state values to structure expected by docx_service
    docx_data = {
        "presentation_title": metadata.get("title", "Spoken Tutorial Script"),
        "series": "Pedagogical Script",
        "tutorial": metadata.get("title", ""),
        "duration": "3-4 min",
        "learning_objectives": metadata.get("learning_objectives", []),
        "prerequisites": metadata.get("prerequisites", ""),
        "meta_tags": metadata.get("meta_tags", []),
        "outline": metadata.get("outline_topics", []),
        "slides": script
    }
    
    from src.services.docx_service import json_to_docx
    try:
        buffer = json_to_docx(docx_data)
        
        # Format a clean filename from the title
        title_slug = metadata.get("title", "script").lower().replace(" ", "_")
        # Strip any invalid characters
        title_slug = "".join([c for c in title_slug if c.isalnum() or c == "_"])[:40]
        filename = f"{title_slug}_script.docx"
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate docx: {str(e)}")

