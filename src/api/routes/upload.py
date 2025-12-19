"""Upload route handlers."""
from fastapi import APIRouter, HTTPException, File, UploadFile
from pathlib import Path
import os
import json
import time
import traceback

from src.services.outline_service import parse_docx_outline

router = APIRouter(tags=["upload"])


@router.post("/upload_outline")
async def upload_outline(file: UploadFile = File(...)):
    """Upload an edited outline file (.md or .docx)."""
    try:
        # Validate file type
        if not (file.filename.endswith('.md') or file.filename.endswith('.docx') or file.filename.endswith('.txt') or file.filename.endswith('.odt')):
            raise HTTPException(status_code=400, detail="Only .md, .txt, .docx, or .odt files are allowed")
        
        # Get project root (3 levels up from src/api/routes/upload.py)
        project_root = Path(__file__).parent.parent.parent
        
        # Save uploaded file temporarily
        upload_dir = project_root / "uploads"
        upload_dir.mkdir(exist_ok=True)
        
        temp_path = upload_dir / f"outline_{int(time.time())}_{file.filename}"
        
        with open(str(temp_path), "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse the document
        outline_text = parse_docx_outline(str(temp_path))
        
        # Clean up temp file
        os.remove(str(temp_path))
        
        return {
            "outline": outline_text,
            "message": "Outline uploaded successfully"
        }
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in upload_outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_script")
async def upload_script(file: UploadFile = File(...)):
    """Upload a script JSON file directly to skip outline → script generation."""
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only .json files are allowed")
        
        # Get project root (3 levels up from src/api/routes/upload.py)
        project_root = Path(__file__).parent.parent.parent
        
        # Read and parse JSON content
        content = await file.read()
        json_script = json.loads(content.decode('utf-8'))
        
        # Generate project ID
        project_id = int(time.time())
        
        # Save a copy
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        json_path = output_dir / f"script_{project_id}.json"
        with open(str(json_path), 'w') as f:
            json.dump(json_script, f, indent=2)
        
        print(f"✅ Script uploaded: {file.filename} → project #{project_id}")
        
        return {
            "json_script": json_script,
            "project_id": project_id,
            "message": "Script uploaded successfully"
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in upload_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))
