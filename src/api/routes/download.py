"""Download route handlers."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/download", tags=["download"])

# Get project root (3 levels up from src/api/routes/download.py)
project_root = Path(__file__).parent.parent.parent.parent


@router.get("/outline/{filename}")
async def download_outline(filename: str):
    """Serve outline files directly."""
    try:
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


@router.get("/image/{project_id}/{filename}")
async def download_image(project_id: str, filename: str):
    """Serve image with Content-Disposition: attachment header for download."""
    try:
        filepath = project_root / "output" / "images" / project_id / filename
        
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Determine media type
        suffix = filepath.suffix.lower()
        media_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        media_type = media_types.get(suffix, 'application/octet-stream')
        
        return FileResponse(
            path=str(filepath),
            filename=filename,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
