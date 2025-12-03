from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union, Optional
import os
import json
import sqlite3
from agent import graph
from sqlalchemy.orm import Session
from database import get_db, engine, Base
from db_models import Project, Asset, ProjectStatus, AssetType
from outline_generator import create_outline_docx, parse_docx_outline

app = FastAPI(title="Slide Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files to serve generated content
app.mount("/static", StaticFiles(directory="static"), name="static")

class SlideContentItem(BaseModel):
    type: str
    items: Optional[List[str]] = None

class Slide(BaseModel):
    id: str
    type: str
    title: str
    content: List[Union[str, dict]] # Pydantic might struggle with mixed types in List, keeping it simple for now or using custom validation if needed. 
    # For simplicity, let's accept dict for the complex content items (lists) and str for text.
    
class GenerateScriptRequest(BaseModel):
    topic: Optional[str] = None  # Either topic OR outline must be provided
    outline: Optional[str] = None  # Pre-generated outline
    title: Optional[str] = None
    target_audience: Optional[str] = None
    mode: Optional[str] = "script_only"  # Default: old monolithic workflow (script_parallel available if needed)

class GenerateOutlineRequest(BaseModel):
    topic: str
    target_audience: Optional[str] = None  # "kids", "students", "professionals", "general" or None to infer

class GenerateVideoRequest(BaseModel):
    json_script: dict
    pdf_path: Optional[str] = None
    project_id: Optional[int] = None  # Track which project this belongs to

class GenerateSlidesRequest(BaseModel):
    json_script: dict
    project_id: Optional[int] = None
    project_id: Optional[int] = None

@app.post("/generate_outline")
async def generate_outline(request: GenerateOutlineRequest, db: Session = Depends(get_db)):
    try:
        # Create a new project using SQLAlchemy
        new_project = Project(
            title=request.topic,  # Use topic as initial title
            outline=request.topic,
            status=ProjectStatus.DRAFT
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        project_id = new_project.id

        # Run the agent to generate outline
        inputs = {
            "topic": request.topic,
            "project_id": project_id,
            "mode": "outline_only"
        }
        
        result = await graph.ainvoke(inputs)
        
        outline_text = result.get("outline", "")
        
        # Generate Markdown file from outline
        docx_path = create_outline_docx(outline_text, project_id)
        outline_url = f"/download/outline/{os.path.basename(docx_path)}"
        
        # Update project status
        new_project.status = ProjectStatus.SCRIPT_READY  # Outline is ready
        db.commit()
        
        return {
            "project_id": project_id,
            "outline": outline_text,
            "outline_docx_url": outline_url,
            "target_audience": result.get("target_audience")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_outline")
async def upload_outline(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an edited outline file (.md or .docx)."""
    try:
        # Validate file type
        if not (file.filename.endswith('.md') or file.filename.endswith('.docx') or file.filename.endswith('.txt')):
            raise HTTPException(status_code=400, detail="Only .md, .txt, or .docx files are allowed")
        
        # Save uploaded file temporarily
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        temp_path = os.path.join(upload_dir, f"outline_{project_id}_{file.filename}")
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse the document
        outline_text = parse_docx_outline(temp_path)
        
        # Update project in database
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project.outline = outline_text
        project.status = ProjectStatus.SCRIPT_READY
        db.commit()
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "project_id": project_id,
            "outline": outline_text,
            "message": "Outline updated successfully"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in upload_outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_script")
async def generate_script(request: GenerateScriptRequest, db: Session = Depends(get_db)):
    """Generates a presentation script. If topic is provided, generates outline first."""
    
    # Validate that either topic or outline is provided
    if not request.topic and not request.outline:
        raise HTTPException(status_code=400, detail="Either 'topic' or 'outline' must be provided")
    
    print(f"Received request to generate script. Topic: {request.topic}, Has outline: {bool(request.outline)}")
    
    # Create new project
    project = Project(
        title=request.title or request.topic or "Untitled",
        status=ProjectStatus.GENERATING_SCRIPT
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    print(f"Created project #{project.id}")

    try:
        # STEP 1: Generate outline if only topic is provided
        outline_text = request.outline
        
        if not outline_text and request.topic:
            print(f"🔍 Step 1: Generating outline for topic: {request.topic}")
            outline_state = {
                "topic": request.topic,
                "project_id": project.id,
                "mode": "outline_only"
            }
            
            outline_result = await graph.ainvoke(outline_state)
            outline_text = outline_result.get("outline", "")
            
            if not outline_text:
                raise HTTPException(status_code=500, detail="Failed to generate outline")
            
            # Save outline to project
            project.outline = outline_text
            db.commit()
            
            print(f"✓ Outline generated successfully ({len(outline_text)} chars)")
        
        # STEP 2: Generate script from outline
        print(f"📝 Step 2: Generating script from outline...")
        
        initial_state = {
            "outline": outline_text,
            "project_id": project.id,
            "mode": getattr(request, 'mode', 'script_only'),
            "target_audience": request.target_audience
        }
        
        result = await graph.ainvoke(initial_state)
        
        script_pdf_path = result.get("script_pdf_path")
        json_script = result.get("json_script")
        
        if script_pdf_path:
            # Save script PDF as an asset
            script_asset = Asset(
                project_id=project.id,
                asset_type=AssetType.SCRIPT_PDF,
                file_path=script_pdf_path
            )
            db.add(script_asset)
            
            # Save JSON script as an asset
            json_path = f"script_{project.id}.json"
            with open(json_path, 'w') as f:
                json.dump(json_script, f, indent=2)
            
            json_asset = Asset(
                project_id=project.id,
                asset_type=AssetType.JSON_SCRIPT,
                file_path=json_path
            )
            db.add(json_asset)
            
            # Update project status
            project.status = ProjectStatus.SCRIPT_READY
            db.commit()
            
            print(f"✅ Saved script PDF and JSON for project #{project.id}")
            
            return JSONResponse({
                "project_id": project.id,
                "script_pdf_url": f"/static/{os.path.basename(script_pdf_path)}",
                "json_script": json_script,
                "outline": outline_text  # Return outline for reference
            })
        else:
            project.status = ProjectStatus.FAILED
            db.commit()
            raise HTTPException(status_code=500, detail="Failed to generate script PDF")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_script: {e}")
        project.status = ProjectStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_slides")
async def generate_slides(request: GenerateSlidesRequest, db: Session = Depends(get_db)):
    """Generates PDF slides from the approved JSON script."""
    print(f"Received request to generate slides. Project ID: {request.project_id}")
    
    # Update project status if ID is provided
    project = None # Initialize project to None
    if request.project_id:
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if project:
            project.status = ProjectStatus.GENERATING_SLIDES
            db.commit()

    initial_state = {
        "json_script": request.json_script, 
        "mode": "slides_only",
        "mode": "slides_only"
    }
    
    try:
        result = await graph.ainvoke(initial_state)
        
        pdf_path = result.get("pdf_path")
        if pdf_path and os.path.exists(pdf_path):
            # Save asset to DB
            if request.project_id and project: # Ensure project exists before trying to update
                asset = Asset(
                    project_id=project.id,
                    asset_type=AssetType.SLIDES_PDF,
                    file_path=pdf_path
                )
                db.add(asset)
                project.status = ProjectStatus.SLIDES_READY
                db.commit()
                print(f"✅ Saved slides PDF for project #{request.project_id}")
            
            return JSONResponse({
                "project_id": request.project_id,
                "slides_pdf_url": f"http://127.0.0.1:8000/static/{os.path.basename(pdf_path)}",
                "pdf_path": pdf_path,
                "json_script": request.json_script
            })
        else:
            if request.project_id and project: # Ensure project exists before trying to update
                project.status = ProjectStatus.FAILED
                db.commit()
            raise HTTPException(status_code=500, detail="Failed to generate PDF slides")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_slides: {e}")
        if request.project_id and project: # Ensure project exists before trying to update
            project.status = ProjectStatus.FAILED
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_video")
async def generate_video(request: GenerateVideoRequest, db: Session = Depends(get_db)):
    """Generates the final video from the approved JSON script and existing PDF."""
    try:
        # Update project status if project_id is provided
        if request.project_id:
            project = db.query(Project).filter(Project.id == request.project_id).first()
            if project:
                project.status = ProjectStatus.GENERATING_VIDEO
                db.commit()
        
        # Pass pdf_path to the state
        initial_state = {
            "json_script": request.json_script, 
            "mode": "video_production",
            "pdf_path": request.pdf_path or "output.pdf"
        }
        result = await graph.ainvoke(initial_state)
        
        video_path = result.get("video_path")
        
        if video_path and os.path.exists(video_path):
            # Save video as an asset
            if request.project_id:
                video_asset = Asset(
                    project_id=request.project_id,
                    asset_type=AssetType.VIDEO,
                    file_path=video_path
                )
                db.add(video_asset)
                
                # Update project status to completed
                project.status = ProjectStatus.COMPLETED
                db.commit()
                print(f"✅ Project #{request.project_id} completed!")
            
            video_filename = os.path.basename(video_path)
            return JSONResponse({
                "project_id": request.project_id,
                "video_url": f"http://127.0.0.1:8000/static/{video_filename}"
            })
        else:
            if request.project_id and project:
                project.status = ProjectStatus.FAILED
                db.commit()
            raise HTTPException(status_code=500, detail="Failed to generate video")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects")
async def list_projects(db: Session = Depends(get_db)):
    """List all projects with their assets."""
    try:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
        
        result = []
        for project in projects:
            # Get assets for this project
            assets = db.query(Asset).filter(Asset.project_id == project.id).all()
            
            assets_data = []
            for asset in assets:
                assets_data.append({
                    "type": asset.asset_type.value,
                    "path": asset.file_path if asset.asset_type != AssetType.JSON_SCRIPT else "(stored in DB)",
                    "created_at": asset.created_at.isoformat()
                })
            
            result.append({
                "id": project.id,
                "title": project.title,
                "status": project.status.value,
                "outline": project.outline,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "assets": assets_data
            })
        
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/outline/{filename}")
async def download_outline(filename: str):
    """Serve outline files directly."""
    try:
        filepath = os.path.join("static", filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            filepath,
            media_type="text/markdown" if filename.endswith('.md') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ensure database tables are created on startup
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
