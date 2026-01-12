"""Translation API endpoints for multi-language script translation."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from src.api.auth import get_current_user, TokenData
from src.services.translation_service import (
    translate_script,
    batch_translate,
    get_supported_languages,
    TranslationResult
)

router = APIRouter(prefix="/translation", tags=["translation"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class TranslateRequest(BaseModel):
    """Request for single-language translation."""
    json_script: dict
    target_language: str
    translate_visual_cues: bool = True
    project_id: Optional[str] = None


class BatchTranslateRequest(BaseModel):
    """Request for multi-language translation."""
    json_script: dict
    languages: List[str]
    translate_visual_cues: bool = True
    project_id: Optional[str] = None


class BatchTranslateResponse(BaseModel):
    """Response for batch translation."""
    results: List[TranslationResult]
    total_requested: int
    total_success: int
    project_id: Optional[int] = None

class UpdateCellRequest(BaseModel):
    """Request to update a single translation cell."""
    slide_id: int
    language_code: str
    text: Optional[str] = None
    visual_cue: Optional[str] = None

class GenerateAudioRequest(BaseModel):
    """Request to generate audio for a specific translation cell."""
    translation_id: int


# ============================================
# ENDPOINTS
# ============================================

@router.get("/languages")
async def get_languages(current_user: TokenData = Depends(get_current_user)):
    """
    Return list of supported languages for translation.
    
    Returns:
        Dictionary of language codes to language info (name, native script)
    """
    return get_supported_languages()


@router.post("/translate")
async def translate_single(data: TranslateRequest, current_user: TokenData = Depends(get_current_user)) -> TranslationResult:
    """
    Translate a script to a single target language.
    
    Args:
        data: TranslateRequest with script and target language
    
    Returns:
        TranslationResult with translated script or error
    """
    result = await translate_script(
        json_script=data.json_script,
        target_language=data.target_language,
        translate_visual_cues=data.translate_visual_cues
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return result


@router.post("/batch_translate")
async def translate_batch(data: BatchTranslateRequest, current_user: TokenData = Depends(get_current_user)) -> BatchTranslateResponse:
    """
    Translate a script to multiple languages in parallel.
    
    Args:
        data: BatchTranslateRequest with script and list of languages
    
    Returns:
        BatchTranslateResponse with results for each language
    """
    if not data.languages:
        raise HTTPException(status_code=400, detail="No languages provided")
    
    results = await batch_translate(
        json_script=data.json_script,
        languages=data.languages,
        translate_visual_cues=data.translate_visual_cues
    )
    
    # Persist to DB
    from src.services.database import save_project_results
    project_id = None
    try:
        project_id = save_project_results(data.json_script, results)
        print(f"🏠 Project and translations saved to DB with ID: {project_id}")
    except Exception as e:
        print(f"⚠️ Warning: Failed to save results to DB: {e}")
    
    return BatchTranslateResponse(
        results=results,
        total_requested=len(data.languages),
        total_success=sum(1 for r in results if r.success),
        project_id=project_id
    )

@router.post("/update_cell")
async def update_cell(data: UpdateCellRequest):
    """Update a specific cell in the translation grid."""
    from src.services.database import update_translation_cell
    success = update_translation_cell(
        slide_id=data.slide_id,
        language_code=data.language_code,
        text=data.text,
        visual_cue=data.visual_cue
    )
    if not success:
        raise HTTPException(status_code=404, detail="Cell not found")
    return {"status": "success"}

@router.get("/project_data/{project_id}")
async def get_project_data(project_id: int):
    """Retrieve the flattened grid data for a project."""
    from src.services.database import get_project_grid_data
    data = get_project_grid_data(project_id)
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")
    return data

@router.post("/generate_cell_audio")
async def generate_cell_audio(data: GenerateAudioRequest):
    """
    Generate audio for a specific translation cell.
    
    1. Looks up the text from the database
    2. Generates audio using TTS
    3. Saves audio file and updates database with URL
    """
    from pathlib import Path
    from src.services.database import get_translation_by_id, update_translation_audio
    from src.services.voice_service import generate_voice_for_slide
    
    # 1. Get the translation text
    translation = get_translation_by_id(data.translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    text = translation["text"]
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="No text to generate audio for")
    
    # 2. Generate audio
    output_dir = Path(__file__).parent.parent.parent.parent / "output" / "cell_audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use translation_id as the identifier for the audio file
    audio_path = await generate_voice_for_slide(
        text=text,
        slide_num=data.translation_id,  # Using translation_id for unique naming
        output_dir=output_dir
    )
    
    if not audio_path:
        raise HTTPException(status_code=500, detail="Failed to generate audio")
    
    # 3. Update database with audio URL
    audio_url = f"/output/cell_audio/{Path(audio_path).name}"
    update_translation_audio(data.translation_id, audio_url)
    
    return {
        "status": "success",
        "audio_url": audio_url,
        "translation_id": data.translation_id
    }


class ExportDocxRequest(BaseModel):
    """Request for DOCX export of translated script."""
    translated_script: dict
    language_code: str
    language_name: str


@router.post("/export_docx")
async def export_docx(data: ExportDocxRequest, current_user: TokenData = Depends(get_current_user)):
    """
    Export a translated script to DOCX in proper script format.
    Uses the same format as the main docx_service (Visual Cue | Narration).
    Only includes the regional language content, not English.
    
    Args:
        data: ExportDocxRequest with translated script and language info
    
    Returns:
        StreamingResponse with the DOCX file
    """
    from src.services.docx_service import json_to_docx
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    script = data.translated_script
    lang_code = data.language_code
    lang_name = data.language_name
    
    # Transform the translated script to use regional language as the main content
    translated_json = {
        "presentation_title": f"{script.get('title', script.get('presentation_title', 'Translated Script'))} ({lang_name})",
        "module": script.get("module", ""),
        "episode": script.get("episode", ""),
        "duration": script.get("duration", ""),
        "learning_objectives": script.get("learning_objectives", []),
        "prerequisites": script.get("prerequisites", ""),
        "meta_tags": script.get("meta_tags", []),
        "slides": []
    }
    
    # Transform slides to use regional language
    narration_key = f"narration_{lang_code}"
    visual_cue_key = f"visual_cue_{lang_code}"
    
    for slide in script.get("slides", []):
        translated_slide = {
            "slide_number": slide.get("slide_number"),
            "title": slide.get("title", ""),
            # Use translated narration, fallback to original
            "narration": slide.get(narration_key, slide.get("narration", "")),
            # Use translated visual cue, fallback to original
            "visual_cue": slide.get(visual_cue_key, slide.get("visual_cue", "")),
            "image_prompt": slide.get(visual_cue_key, slide.get("visual_cue", slide.get("image_prompt", "")))
        }
        translated_json["slides"].append(translated_slide)
    
    # Use existing json_to_docx to generate proper format
    buffer = json_to_docx(translated_json)
    
    # Return as downloadable file with explicit CORS headers
    filename = f"script_{lang_code}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
