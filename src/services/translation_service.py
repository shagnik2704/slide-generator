"""
Multi-language translation service for Spoken Tutorial scripts.
Supports batch translation to multiple Indian languages.
"""
import asyncio
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI


# ============================================
# PYDANTIC MODELS
# ============================================

class TranslatedSlide(BaseModel):
    """A single translated slide."""
    slide_number: int = Field(description="Slide number")
    narration: str = Field(description="Translated narration")
    visual_cue: Optional[str] = Field(default=None, description="Translated visual cue")


class TranslationBatch(BaseModel):
    """Batch of translated slides."""
    slides: List[TranslatedSlide] = Field(description="All translated slides")


class TranslationResult(BaseModel):
    """Result of translating to a single language."""
    language: str
    language_code: str
    language_native: str
    translated_script: dict
    success: bool
    error: Optional[str] = None


# ============================================
# SUPPORTED LANGUAGES
# ============================================

SUPPORTED_LANGUAGES = {
    "hi": {"name": "Hindi", "native": "हिंदी"},
    "ta": {"name": "Tamil", "native": "தமிழ்"},
    "te": {"name": "Telugu", "native": "తెలుగు"},
    "mr": {"name": "Marathi", "native": "मराठी"},
    "bn": {"name": "Bengali", "native": "বাংলা"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી"},
    "ml": {"name": "Malayalam", "native": "മലയാളം"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
    "or": {"name": "Odia", "native": "ଓଡ଼ିଆ"},
    "as": {"name": "Assamese", "native": "অসমীয়া"},
}


# ============================================
# TRANSLATION SERVICE
# ============================================

async def translate_script(
    json_script: dict,
    target_language: str,
    translate_visual_cues: bool = True
) -> TranslationResult:
    """
    Translate a script to a target language.
    
    Args:
        json_script: The parsed script JSON with slides
        target_language: Language code (e.g., 'hi', 'ta', 'te')
        translate_visual_cues: Whether to also translate visual cues
    
    Returns:
        TranslationResult with translated script or error
    """
    if target_language not in SUPPORTED_LANGUAGES:
        return TranslationResult(
            language=target_language,
            language_code=target_language,
            language_native="Unknown",
            translated_script={},
            success=False,
            error=f"Unsupported language: {target_language}"
        )
    
    lang_info = SUPPORTED_LANGUAGES[target_language]
    lang_name = lang_info["name"]
    lang_native = lang_info["native"]
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
    )
    
    slides = json_script.get("slides", [])
    if not slides:
        return TranslationResult(
            language=lang_name,
            language_code=target_language,
            language_native=lang_native,
            translated_script={},
            success=False,
            error="No slides found in script"
        )
    
    print(f"🌐 Translating to {lang_name} ({lang_native})...")
    
    try:
        # Build content to translate
        content_to_translate = []
        for i, slide in enumerate(slides):
            item = {
                "slide_number": slide.get("slide_number", i + 1),
                "narration": slide.get("narration", "")
            }
            if translate_visual_cues and slide.get("visual_cue"):
                item["visual_cue"] = slide.get("visual_cue", "")
            content_to_translate.append(item)
        
        # Build prompt
        visual_cue_instruction = ""
        if translate_visual_cues:
            visual_cue_instruction = "- Also translate the visual_cue field if present"
        
        prompt = f"""You are an expert English-to-{lang_name} translator for Spoken Tutorial scripts.
        IMPORTANT: Preserve **bold** markers exactly. Transliterate the content inside **markers** to {lang_native} script.(e.g., Python → पायथन, Terminal → టెర్మినల్)
{visual_cue_instruction}

**Content to translate:**
{json.dumps(content_to_translate, indent=2, ensure_ascii=False)}

Return the {lang_name} translation for each slide. Include both narration and visual_cue if present."""

        # Call LLM with structured output
        translation_llm = llm.with_structured_output(TranslationBatch)
        result = await translation_llm.ainvoke(prompt)
        
        if not result or not result.slides:
            return TranslationResult(
                language=lang_name,
                language_code=target_language,
                language_native=lang_native,
                translated_script={},
                success=False,
                error="Translation returned empty result"
            )
        
        # Create translated script by copying original and adding translations
        translated_script = json_script.copy()
        translated_slides = []
        
        # Build lookup from result
        translation_lookup = {s.slide_number: s for s in result.slides}
        
        for i, slide in enumerate(slides):
            slide_num = slide.get("slide_number", i + 1)
            translated_slide = slide.copy()
            
            if slide_num in translation_lookup:
                trans = translation_lookup[slide_num]
                translated_slide[f"narration_{target_language}"] = trans.narration
                if trans.visual_cue:
                    translated_slide[f"visual_cue_{target_language}"] = trans.visual_cue
            
            translated_slides.append(translated_slide)
        
        translated_script["slides"] = translated_slides
        translated_script["target_language"] = target_language
        translated_script["target_language_name"] = lang_name
        translated_script["target_language_native"] = lang_native
        
        print(f"   ✓ Translated {len(result.slides)} slides to {lang_name}")
        
        return TranslationResult(
            language=lang_name,
            language_code=target_language,
            language_native=lang_native,
            translated_script=translated_script,
            success=True
        )
        
    except Exception as e:
        print(f"   ❌ Translation failed: {e}")
        return TranslationResult(
            language=lang_name,
            language_code=target_language,
            language_native=lang_native,
            translated_script={},
            success=False,
            error=str(e)
        )


async def batch_translate(
    json_script: dict,
    languages: List[str],
    translate_visual_cues: bool = True
) -> List[TranslationResult]:
    """
    Translate a script to multiple languages in parallel.
    
    Args:
        json_script: The parsed script JSON with slides
        languages: List of language codes (e.g., ['hi', 'ta', 'te'])
        translate_visual_cues: Whether to also translate visual cues
    
    Returns:
        List of TranslationResult, one per language
    """
    # Filter to only supported languages
    valid_languages = [lang for lang in languages if lang in SUPPORTED_LANGUAGES]
    
    if not valid_languages:
        return [TranslationResult(
            language="Unknown",
            language_code="",
            language_native="",
            translated_script={},
            success=False,
            error="No valid languages provided"
        )]
    
    print(f"🌍 Batch translating to {len(valid_languages)} languages: {valid_languages}")
    
    # Create tasks for parallel execution
    tasks = [
        translate_script(json_script, lang, translate_visual_cues)
        for lang in valid_languages
    ]
    
    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions that were returned
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            lang = valid_languages[i]
            lang_info = SUPPORTED_LANGUAGES.get(lang, {})
            processed_results.append(TranslationResult(
                language=lang_info.get("name", "Unknown"),
                language_code=lang,
                language_native=lang_info.get("native", ""),
                translated_script={},
                success=False,
                error=str(result)
            ))
        else:
            processed_results.append(result)
    
    success_count = sum(1 for r in processed_results if r.success)
    print(f"   ✓ Completed: {success_count}/{len(valid_languages)} translations successful")
    
    return processed_results


def get_supported_languages() -> Dict[str, dict]:
    """Return the dictionary of supported languages."""
    return SUPPORTED_LANGUAGES
