"""FastAPI routes for the Script Chat flow."""
import io
import json
import uuid
import logging
from copy import deepcopy
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from src.api.auth import TokenData, get_current_user
from src.script_chat.graph import build_script_chat_graph
from src.script_chat.persistence import (
    archive_thread,
    close_script_chat_pool,
    create_thread,
    delete_thread,
    get_pool,
    get_thread,
    list_threads,
    open_script_chat_pool,
    update_thread,
)
from src.script_chat.schemas import (
    EditableScriptField,
    ResumeAction,
    ScriptMetadata,
    dump_models,
    parse_script,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/script-chat", tags=["Script Chat"])

_graph = None

def get_graph():
    global _graph
    if _graph is None:
        raise RuntimeError("Graph is not initialized. Make sure server lifespan started.")
    return _graph


async def _get_state_or_404(config: dict):
    state = await get_graph().aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    return state


async def _get_owned_state_or_404(thread_id: str, current_user: TokenData):
    """Load graph state only after verifying that this user owns the thread."""
    if not await get_thread(thread_id, current_user.sub):
        # Deliberately avoid exposing whether another user's UUID exists.
        raise HTTPException(status_code=404, detail="Thread not found")
    config = {"configurable": {"thread_id": thread_id}}
    return await _get_state_or_404(config)


def _interrupt_payload(state):
    if getattr(state, "tasks", None):
        for task in state.tasks:
            if getattr(task, "interrupts", None):
                return task.interrupts[0].value
    return None

async def init_script_chat_graph():
    global _graph
    await open_script_chat_pool()
    try:
        saver = AsyncPostgresSaver(get_pool())
        _graph = build_script_chat_graph(checkpointer=saver)
    except Exception:
        await close_script_chat_pool()
        raise
    logger.info("✅ Script Chat graph initialized with AsyncPostgresSaver")

async def close_script_chat_graph():
    global _graph
    _graph = None
    await close_script_chat_pool()
    logger.info("🔒 Script Chat PostgreSQL pool closed")

class StartRequest(BaseModel):
    outline: str = Field(min_length=1)
    foss_name: Optional[str] = None

class StartResponse(BaseModel):
    thread_id: str
    message: str

class ResumeRequest(BaseModel):
    """Payload to resume from an interrupt."""
    action: ResumeAction
    instruction: Optional[str] = None
    edited_content: Optional[str] = None
    edited_metadata: Optional[ScriptMetadata] = None

class ManualEditRequest(BaseModel):
    """Direct manual edit to a slide (zero LLM tokens)."""
    slide_number: int = Field(ge=1)
    field: EditableScriptField
    value: str

class RevertRequest(BaseModel):
    checkpoint_id: str

class JumpRequest(BaseModel):
    target_stage: Literal["metadata_review", "generate", "edit", "compliance"]
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
        await update_thread(
            config["configurable"]["thread_id"],
            current_stage=None,
            status="running",
        )
        stream_input = input_data if input_data is not None else None
        graph = get_graph()
        
        async for mode, chunk in graph.astream(
            stream_input,
            config=config,
            stream_mode=["custom", "updates"]
        ):
            if mode == "custom":
                yield _sse_event("progress", chunk)
            
            elif mode == "updates":
                for node_name in chunk:
                    if node_name == "__interrupt__":
                        continue
                    yield _sse_event("state", {
                        "node": node_name,
                        "status": "completed"
                    })
        
        state = await graph.aget_state(config)
        interrupt_payload = _interrupt_payload(state)
        current_stage = state.values.get("current_stage", "unknown")
        metadata = state.values.get("metadata") or {}
        title = metadata.get("title") if isinstance(metadata, dict) else getattr(metadata, "title", None)
        status = "awaiting_review" if interrupt_payload else "completed"
        if current_stage == "error":
            status = "failed"
        await update_thread(
            config["configurable"]["thread_id"],
            current_stage=current_stage,
            status=status,
            title=title,
        )
        if interrupt_payload:
            yield _sse_event("interrupt", interrupt_payload)
        else:
            yield _sse_event("done", {
                "stage": current_stage
            })
    
    except Exception as e:
        logger.error(f"SSE stream error: {e}", exc_info=True)
        try:
            await update_thread(
                config["configurable"]["thread_id"],
                current_stage="error",
                status="failed",
            )
        except Exception:
            logger.exception("Failed to persist Script Chat stream failure")
        yield _sse_event("error", {"message": str(e)})

@router.post("/start", response_model=StartResponse)
async def start_session(req: StartRequest, current_user: TokenData = Depends(get_current_user)):
    """Start a new script chat session.
    
    Returns a thread_id. Client should immediately connect to 
    GET /script-chat/stream/{thread_id} to receive SSE events.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initialize the graph state in the database checkpointer
    initial_input = {
        "raw_outline": req.outline,
        "foss_name": req.foss_name,
        "messages": [],
        "script_version": 0,
        "current_stage": "ingest"
    }
    
    outline_preview = " ".join(req.outline.split())[:240]
    await create_thread(thread_id, current_user.sub, req.foss_name, outline_preview)
    try:
        await get_graph().aupdate_state(config, initial_input, as_node="__start__")
    except Exception:
        await delete_thread(thread_id, current_user.sub)
        raise
    
    return StartResponse(
        thread_id=thread_id,
        message="Session created. Connect to /script-chat/stream/{thread_id} to begin."
    )


@router.get("/stream/{thread_id}")
async def stream_events(thread_id: str, current_user: TokenData = Depends(get_current_user)):
    """SSE endpoint. Streams LangGraph events for the given thread.
    
    On first connection: starts the graph from the saved state.
    On subsequent connections: streams the current state (useful for reconnects).
    """
    config = {"configurable": {"thread_id": thread_id}}
    state = await _get_owned_state_or_404(thread_id, current_user)
    
    interrupt_payload = _interrupt_payload(state)
    is_interrupted = interrupt_payload is not None
    
    if state.next and not is_interrupted:
        return StreamingResponse(
            _stream_graph(config, None),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        async def reconnect_stream():
            if is_interrupted:
                yield _sse_event("interrupt", interrupt_payload)
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


@router.post("/resume/{thread_id}")
async def resume_session(
    thread_id: str,
    req: ResumeRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Resume from an interrupt (HITL gate).
    
    Returns an SSE stream of events as the graph continues executing.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state = await _get_owned_state_or_404(thread_id, current_user)
    if not state.next or _interrupt_payload(state) is None:
        raise HTTPException(
            status_code=400,
            detail=f"Graph is not paused at an interrupt. Current stage: {state.values.get('current_stage')}",
        )

    resume_data = {"action": req.action}
    if req.instruction:
        resume_data["instruction"] = req.instruction
    if req.edited_content:
        resume_data["edited_content"] = req.edited_content
    if req.edited_metadata:
        resume_data["edited_metadata"] = req.edited_metadata.model_dump()
    
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
async def manual_edit(
    thread_id: str,
    req: ManualEditRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Direct manual edit to a slide while paused at script review."""
    config = {"configurable": {"thread_id": thread_id}}

    state = await _get_owned_state_or_404(thread_id, current_user)
    interrupt_payload = _interrupt_payload(state)
    if not interrupt_payload or interrupt_payload.get("type") != "script_review":
        raise HTTPException(status_code=400, detail="Manual edits are only allowed during script review")

    raw_script = state.values.get("script", [])
    if not raw_script:
        raise HTTPException(status_code=400, detail="No script in state")

    try:
        script = dump_models(parse_script(deepcopy(raw_script)))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid script state: {str(e)}") from e

    for slide in script:
        if slide.get("slide_number") == req.slide_number:
            slide[req.field] = req.value
            break
    else:
        raise HTTPException(status_code=404, detail=f"Slide {req.slide_number} not found")

    try:
        script = dump_models(parse_script(script))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid edit result: {str(e)}") from e

    await get_graph().aupdate_state(
        config,
        {
            "script": script,
            "script_version": state.values.get("script_version", 0) + 1,
        },
    )
    await update_thread(
        thread_id,
        current_stage=state.values.get("current_stage", "script_review"),
        status="awaiting_review",
    )
    
    return {
        "success": True,
        "slide_number": req.slide_number,
        "field": req.field,
        "message": "Slide updated (zero tokens used)"
    }


@router.get("/history/{thread_id}")
async def get_history(thread_id: str, current_user: TokenData = Depends(get_current_user)):
    """Retrieve the current state and conversation history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    thread = await get_thread(thread_id, current_user.sub)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    state = await _get_state_or_404(config)
    
    values = state.values
    
    interrupt_payload = _interrupt_payload(state)
    is_interrupted = interrupt_payload is not None
    
    return {
        "thread_id": thread_id,
        "raw_outline": values.get("raw_outline"),
        "current_stage": values.get("current_stage", "unknown"),
        "foss_name": values.get("foss_name"),
        "script_version": values.get("script_version", 0),
        "script": values.get("script"),
        "metadata": values.get("metadata"),
        "grounding_report": values.get("grounding_report"),
        "compliance_results": values.get("compliance_results"),
        "is_interrupted": is_interrupted,
        "interrupt_payload": interrupt_payload,
        "status": thread["status"],
        "created_at": thread["created_at"],
        "updated_at": thread["updated_at"],
    }


@router.get("/threads")
async def get_threads(current_user: TokenData = Depends(get_current_user)):
    """List the logged-in user's persistent Script Chat threads."""
    return {"threads": await list_threads(current_user.sub)}


@router.post("/threads/{thread_id}/archive")
async def archive_thread_endpoint(
    thread_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Archive a thread owned by the current user without deleting checkpoints."""
    if not await archive_thread(thread_id, current_user.sub):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"success": True, "thread_id": thread_id}


@router.get("/checkpoints/{thread_id}")
async def get_checkpoints(thread_id: str, current_user: TokenData = Depends(get_current_user)):
    """Retrieve the list of past state snapshots (edits/versions)."""
    config = {"configurable": {"thread_id": thread_id}}
    await _get_owned_state_or_404(thread_id, current_user)
    graph = get_graph()
    
    checkpoints = []
    async for state_snapshot in graph.aget_state_history(config):
        version = state_snapshot.values.get("script_version")
        if version is not None:
            checkpoints.append({
                "checkpoint_id": state_snapshot.config["configurable"]["checkpoint_id"],
                "version": version,
                "stage": state_snapshot.values.get("current_stage"),
                "timestamp": state_snapshot.created_at if hasattr(state_snapshot, "created_at") else None
            })
            
    seen_versions = set()
    unique_checkpoints = []
    for cp in checkpoints:
        if cp["version"] not in seen_versions:
            seen_versions.add(cp["version"])
            unique_checkpoints.append(cp)
            
    return {"checkpoints": unique_checkpoints}


@router.post("/revert/{thread_id}")
async def revert_state(
    thread_id: str,
    req: RevertRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Reverts the thread's state back to a past checkpoint's values."""
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()
    await _get_owned_state_or_404(thread_id, current_user)
    
    past_config = {"configurable": {"thread_id": thread_id, "checkpoint_id": req.checkpoint_id}}
    past_state = await graph.aget_state(past_config)
    
    if not past_state or not past_state.values:
        raise HTTPException(status_code=404, detail="Past checkpoint not found")

    if past_state.values.get("script"):
        try:
            parse_script(past_state.values["script"])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Past checkpoint has invalid script: {str(e)}") from e

    await graph.aupdate_state(config, past_state.values)
    await update_thread(
        thread_id,
        current_stage=past_state.values.get("current_stage", "unknown"),
        status="awaiting_review" if _interrupt_payload(past_state) else "running",
    )
    
    return {"success": True, "message": f"Successfully reverted to script version {past_state.values.get('script_version')}"}


@router.post("/jump/{thread_id}")
async def jump_stage(
    thread_id: str,
    req: JumpRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Move a paused thread to a supported review/continuation point."""
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()
    
    state = await _get_owned_state_or_404(thread_id, current_user)
    if req.target_stage == "metadata_review":
        if not state.values.get("metadata"):
            raise HTTPException(status_code=400, detail="Cannot jump to metadata review without metadata")
        await graph.aupdate_state(config, {"current_stage": "metadata"}, as_node="metadata")
        await update_thread(thread_id, current_stage="metadata", status="awaiting_review")
        return {"success": True, "message": "Successfully jumped to metadata_review"}

    as_node = "metadata_review" if req.target_stage == "generate" else "script_review"
    await graph.aupdate_state(
        config, 
        {"current_stage": req.target_stage}, 
        as_node=as_node,
    )
    await update_thread(thread_id, current_stage=req.target_stage, status="awaiting_review")
    
    return {"success": True, "message": f"Successfully jumped to {req.target_stage}"}


@router.get("/export-docx/{thread_id}")
async def export_docx_file(
    thread_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Retrieve the current script state and export it to a Word document (.docx)."""
    config = {"configurable": {"thread_id": thread_id}}
    state = await _get_owned_state_or_404(thread_id, current_user)
        
    metadata = state.values.get("metadata", {})
    series_name = state.values.get("foss_name") or metadata.get("foss_name") or "Pedagogical Script"
    try:
        script = dump_models(parse_script(state.values.get("script", [])))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid script state: {str(e)}") from e
    
    docx_data = {
        "presentation_title": metadata.get("title", "Spoken Tutorial Script"),
        "series": series_name,
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
        
        title_slug = metadata.get("title", "script").lower().replace(" ", "_")
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


@router.get("/export-wiki/{thread_id}")
async def export_wiki_file(
    thread_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Retrieve the current script state and export it to MediaWiki markup (.wiki)."""
    state = await _get_owned_state_or_404(thread_id, current_user)

    metadata = state.values.get("metadata", {})
    series_name = state.values.get("foss_name") or metadata.get("foss_name") or "Pedagogical Script"
    try:
        script = dump_models(parse_script(state.values.get("script", [])))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid script state: {str(e)}") from e

    wiki_data = {
        "presentation_title": metadata.get("title", "Spoken Tutorial Script"),
        "series": series_name,
        "tutorial": metadata.get("title", ""),
        "duration": "3-4 min",
        "learning_objectives": metadata.get("learning_objectives", []),
        "prerequisites": metadata.get("prerequisites", ""),
        "system_requirements": metadata.get("system_requirements", ""),
        "meta_tags": metadata.get("meta_tags", []),
        "outline": metadata.get("outline_topics", []),
        "slides": script,
    }

    from src.services.mediawiki_service import create_mediawiki_script
    try:
        content = create_mediawiki_script(wiki_data)

        title_slug = metadata.get("title", "script").lower().replace(" ", "_")
        title_slug = "".join([c for c in title_slug if c.isalnum() or c == "_"])[:40]
        filename = f"{title_slug}_script.wiki"

        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate wiki: {str(e)}")
