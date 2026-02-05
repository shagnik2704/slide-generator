from fastapi import APIRouter, HTTPException
from src.api.models import GenerateTutorialRequest, GenerateTutorialResponse, ShareTutorialRequest, ShareTutorialResponse
from src.workflow import run_pipeline
from src.nodes.gsheet import share_sheet

router = APIRouter(prefix="/redesign", tags=["redesign"])

@router.get("/")
def health_check():
    return {"status": "OK", "message": "Pipeline is alive."}

@router.post("/generate", response_model=GenerateTutorialResponse)
def generate_tutorial(request: GenerateTutorialRequest):
    try:
        state, url = run_pipeline(
            foss_name=request.foss_name,
            language=request.language,
            export=True,  # Always export for generation
            reciept_emails=[],  # No emails for generation
            reciept_role="writer"  # Default role, not used since no emails
        )

        return {
            "status": "Success",
            "url": url
        }

    except ValueError as e:
        # Handle validation errors (e.g., no tutorials found)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    