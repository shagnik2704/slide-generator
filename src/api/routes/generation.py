"""Generation route handlers (script, slides, video)."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import os
import json
import time
import traceback

from src.api.auth import get_current_user, TokenData
from src.api.models import GenerateScriptRequest, GenerateVideoRequest, ExportMediaWikiRequest, DownloadScriptDocxRequest
from src.services.mediawiki_service import export_to_mediawiki
from src.services.docx_service import export_script_docx, docx_to_json

router = APIRouter(tags=["generation"])


@router.post("/generate_script")
async def generate_script(request: GenerateScriptRequest, req: Request, current_user: TokenData = Depends(get_current_user)):
    """Generates a presentation script from a user-provided outline."""
    
    print(f"Received request to generate script from outline ({len(request.outline)} chars)")

    try:
        # Get project root (3 levels up from src/api/routes/generation.py)
        project_root = Path(__file__).parent.parent.parent
        
        print(f"📝 Generating script from outline...")
        
        initial_state = {
            "outline": request.outline,
            "mode": getattr(request, 'mode', 'script_only'),
        }
        
        # Use graph from app.state
        graph = req.app.state.graph
        result = await graph.ainvoke(initial_state)
        
        json_script = result.get("json_script")
        
        if json_script:
            project_id = int(time.time())
            
            # Save JSON script
            output_dir = project_root / "output"
            output_dir.mkdir(exist_ok=True)
            json_path = output_dir / f"script_{project_id}.json"
            with open(str(json_path), 'w') as f:
                json.dump(json_script, f, indent=2)
            
            print(f"✅ Saved script JSON for project #{project_id}")
            print(f"   Slides: {len(json_script.get('slides', []))}")
            
            return JSONResponse({
                "json_script": json_script,
                "outline": request.outline
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to generate script")
            
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))






@router.post("/generate_video")
async def generate_video(request: GenerateVideoRequest, req: Request, current_user: TokenData = Depends(get_current_user)):
    """Generates the final video from the approved JSON script and existing PDF."""
    try:
        # Get project root (3 levels up from src/api/routes/generation.py)
        project_root = Path(__file__).parent.parent.parent
        
        # Pass pdf_path to the state
        initial_state = {
            "json_script": request.json_script, 
            "mode": "video_production",
            "pdf_path": request.pdf_path or "output.pdf"
        }
        # Use graph from app.state
        graph = req.app.state.graph
        result = await graph.ainvoke(initial_state)
        
        video_path = result.get("video_path")
        
        if video_path and os.path.exists(video_path):
            video_filename = os.path.basename(video_path)
            print(f"✅ Generated video: {video_filename}")
            
            return JSONResponse({
                "video_url": f"/static/{video_filename}"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to generate video")
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export_mediawiki")
async def export_mediawiki_endpoint(request: ExportMediaWikiRequest, current_user: TokenData = Depends(get_current_user)):
    """Exports the JSON script to MediaWiki format for Spoken Tutorial upload."""
    print("Exporting script to MediaWiki format...")
    
    try:
        result = export_to_mediawiki(request.json_script)
        
        print(f"✅ Exported to MediaWiki: {result['file_path']}")
        
        return JSONResponse({
            "mediawiki_content": result["content"],
            "mediawiki_file_url": f"/static/{os.path.basename(result['file_path'])}",
            "file_path": result["file_path"]
        })
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in export_mediawiki: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/docx_to_mediawiki")
async def docx_to_mediawiki(file: UploadFile = File(...), current_user: TokenData = Depends(get_current_user)):
    """Converts a .docx script directly to MediaWiki format in one step."""
    print(f"Converting .docx to MediaWiki: {file.filename}")
    
    try:
        # Validate file type
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="Only .docx files are allowed")
        
        # Read file content
        content = await file.read()
        
        # Step 1: Parse docx → JSON
        from io import BytesIO
        json_script = docx_to_json(BytesIO(content))
        
        slide_count = len(json_script.get('slides', []))
        print(f"📝 Parsed script: {slide_count} slides")
        
        # Step 2: JSON → MediaWiki
        result = export_to_mediawiki(json_script)
        
        print(f"✅ Converted to MediaWiki: {result['file_path']}")
        
        return JSONResponse({
            "mediawiki_content": result["content"],
            "mediawiki_file_url": f"/static/{os.path.basename(result['file_path'])}",
            "file_path": result["file_path"],
            "slide_count": slide_count,
            "message": f"Successfully converted {slide_count} slides to MediaWiki format"
        })
        
    except ValueError as e:
        print(f"Parsing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in docx_to_mediawiki: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download_script_docx")
async def download_script_docx(request: DownloadScriptDocxRequest, current_user: TokenData = Depends(get_current_user)):
    """Downloads the script as an editable Word document with two-column table format."""
    print("Generating editable script .docx...")
    
    try:
        result = export_script_docx(request.json_script)
        file_path = result["file_path"]
        
        print(f"✅ Generated script .docx: {result['file_name']}")
        
        return FileResponse(
            path=file_path,
            filename=result["file_name"],
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in download_script_docx: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_edited_script")
async def upload_edited_script(file: UploadFile = File(...), current_user: TokenData = Depends(get_current_user)):
    """Uploads an edited .docx script and converts it back to JSON format."""
    print(f"Receiving edited script: {file.filename}")
    
    try:
        # Validate file type
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="Only .docx files are allowed")
        
        # Read file content
        content = await file.read()
        
        # Parse docx to JSON
        from io import BytesIO
        json_script = docx_to_json(BytesIO(content))
        
        print(f"✅ Parsed edited script: {len(json_script.get('slides', []))} slides")
        
        return JSONResponse({
            "json_script": json_script,
            "slide_count": len(json_script.get('slides', [])),
            "message": "Script uploaded and parsed successfully"
        })
        
    except ValueError as e:
        print(f"Parsing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in upload_edited_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))
