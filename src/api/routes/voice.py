"""Voice generation route handlers."""
from fastapi import APIRouter, HTTPException, Depends
import traceback

from src.api.auth import get_current_user, TokenData

router = APIRouter(tags=["voice"])


@router.post("/generate_voice")
async def generate_voice_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Generate voice narration for a JSON script.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID (auto-generated if not provided)
    
    Returns:
        audio_urls: Per-slide audio file URLs
        zip_url: URL to download all audio as ZIP
    """
    print("🎤 Starting voice generation...")
    
    try:
        json_script = data.get('json_script')
        project_id = data.get('project_id')
        
        if not json_script:
            raise HTTPException(status_code=400, detail="json_script is required")
        
        from src.services.voice_service import generate_voice_for_script
        result = await generate_voice_for_script(
            json_script=json_script,
            project_id=project_id,
        )
        
        print(f"✅ Voice generation complete: {result.get('generated_slides')}/{result.get('total_slides')} slides")
        
        return result
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate_voice_combined")
async def generate_voice_combined_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Generate a SINGLE audio file for the entire script.
    
    Combines all slide narrations with pauses into one continuous audio file.
    Useful for creating full tutorial audio in one go.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID (auto-generated if not provided)
    
    Returns:
        audio_url: URL to the combined audio file
        duration_estimate: Approximate duration
        total_slides: Number of slides combined
    """
    print("🎤 Starting COMBINED voice generation...")
    
    try:
        json_script = data.get('json_script')
        project_id = data.get('project_id')
        
        if not json_script:
            raise HTTPException(status_code=400, detail="json_script is required")
        
        from src.services.voice_service import generate_voice_combined
        result = await generate_voice_combined(
            json_script=json_script,
            project_id=project_id,
        )
        
        if result.get('success'):
            print(f"✅ Combined voice generation complete: {result.get('total_slides')} slides → 1 audio file")
        else:
            print(f"⚠️ Combined voice generation failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_voice_combined: {e}")
        raise HTTPException(status_code=500, detail=str(e))
