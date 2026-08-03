"""Voice generation route handlers."""
from fastapi import APIRouter, HTTPException, Depends
import traceback

from src.api.auth import get_current_user, TokenData
from src.services.voice_service import COMBINE_SOURCES, UnsupportedLanguageError

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
        speaker = data.get('speaker')
        pace = data.get('pace')
        
        if pace is not None:
            try:
                pace = float(pace)
            except (ValueError, TypeError):
                pace = None
        
        if not json_script:
            raise HTTPException(status_code=400, detail="json_script is required")
        
        from src.services.voice_service import generate_voice_for_script
        result = await generate_voice_for_script(
            json_script=json_script,
            project_id=project_id,
            speaker=speaker,
            pace=pace
        )
        
        print(f"✅ Voice generation complete: {result.get('generated_slides')}/{result.get('total_slides')} slides")

        return result

    except HTTPException:
        raise
    except UnsupportedLanguageError as e:
        print(f"⚠️ Voice generation rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))
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
        source: 'continuous' (default) synthesizes the script as one stream
            with as few seams as possible; 'per_slide' synthesizes each slide
            separately and stitches them, keeping every slide's file so an
            inconsistent one can be regenerated on its own
        slide_gap_seconds: Pause inserted between slides ('per_slide' only)

    Returns:
        audio_url: URL to the combined audio file
        duration_estimate: Approximate duration
        total_slides: Number of slides combined
        slide_audio_urls: Per-slide files ('per_slide' only)
    """
    print("🎤 Starting COMBINED voice generation...")

    try:
        json_script = data.get('json_script')
        project_id = data.get('project_id')
        speaker = data.get('speaker')
        pace = data.get('pace')
        source = data.get('source', COMBINE_SOURCES[0])
        slide_gap_seconds = data.get('slide_gap_seconds', 0.0)

        if pace is not None:
            try:
                pace = float(pace)
            except (ValueError, TypeError):
                pace = None

        try:
            slide_gap_seconds = max(0.0, float(slide_gap_seconds))
        except (ValueError, TypeError):
            slide_gap_seconds = 0.0

        if not json_script:
            raise HTTPException(status_code=400, detail="json_script is required")

        if source not in COMBINE_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"source must be one of: {', '.join(COMBINE_SOURCES)}"
            )

        from src.services.voice_service import generate_voice_combined
        result = await generate_voice_combined(
            json_script=json_script,
            project_id=project_id,
            speaker=speaker,
            pace=pace,
            source=source,
            slide_gap_seconds=slide_gap_seconds
        )
        
        if result.get('success'):
            print(f"✅ Combined voice generation complete: {result.get('total_slides')} slides → 1 audio file")
        else:
            print(f"⚠️ Combined voice generation failed: {result.get('error')}")

        return result

    except HTTPException:
        raise
    except UnsupportedLanguageError as e:
        print(f"⚠️ Combined voice generation rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_voice_combined: {e}")
        raise HTTPException(status_code=500, detail=str(e))
