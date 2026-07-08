"""Upload and script parsing route handlers."""
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from pathlib import Path
import os
import json
import time
import traceback

from src.api.auth import get_current_user, TokenData
from src.services.outline_service import parse_docx_outline
from src.api.routes.compliance import _detect_tutorial_type

router = APIRouter(tags=["upload"])


@router.post("/upload_outline")
async def upload_outline(file: UploadFile = File(...), current_user: TokenData = Depends(get_current_user)):
    """Upload an edited outline file (.md, .docx, .txt, or .odt)."""
    try:
        # Validate file type (case-insensitive)
        filename_lower = file.filename.lower() if file.filename else ""
        if not (filename_lower.endswith('.md') or filename_lower.endswith('.docx') or filename_lower.endswith('.txt') or filename_lower.endswith('.odt')):
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
        try:
            outline_text = parse_docx_outline(str(temp_path))
        except ValueError as ve:
            # Clean up temp file before raising error
            if temp_path.exists():
                os.remove(str(temp_path))
            raise HTTPException(status_code=400, detail=f"Error parsing document: {str(ve)}")
        except Exception as parse_error:
            # Clean up temp file before raising error
            if temp_path.exists():
                os.remove(str(temp_path))
            raise HTTPException(status_code=400, detail=f"Failed to parse document. Please ensure it's a valid .docx, .md, .txt, or .odt file: {str(parse_error)}")
        
        # Clean up temp file
        if temp_path.exists():
            os.remove(str(temp_path))
        
        return {
            "outline": outline_text,
            "message": f"Outline uploaded successfully ({file.filename})"
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in upload_outline: {e}")
        raise HTTPException(status_code=500, detail=f"Server error while processing file: {str(e)}")


@router.post("/parse_script")
async def parse_script(file: UploadFile = File(...), current_user: TokenData = Depends(get_current_user)):
    """Parse a script file (.json, .docx, or .odt) WITHOUT running any checks."""
    try:
        filename = file.filename.lower()
        
        # Validate file type
        if not (filename.endswith('.json') or filename.endswith('.docx') or filename.endswith('.odt')):
            raise HTTPException(status_code=400, detail="Only .json, .docx, or .odt files are allowed")
        
        # Get project root
        project_root = Path(__file__).parent.parent.parent
        
        # Read file content
        content = await file.read()
        
        # Parse based on file type
        if filename.endswith('.json'):
            # Direct JSON parsing
            json_script = json.loads(content.decode('utf-8'))
            source_artifact = {"file_type": "json", "hyperlinks": []}
        else:
            # Parse docx/odt using existing parser
            from io import BytesIO
            from src.services.docx_service import docx_to_json, extract_docx_hyperlinks
            
            json_script = docx_to_json(BytesIO(content))
            source_artifact = {
                "file_type": "docx" if filename.endswith('.docx') else "odt",
                "hyperlinks": extract_docx_hyperlinks(BytesIO(content)) if filename.endswith('.docx') else []
            }
        
        # Detect tutorial type (demo or conceptual)
        tutorial_type = _detect_tutorial_type(json_script)
        
        # Generate project ID
        project_id = int(time.time())
        
        # Save a copy
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        json_path = output_dir / f"script_{project_id}.json"
        with open(str(json_path), 'w') as f:
            json.dump(json_script, f, indent=2)
        
        print(f"✅ Script parsed: {file.filename} → project #{project_id}")
        
        return {
            "json_script": json_script,
            "project_id": project_id,
            "tutorial_type": tutorial_type,
            "source_artifact": source_artifact,
            "message": "Script parsed successfully"
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Could not parse document: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in parse_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_script")
async def upload_script(file: UploadFile = File(...), current_user: TokenData = Depends(get_current_user)):
    """Upload a script file (.json, .docx, or .odt) and run compliance check."""
    try:
        filename = file.filename.lower()
        
        # Validate file type
        if not (filename.endswith('.json') or filename.endswith('.docx') or filename.endswith('.odt')):
            raise HTTPException(status_code=400, detail="Only .json, .docx, or .odt files are allowed")
        
        # Get project root
        project_root = Path(__file__).parent.parent.parent
        
        # Read file content
        content = await file.read()
        
        # Parse based on file type
        if filename.endswith('.json'):
            # Direct JSON parsing
            json_script = json.loads(content.decode('utf-8'))
        else:
            # Parse docx/odt using existing parser
            from io import BytesIO
            from src.services.docx_service import docx_to_json
            
            json_script = docx_to_json(BytesIO(content))
        
        # Detect tutorial type (demo or conceptual)
        tutorial_type = _detect_tutorial_type(json_script)
        
        # Run compliance checks
        from src.services.compliance_service import check_compliance
        compliance_report = await check_compliance(json_script, tutorial_type)
        
        # Generate project ID
        project_id = int(time.time())
        
        # Save a copy
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        json_path = output_dir / f"script_{project_id}.json"
        with open(str(json_path), 'w') as f:
            json.dump(json_script, f, indent=2)
        
        print(f"✅ Script uploaded: {file.filename} → project #{project_id}")
        print(f"📋 Compliance: {compliance_report['summary']['ai_failed']} issues found")
        
        return {
            "json_script": json_script,
            "project_id": project_id,
            "message": "Script uploaded successfully",
            "compliance_report": compliance_report
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Could not parse document: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in upload_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))
