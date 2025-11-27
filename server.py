from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union, Optional
import os
from agent import graph

app = FastAPI(title="Slide Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files to serve generated content
app.mount("/static", StaticFiles(directory="."), name="static")

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
    outline: str

class GenerateVideoRequest(BaseModel):
    json_script: dict
    pdf_path: Optional[str] = None # Added pdf_path

@app.post("/generate_script")
async def generate_script(request: GenerateScriptRequest):
    """Generates a script PDF from the outline."""
    try:
        print(f"DEBUG: Received generate_script request with outline: '{request.outline}'")
        initial_state = {"outline": request.outline, "mode": "script_only"}
        result = await graph.ainvoke(initial_state)
        
        script_pdf_path = result.get("script_pdf_path")
        json_script = result.get("json_script")
        
        if script_pdf_path and os.path.exists(script_pdf_path):
            # Return URL to the PDF and the JSON script for the next step
            return JSONResponse({
                "script_pdf_url": f"http://127.0.0.1:8000/static/{script_pdf_path}",
                "json_script": json_script
            })
        else:
            print(f"ERROR: Failed to generate script PDF. Result keys: {result.keys()}")
            raise HTTPException(status_code=500, detail="Failed to generate script PDF")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in generate_script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_slides")
async def generate_slides(request: GenerateVideoRequest):
    """Generates slides PDF from the approved JSON script."""
    try:
        initial_state = {"json_script": request.json_script, "mode": "slides_only"}
        result = await graph.ainvoke(initial_state)
        
        pdf_path = result.get("pdf_path")
        
        if pdf_path and os.path.exists(pdf_path):
            return JSONResponse({
                "slides_pdf_url": f"http://127.0.0.1:8000/static/{pdf_path}",
                "pdf_path": pdf_path, # Return raw path for next step
                "json_script": request.json_script
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to generate slides PDF")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_video")
async def generate_video(request: GenerateVideoRequest):
    """Generates the final video from the approved JSON script and existing PDF."""
    try:
        # Pass pdf_path to the state
        initial_state = {
            "json_script": request.json_script, 
            "mode": "video_production",
            "pdf_path": request.pdf_path or "output.pdf" # Fallback to default if missing
        }
        result = await graph.ainvoke(initial_state)
        
        video_path = result.get("video_path")
        
        if video_path and os.path.exists(video_path):
            # Use basename to avoid absolute path issues with StaticFiles mounted on "."
            video_filename = os.path.basename(video_path)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
