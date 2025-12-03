from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union, Optional
import os
import json
from agent import graph
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
    content: List[Union[str, dict]]

class GenerateScriptRequest(BaseModel):
    topic: Optional[str] = None  # Either topic OR outline must be provided
    outline: Optional[str] = None  # Pre-generated outline
    title: Optional[str] = None
    target_audience: Optional[str] = None
    mode: Optional[str] = "script_only"

class GenerateOutlineRequest(BaseModel):
    topic: str
    target_audience: Optional[str] = None

class GenerateVideoRequest(BaseModel):
    json_script: dict
    pdf_path: Optional[str] = None

class GenerateSlidesRequest(BaseModel):
    json_script: dict

@app.post("/generate_outline")
async def generate_outline(request: GenerateOutlineRequest):
    try:
        # Run the agent to generate outline
        inputs = {
            "topic": request.topic,
            "mode": "outline_only"
        }
        
        result = await graph.ainvoke(inputs)
        
        outline_text = result.get("outline", "")
        
        # Generate a simple project ID (timestamp-based)
        import time
        project_id = int(time.time())
        
        # Generate Markdown file from outline
        docx_path = create_outline_docx(outline_text, project_id)
        outline_url = f"/download/outline/{os.path.basename(docx_path)}"
        
        return {
            "outline": outline_text,
            "outline_docx_url": outline_url,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_outline")
async def upload_outline(file: UploadFile = File(...)):
    """Upload an edited outline file (.md or .docx)."""
    try:
        # Validate file type
        if not (file.filename.endswith('.md') or file.filename.endswith('.docx') or file.filename.endswith('.txt')):
            raise HTTPException(status_code=400, detail="Only .md, .txt, or .docx files are allowed")
        
        # Save uploaded file temporarily
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        import time
        temp_path = os.path.join(upload_dir, f"outline_{int(time.time())}_{file.filename}")
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse the document
        outline_text = parse_docx_outline(temp_path)
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "outline": outline_text,
            "message": "Outline uploaded successfully"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in upload_outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_script")
async def generate_script(request: GenerateScriptRequest):
    """Generates a presentation script. If topic is provided, generates outline first."""
    
    # Validate that either topic or outline is provided
    if not request.topic and not request.outline:
        raise HTTPException(status_code=400, detail="Either 'topic' or 'outline' must be provided")
    
    print(f"Received request to generate script. Topic: {request.topic}, Has outline: {bool(request.outline)}")

    try:
        # STEP 1: Generate outline if only topic is provided
        outline_text = request.outline
        
        if not outline_text and request.topic:
            print(f"🔍 Step 1: Generating outline for topic: {request.topic}")
            outline_state = {
                "topic": request.topic,
                "mode": "outline_only"
            }
            
            outline_result = await graph.ainvoke(outline_state)
            outline_text = outline_result.get("outline", "")
            
            if not outline_text:
                raise HTTPException(status_code=500, detail="Failed to generate outline")
            
            print(f"✓ Outline generated successfully ({len(outline_text)} chars)")
        
        # STEP 2: Generate script from outline
        print(f"📝 Step 2: Generating script from outline...")
        
        initial_state = {
            "outline": outline_text,
            "mode": getattr(request, 'mode', 'script_only'),
            "target_audience": request.target_audience,
            "evaluation_iteration": 0,
            "evaluation_passed": False,
            "evaluation_feedback": None
        }
        
        result = await graph.ainvoke(initial_state)
        
        script_pdf_path = result.get("script_pdf_path")
        json_script = result.get("json_script")
        
        if script_pdf_path:
            # Generate simple project ID
            import time
            project_id = int(time.time())
            
            # Save JSON script
            json_path = f"script_{project_id}.json"
            with open(json_path, 'w') as f:
                json.dump(json_script, f, indent=2)
            
            print(f"✅ Saved script PDF and JSON for project #{project_id}")
            
            return JSONResponse({
                "script_pdf_url": f"/static/{os.path.basename(script_pdf_path)}",
                "json_script": json_script,
                "outline": outline_text
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to generate script PDF")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_slides")
async def generate_slides(request: GenerateSlidesRequest):
    """Generates PDF slides from the approved JSON script."""
    print(f"Received request to generate slides")

    initial_state = {
        "json_script": request.json_script, 
        "mode": "slides_only"
    }
    
    try:
        result = await graph.ainvoke(initial_state)
        
        pdf_path = result.get("pdf_path")
        if pdf_path and os.path.exists(pdf_path):
            print(f"✅ Generated slides PDF")
            
            return JSONResponse({
                "slides_pdf_url": f"http://127.0.0.1:8000/static/{os.path.basename(pdf_path)}",
                "pdf_path": pdf_path,
                "json_script": request.json_script
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to generate PDF slides")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_slides: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_video")
async def generate_video(request: GenerateVideoRequest):
    """Generates the final video from the approved JSON script and existing PDF."""
    try:
        # Pass pdf_path to the state
        initial_state = {
            "json_script": request.json_script, 
            "mode": "video_production",
            "pdf_path": request.pdf_path or "output.pdf"
        }
        result = await graph.ainvoke(initial_state)
        
        video_path = result.get("video_path")
        
        if video_path and os.path.exists(video_path):
            video_filename = os.path.basename(video_path)
            print(f"✅ Generated video: {video_filename}")
            
            return JSONResponse({
                "video_url": f"http://127.0.0.1:8000/static/{video_filename}"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to generate video")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_video: {e}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
