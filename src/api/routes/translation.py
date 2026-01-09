"""Translation API endpoints for multi-language script translation."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

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


# ============================================
# ENDPOINTS
# ============================================

@router.get("/languages")
async def get_languages():
    """
    Return list of supported languages for translation.
    
    Returns:
        Dictionary of language codes to language info (name, native script)
    """
    return get_supported_languages()


@router.post("/translate")
async def translate_single(data: TranslateRequest) -> TranslationResult:
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
async def translate_batch(data: BatchTranslateRequest) -> BatchTranslateResponse:
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
    
    return BatchTranslateResponse(
        results=results,
        total_requested=len(data.languages),
        total_success=sum(1 for r in results if r.success)
    )


class ExportDocxRequest(BaseModel):
    """Request for DOCX export of translated script."""
    translated_script: dict
    language_code: str
    language_name: str


@router.post("/export_docx")
async def export_docx(data: ExportDocxRequest):
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
