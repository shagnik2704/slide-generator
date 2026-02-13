"""Image generation and prompt enhancement route handlers."""
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from pathlib import Path
import time
import traceback

from src.api.auth import get_current_user, TokenData

router = APIRouter(tags=["images"])


@router.post("/enhance_prompts")
async def enhance_prompts_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Enhance visual cues from a script into detailed image generation prompts.
    
    Args:
        json_script: The parsed script JSON with slides containing image_prompt fields
        project_id: Optional project ID for tracking
    
    Returns:
        enhanced_prompts: List of {slide_number, title, original, enhanced, skip_reason}
    """
    print("🎨 Enhancing visual prompts...")
    
    try:
        json_script = data.get('json_script')
        project_id = data.get('project_id')
        
        if not json_script:
            raise HTTPException(status_code=400, detail="json_script is required")
        
        from src.services.prompt_enhancer import enhance_prompts
        result = enhance_prompts(json_script, project_id)
        
        print(f"✅ Enhanced {result.get('enhanced_count', 0)} prompts, skipped {result.get('skipped_count', 0)}")
        
        return result
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in enhance_prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_reference_image")
async def upload_reference_image(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    slide_number: int = Form(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Upload a reference image for image-to-image generation.
    
    Returns the path where the image was saved.
    """
    print(f"📎 Uploading reference image for slide {slide_number}...")
    
    try:
        # Create reference images directory
        project_root = Path(__file__).parent.parent.parent.parent
        ref_dir = project_root / "output" / "images" / str(project_id) / "references"
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the file
        file_ext = Path(file.filename).suffix or ".png"
        ref_path = ref_dir / f"slide_{slide_number}_ref{file_ext}"
        
        content = await file.read()
        with open(ref_path, "wb") as f:
            f.write(content)
        
        print(f"  ✓ Saved reference image: {ref_path}")
        
        return {"path": str(ref_path), "slide_number": slide_number}
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in upload_reference_image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate_images")
async def generate_images_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Generate images from approved prompts.
    
    Args:
        project_id: Project ID for file naming
        prompts: List of {slide_number, prompt} objects
        aspect_ratio: Optional, defaults to "1:1"
    
    Returns:
        images: List of {slide_number, url, success}
        zip_url: URL to download all images as ZIP
    """
    print("🖼️ Generating images from prompts...")
    
    try:
        project_id = data.get('project_id')
        prompts = data.get('prompts', [])
        aspect_ratio = data.get('aspect_ratio', '1:1')
        
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        
        if not prompts:
            raise HTTPException(status_code=400, detail="prompts list is required")
        
        from src.services.image_service import generate_images
        result = generate_images(prompts, project_id, aspect_ratio)
        
        print(f"✅ Generated {result.get('generated', 0)} images, {result.get('failed', 0)} failed")
        
        return result
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_images: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/modify_image')
async def modify_image_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Modify an existing generated image with a new prompt.
    
    Args:
        project_id: Project ID
        slide_number: Row number
        sentence_index: Sentence index
        modification_prompt: The change you want to make (e.g., "change background to forest")
        base_image_url: URL of the existing image to modify (e.g., "/output/images/123/row_5_sent_2.png")
        aspect_ratio: Optional, defaults to "16:9"
    
    Returns:
        success: Boolean indicating if modification was successful
        url: URL of the modified image
        timestamp: Cache-busting timestamp
    """
    print("Modifying existing image...")
    
    try:
        project_id = data.get('project_id')
        slide_number = data.get('slide_number')
        sentence_index = data.get('sentence_index')
        modification_prompt = data.get('modification_prompt')
        base_image_url = data.get('base_image_url')
        aspect_ratio = data.get('aspect_ratio', '16:9')
        
        # Validate inputs
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        if slide_number is None:
            raise HTTPException(status_code=400, detail="slide_number is required")
        if sentence_index is None:
            raise HTTPException(status_code=400, detail="sentence_index is required")
        if not modification_prompt:
            raise HTTPException(status_code=400, detail="modification_prompt is required")
        if not base_image_url:
            raise HTTPException(status_code=400, detail="base_image_url is required")
        
        # Convert URL to file path
        # e.g., "/output/images/123/row_5_sent_2.png" -> "output/images/123/row_5_sent_2.png"
        project_root = Path(__file__).parent.parent.parent.parent
        base_image_path = project_root / base_image_url.lstrip('/')
        
        if not base_image_path.exists():
            raise HTTPException(status_code=404, detail=f"Base image not found: {base_image_url}")
        
        print(f"Base image: {base_image_path.name}")
        print(f"Modification: {modification_prompt[:60]}...")
        
        from src.services.image_service import modify_existing_image
        
        success = modify_existing_image(
            base_image_path=base_image_path,
            modification_prompt=modification_prompt,
            output_path=base_image_path,  
            aspect_ratio=aspect_ratio
        )
        
        if success:
            print(f"Image modified successfully")
            return {
                "success": True,
                "url": base_image_url,
                "timestamp": int(time.time()),  
                "message": "Image modified successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to modify image")
            
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in modify_image: {e}")
        raise HTTPException(status_code=500, detail=str(e))
