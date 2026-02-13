"""Quality check route handlers."""
from fastapi import APIRouter, HTTPException, Depends
import traceback

from src.api.auth import get_current_user, TokenData

router = APIRouter(tags=["quality"])


@router.post("/check_quality")
async def check_quality_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Run quality checks and translate script to target language.
    
    Uses back-translation method (English → Language → English) to verify translation quality.
    
    Args (in data):
        json_script: The script JSON to check
        language_code: Target language code ('hi', 'ta', 'te', etc). Defaults to 'hi' (Hindi)
    
    Returns:
        - Quality check results (translation quality, timing, transliteration)
        - Full translated script in target language
        - Language info (code, name, native script)
    """
    language_code = data.get('language_code', 'hi')
    print(f"Running quality checks with {language_code} translation...")
    
    try:
        json_script = data.get('json_script')
        
        if not json_script:
            raise HTTPException(status_code=400, detail="json_script is required")
        
        from src.services.quality_service import check_quality
        result = await check_quality(json_script, language_code)
        
        summary = result.get('summary', {})
        lang_name = result.get('language_name', 'Unknown')
        print(f"✅ Quality check complete ({lang_name}): {summary.get('ai_passed', 0)}/{summary.get('total', 0)} passed")
        print(f"📊 Avg translation quality: {summary.get('avg_quality_score', 0)}/5")
        
        return result
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in check_quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch_check_quality")
async def batch_check_quality_endpoint(data: dict, current_user: TokenData = Depends(get_current_user)):
    """
    Run quality checks for multiple scripts in parallel.
    
    Args (in data):
        scripts: List of script JSON objects to check
        language_code: Target language code for all scripts. Defaults to 'hi' (Hindi)
    
    Returns:
        results: List of quality check results (one per script)
        batch_summary: Overall batch statistics
    """
    language_code = data.get('language_code', 'hi')
    print(f"📋 Batch quality check requested ({language_code})...")
    
    try:
        scripts = data.get('scripts', [])
        
        if not scripts:
            raise HTTPException(status_code=400, detail="scripts list is required")
        
        print(f"   Processing {len(scripts)} scripts...")
        
        from src.services.quality_service import batch_check_quality
        result = await batch_check_quality(scripts, language_code)
        
        summary = result.get('batch_summary', {})
        print(f"✅ Batch quality check complete: {summary.get('scripts_passed', 0)}/{summary.get('total_scripts', 0)} passed")
        
        return result
        
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR in batch_check_quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))
