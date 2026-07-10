from fastapi import APIRouter, HTTPException
from src.nodes.redesign.gsheet import share_sheet
from src.nodes.redesign.workflow import run_pipeline
from src.nodes.redesign.utils.schema import GenerateTutorialRequest, GenerateTutorialResponse, ShareTutorialRequest, ShareTutorialResponse

router = APIRouter(prefix="/redesign", tags=["redesign"])

@router.get("/")
def health_check():
    return {"status": "OK", "message": "Pipeline is alive."}

@router.post("/generate", response_model=GenerateTutorialResponse)
def generate_tutorial(request: GenerateTutorialRequest):
    try:
        return run_pipeline(request=request)

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
    