"""
Slides Translation API Route.

Endpoint for translating .tex Beamer files to different languages.
"""

import logging
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

from src.api.auth import get_current_user, TokenData
from src.services.slides_translation_service import (
    translate_slides,
    get_supported_languages,
    LANGUAGE_CONFIG,
    SlidesTranslationResult
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Slides Translation"])

# Get project root for output directory
project_root = Path(__file__).parent.parent.parent.parent


@router.get("/slides-translation/languages")
async def get_languages():
    """Get list of supported languages for slides translation."""
    return get_supported_languages()


@router.post("/translate_slides")
async def translate_slides_endpoint(
    file: UploadFile = File(..., description="The .tex file to translate"),
    target_language: str = Form(..., description="Target language code (e.g., 'hi', 'ta', 'te')"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Translate a .tex Beamer file to a target language.
    
    The translated file will:
    - Have all human-readable text translated
    - Keep all LaTeX commands intact
    - Include XeLaTeX packages for Unicode font support
    - Be saved with the language code suffix (e.g., tutorial_hi.tex)
    
    Args:
        file: The .tex file to translate
        target_language: Language code (hi, ta, te, mr, bn, gu, kn, ml, pa, or, as)
    
    Returns:
        filename: Name of the translated file
        download_url: URL to download the translated .tex
        language_name: Full language name (e.g., "Hindi")
        language_native: Language name in native script (e.g., "हिंदी")
        font_name: Required font for compilation
    """
    logger.info(f"🎯 Translate slides request: {file.filename} -> {target_language}")
    
    # Validate file type
    if not file.filename.endswith('.tex'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a .tex file."
        )
    
    # Validate language
    if target_language not in LANGUAGE_CONFIG:
        supported = list(LANGUAGE_CONFIG.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {target_language}. Supported: {supported}"
        )
    
    try:
        # Read file content
        content = await file.read()
        tex_content = content.decode('utf-8')
        
        logger.info(f"📄 Read {len(tex_content)} characters from {file.filename}")
        
        # Set up output directory
        output_dir = project_root / "output" / "slides" / "translated"
        
        # Translate
        result: SlidesTranslationResult = await translate_slides(
            tex_content=tex_content,
            target_language=target_language,
            original_filename=file.filename,
            output_dir=output_dir
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {result.error}"
            )
        
        logger.info(f"✅ Translation complete: {result.filename}")
        
        return {
            "success": True,
            "filename": result.filename,
            "download_url": result.download_url,
            "language_code": result.language_code,
            "language_name": result.language_name,
            "language_native": result.language_native,
            "font_name": result.font_name,
            "compile_command": "xelatex"
        }
        
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid file encoding. The .tex file must be UTF-8 encoded."
        )
    except Exception as e:
        logger.error(f"❌ Translation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )
