from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import logging
from src.nodes.redesign.gsheet import share_sheet
from src.nodes.redesign.workflow import run_pipeline
from src.nodes.redesign.utils.schema import GenerateTutorialRequest, GenerateTutorialResponse, ShareTutorialRequest, ShareTutorialResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/redesign", tags=["redesign"])

# In-memory store for redesign task progress
redesign_tasks = {}

class WebhookPayload(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    stage: str
    url: Optional[str] = None

@router.get("/")
def health_check():
    return {"status": "OK", "message": "Pipeline is alive."}

def run_pipeline_task(request: GenerateTutorialRequest, task_id: str, webhook_url: str):
    logger.info(f"Background task starting for {task_id}")
    run_pipeline(request=request, task_id=task_id, webhook_url=webhook_url)

@router.post("/generate", response_model=GenerateTutorialResponse)
def generate_tutorial(request: GenerateTutorialRequest, background_tasks: BackgroundTasks):
    try:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Determine webhook URL
        webhook_url = request.webhook_url
        if not webhook_url:
            webhook_url = "http://localhost:8000/redesign/webhook"
            
        # Initialize in-memory status so polling works immediately
        redesign_tasks[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "progress": 0,
            "message": "Task queued, starting redesign pipeline...",
            "stage": "init",
            "url": None
        }
        
        # Enqueue the background task
        background_tasks.add_task(run_pipeline_task, request, task_id, webhook_url)
        
        return GenerateTutorialResponse(status="started", url="", task_id=task_id)

    except Exception as e:
        logger.error(f"Error starting generate task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
def receive_webhook(payload: WebhookPayload):
    """
    Webhook receiver endpoint. Updates in-memory dictionary.
    """
    task_id = payload.task_id
    redesign_tasks[task_id] = {
        "task_id": task_id,
        "status": payload.status,
        "progress": payload.progress,
        "message": payload.message,
        "stage": payload.stage,
        "url": payload.url
    }
    return {"status": "ok"}

@router.get("/progress/{task_id}")
def get_progress(task_id: str):
    """
    Query endpoint to check progress status for a specific task.
    """
    if task_id not in redesign_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return redesign_tasks[task_id]

@router.post("/share", response_model=ShareTutorialResponse)
def share_tutorial(request: ShareTutorialRequest):
    try:
        message = share_sheet(request.url, request.recipients)
        return {
            "status": "Success",
            "message": message
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    