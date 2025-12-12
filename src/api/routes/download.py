"""Download route handlers."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/download", tags=["download"])


@router.get("/outline/{filename}")
async def download_outline(filename: str):
    """Serve outline files directly."""
    try:
        # Get project root (3 levels up from src/api/routes/download.py)
        project_root = Path(__file__).parent.parent.parent
        filepath = project_root / "static" / filename
        
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            str(filepath),
            media_type="text/markdown" if filename.endswith('.md') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
