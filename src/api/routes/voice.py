"""Voice generation route handlers."""
from fastapi import APIRouter, HTTPException, Depends
import traceback

from src.api.auth import get_current_user, TokenData
from src.activity.tracker import log_activity
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
        json_script = data.get('json_script') or data.get('script')
        project_id = data.get('project_id')
        speaker = data.get('speaker')
        pace = data.get('pace')
        
        if pace is not None:
            try:
                pace = float(pace)
            except (ValueError, TypeError):
                pace = None
        
        if not json_script:
            raise HTTPException(status_code=400, detail="json_script (or script) is required")
        
        from src.services.voice_service import generate_voice_for_script
        result = await generate_voice_for_script(
            json_script=json_script,
            project_id=project_id,
            speaker=speaker,
            pace=pace
        )
        
        print(f"✅ Voice generation complete: {result.get('generated_slides')}/{result.get('total_slides')} slides")

        log_activity(
            user=current_user,
            activity_type="voice_generation",
            detail=f"Generated {result.get('generated_slides', 0)}/{result.get('total_slides', 0)} slides voice",
            status="completed" if result.get("success") else "failed",
            metadata={"project_id": project_id, "duration": result.get("duration_estimate")},
        )

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
        speaker: Voice actor (default: priya)
        pace: Speed multiplier (default: 0.9)
        language_code: Target language (default: en-IN)
        slide_gap_seconds: Silence between slides (default: 0.6)

    Returns:
        {
            "audio_url": "/output/audio/.../full_narration.wav",
            "zip_url": "/output/audio/.../narration.zip",
            "slide_audio_urls": {"1": "...", "2": "..."},
            "duration_seconds": 125.4,
            "duration_estimate": "2:05",
            "total_slides": 4,
            "success": True
        }
    """
    json_script = data.get("json_script") or data.get("script")
    if not json_script:
        raise HTTPException(status_code=400, detail="json_script (or script) is required")

    project_id = data.get("project_id")
    source = data.get("source", "continuous")
    speaker = data.get("speaker")
    pace = data.get("pace")
    language_code = data.get("language_code") or data.get("language")
    slide_gap_seconds = data.get("slide_gap_seconds", 0.6)

    if source not in COMBINE_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source: {source!r}. Must be one of: {COMBINE_SOURCES}",
        )

    if pace is not None:
        try:
            pace = float(pace)
        except (ValueError, TypeError):
            pace = None

    try:
        slide_gap_seconds = max(0.0, float(slide_gap_seconds))
    except (ValueError, TypeError):
        slide_gap_seconds = 0.6

    try:
        from src.services.voice_service import generate_voice_combined
        result = await generate_voice_combined(
            json_script=json_script,
            project_id=project_id,
            source=source,
            speaker=speaker,
            pace=pace,
            language_code=language_code,
            slide_gap_seconds=slide_gap_seconds,
        )

        if result.get("success"):
            print(f"✅ Combined voice generation complete: {result.get('audio_url')}")
        else:
            print(f"⚠️ Combined voice generation failed: {result.get('error')}")

        log_activity(
            user=current_user,
            activity_type="voice_generation_combined",
            detail=f"Combined voice ({result.get('total_slides', 0)} slides)",
            status="completed" if result.get("success") else "failed",
            metadata={"project_id": project_id, "duration": result.get("duration_estimate")},
        )

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


@router.post("/generate_voice_patch")
async def generate_voice_patch_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Generate a standalone audio patch for an arbitrary sentence or word.
    Does not require a slide deck or full script structure.

    Args:
        data: {
            "text": "...",
            "speaker": "priya",        # optional
            "pace": 0.85,              # optional
            "language_code": "en-IN",  # optional
            "patch_id": "..."          # optional
        }

    Returns:
        {
            "audio_url": "/output/audio/patches/patch_....wav",
            "success": True,
            "duration_seconds": 3.2,
            "duration_estimate": "0:03",
            "text": "...",
            "speaker": "priya",
            "pace": 0.85,
            "word_count": 7
        }
    """
    print("🎤 Starting voice patch generation...")
    text = data.get("text")
    if not text or not str(text).strip():
        raise HTTPException(status_code=400, detail="text is required and must not be empty")

    speaker = data.get("speaker")
    pace = data.get("pace")
    language_code = data.get("language_code") or data.get("language") or "en-IN"
    patch_id = data.get("patch_id")

    if pace is not None:
        try:
            pace = float(pace)
        except (ValueError, TypeError):
            pace = None

    try:
        from src.services.voice_service import generate_voice_patch
        result = await generate_voice_patch(
            text=str(text),
            speaker=speaker,
            pace=pace,
            language_code=language_code,
            patch_id=patch_id,
        )

        log_activity(
            user=current_user,
            activity_type="voice_patch",
            detail=f"Patch: {str(text)[:60]}",
            status="completed" if result.get("success") else "failed",
            metadata={"speaker": speaker, "pace": pace, "patch_id": result.get("patch_id")},
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnsupportedLanguageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in generate_voice_patch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate_slide")
async def regenerate_slide_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Regenerate the audio for a SINGLE slide and stitch it back into full_narration.wav.

    Args:
        data: {
            "project_id": "...",
            "slide_number": 2,          # aliases: slide_num, row, row_number
            "text": "...",              # aliases: narration
            "speaker": "priya",        # optional
            "pace": 0.9,               # optional
            "language_code": "en-IN",  # optional
            "slide_gap_seconds": 0.0   # optional
        }
    """
    print("🎤 Starting single slide regeneration...")
    raw_project_id = data.get("project_id") or data.get("projectId")
    project_id = str(raw_project_id).replace("project_", "").strip() if raw_project_id else None

    raw_slide_num = (
        data.get("slide_number")
        if data.get("slide_number") is not None
        else (
            data.get("slide_num")
            if data.get("slide_num") is not None
            else (
                data.get("row")
                if data.get("row") is not None
                else data.get("row_number")
            )
        )
    )
    try:
        slide_number = int(raw_slide_num) if raw_slide_num is not None else None
    except (ValueError, TypeError):
        slide_number = None

    text = data.get("text") or data.get("narration")

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    if slide_number is None:
        raise HTTPException(status_code=400, detail="slide_number is required")

    if not text:
        raise HTTPException(status_code=400, detail="text (or narration) is required")

    speaker = data.get("speaker")
    pace = data.get("pace")
    language_code = data.get("language_code") or data.get("language")
    slide_gap_seconds = data.get("slide_gap_seconds", 0.0)

    if pace is not None:
        try:
            pace = float(pace)
        except (ValueError, TypeError):
            pace = None

    try:
        slide_gap_seconds = max(0.0, float(slide_gap_seconds))
    except (ValueError, TypeError):
        slide_gap_seconds = 0.0

    try:
        from src.services.voice_service import regenerate_slide_audio
        result = await regenerate_slide_audio(
            project_id=project_id,
            slide_number=slide_number,
            text=str(text),
            speaker=speaker,
            pace=pace,
            language_code=language_code,
            slide_gap_seconds=slide_gap_seconds,
        )

        log_activity(
            user=current_user,
            activity_type="regenerate_slide",
            detail=f"Row {slide_number} (project {project_id})",
            status="completed" if result.get("success") else "failed",
            metadata={"project_id": project_id, "slide_number": slide_number},
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnsupportedLanguageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in regenerate_slide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


