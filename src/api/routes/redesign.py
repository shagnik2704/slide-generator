from fastapi import APIRouter, HTTPException
from src.api.models import TutorialRequest, TutorialResponse
from src.workflow import run_pipeline

router = APIRouter()

@router.get("/")
def health_check():
    return {"status": "OK", "message": "Pipeline is alive."}

@router.post("/redesign", response_model=TutorialResponse)
def redesign_tutorial(request: TutorialRequest):
    try:
        state, url = run_pipeline(
            foss_name=request.foss_name,
            language=request.language,
            export=request.export,
            recipet_emails=request.user_emails,
            reciept_roles=request.user_role
        )

        return {
            "status": "Success",
            "url": url,
            "response": state
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))