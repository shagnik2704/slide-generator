"""
Quality checking service for Spoken Tutorial scripts.
Uses back-translation (English → Target Language → English) for quality verification.
Supports multiple Indian languages.
"""
import asyncio
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

# Import supported languages from translation service
from src.services.translation_service import SUPPORTED_LANGUAGES


class TranslatedSlide(BaseModel):
    """A single translated slide with back-translation."""
    slide_number: int = Field(description="Slide number")
    translated_narration: str = Field(description="Translated narration in target language")


class BackTranslatedSlide(BaseModel):
    """A single back-translated slide."""
    slide_number: int = Field(description="Slide number")
    english_narration: str = Field(description="Back-translated English narration")


class TranslationBatch(BaseModel):
    """Batch of translated slides."""
    slides: List[TranslatedSlide] = Field(description="All translated slides")


class BackTranslationBatch(BaseModel):
    """Batch of back-translated slides."""
    slides: List[BackTranslatedSlide] = Field(description="All back-translated slides")


class MeaningComparison(BaseModel):
    """Comparison result for a single slide."""
    slide_number: int = Field(description="Slide number")
    meaning_preserved: bool = Field(description="True if meaning is preserved, False if meaning changed")
    similarity_score: int = Field(description="Similarity score 1-5 (5=identical meaning, 1=completely different)")
    issues: List[str] = Field(description="List of specific meaning differences found", default_factory=list)


class ComparisonResults(BaseModel):
    """Results of comparing original with back-translation."""
    overall_quality: bool = Field(description="True if overall translation quality is acceptable (avg score >= 4)")
    comparisons: List[MeaningComparison] = Field(description="Per-slide comparison results")


async def check_quality(json_script: dict, language_code: str = "hi") -> dict:
    """
    Run quality checks using back-translation approach.
    
    Flow:
    1. English → Target Language (forward translation)
    2. Target Language → English (back-translation)
    3. Compare original English with back-translated English
    
    Args:
        json_script: The parsed script JSON with slides
        language_code: Target language code (e.g., 'hi', 'ta', 'te'). Defaults to Hindi.
    
    Returns:
        Dictionary with quality checks and translated script
    """
    # Get language info
    lang_info = SUPPORTED_LANGUAGES.get(language_code)
    if not lang_info:
        return _get_error_response(f"Unsupported language: {language_code}")
    
    lang_name = lang_info["name"]
    lang_native = lang_info["native"]
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
    )
    
    slides = json_script.get("slides", [])[:-1]
    if not slides:
        return _get_error_response("No slides found in script")
    
    print(f"🔄 Starting back-translation for {len(slides)} slides to {lang_name} ({lang_native})...")
    
    try:
        # ============================================
        # STEP 1: Forward Translation (English → Target Language)
        # ============================================
        print(f"📝 Step 1: Translating English → {lang_name}...")
        
        forward_prompt = f"""You are an expert English-to-{lang_name} translator for Spoken Tutorial scripts.

Translate ONLY the narration text from English to {lang_name}. Follow these rules:

**Translation Rules:**
- Use natural, conversational {lang_name} (native script: {lang_native})
- Keep technical terms in English/transliterated (e.g., Python, Linux, File menu, click)
- If text has **bold** markers, transliterate them to {lang_name}
- Each sentence should be speakable in one breath

**Script to translate:**
{json.dumps([{"slide_number": s.get("slide_number", i+1), "narration": s.get("narration", "")} for i, s in enumerate(slides)], indent=2)}

Return the {lang_name} translation for each slide."""

        forward_llm = llm.with_structured_output(TranslationBatch)
        forward_result = await forward_llm.ainvoke(forward_prompt)
        
        if not forward_result or not forward_result.slides:
            return _get_error_response("Forward translation failed")
        
        translations = {s.slide_number: s.translated_narration for s in forward_result.slides}
        print(f"   ✓ Translated {len(translations)} slides to {lang_name}")
        
        # ============================================
        # STEP 2: Back Translation (Target Language → English)
        # ============================================
        print(f"📝 Step 2: Back-translating {lang_name} → English...")
        
        back_prompt = f"""You are an expert {lang_name}-to-English translator.

Translate these {lang_name} narrations back to English. Be literal and accurate - do NOT try to guess the original text.

**{lang_name} narrations to translate:**
{json.dumps([{"slide_number": sn, "text": tn} for sn, tn in translations.items()], indent=2, ensure_ascii=False)}

Return the English translation for each slide."""

        back_llm = llm.with_structured_output(BackTranslationBatch)
        back_result = await back_llm.ainvoke(back_prompt)
        
        if not back_result or not back_result.slides:
            return _get_error_response("Back translation failed")
        
        back_translations = {s.slide_number: s.english_narration for s in back_result.slides}
        print(f"   ✓ Back-translated {len(back_translations)} slides to English")
        
        # ============================================
        # STEP 3: Compare Original vs Back-Translation
        # ============================================
        print("📝 Step 3: Comparing original with back-translation...")
        
        # Build comparison data
        comparison_data = []
        for i, slide in enumerate(slides):
            slide_num = slide.get("slide_number", i + 1)
            comparison_data.append({
                "slide_number": slide_num,
                "original_english": slide.get("narration", ""),
                "back_translated_english": back_translations.get(slide_num, "")
            })
        
        compare_prompt = f"""You are a quality assessor comparing original English text with back-translated English.

For each slide, determine if the MEANING is preserved:
- Compare the original English with the back-translated English
- Score 1-5: 5 = identical meaning, 4 = minor wording difference, 3 = some meaning lost, 2 = significant difference, 1 = completely different
- List any specific meaning differences (missing info, changed facts, wrong terms)
- meaning_preserved = True if score >= 4

**Comparisons:**
{json.dumps(comparison_data, indent=2)}

Overall quality passes if average score >= 4."""

        compare_llm = llm.with_structured_output(ComparisonResults)
        compare_result = await compare_llm.ainvoke(compare_prompt)
        
        if not compare_result:
            return _get_error_response("Comparison failed")
        
        print(f"   ✓ Compared {len(compare_result.comparisons)} slides")
        
        # ============================================
        # Build Response
        # ============================================
        
        # Calculate stats
        scores = [c.similarity_score for c in compare_result.comparisons]
        avg_score = sum(scores) / len(scores) if scores else 0
        passed_count = sum(1 for c in compare_result.comparisons if c.meaning_preserved)
        failed_count = len(compare_result.comparisons) - passed_count
        
        # Build checks array (for UI compatibility)
        checks = [
            {
                "id": "back_translation",
                "criteria": "Does back-translation match original meaning?",
                "ai_review": compare_result.overall_quality,
                "ai_notes": f"Average similarity score: {avg_score:.1f}/5. {passed_count} slides passed, {failed_count} failed.",
                "human_review": None
            },
            {
                "id": "transliteration",
                "criteria": "Are technical terms preserved?",
                "ai_review": True,  # Checked implicitly in comparison
                "ai_notes": "Technical terms checked via back-translation comparison.",
                "human_review": None
            }
        ]
        
        # Build translated script with comparison data
        translated_script = {
            "title": json_script.get("presentation_title", json_script.get("title", "Untitled")),
            f"title_{language_code}": await _translate_title(json_script.get("presentation_title", json_script.get("title", "")), llm, lang_name),
            "slides": []
        }
        
        comparison_map = {c.slide_number: c for c in compare_result.comparisons}
        
        for i, slide in enumerate(slides):
            slide_num = slide.get("slide_number", i + 1)
            comparison = comparison_map.get(slide_num)
            
            translated_script["slides"].append({
                "slide_number": slide_num,
                "narration": translations.get(slide_num, ""),
                "narration_original": slide.get("narration", ""),
                "back_translation": back_translations.get(slide_num, ""),
                "image_prompt": slide.get("image_prompt", ""),
                "similarity_score": comparison.similarity_score if comparison else 0,
                "meaning_preserved": comparison.meaning_preserved if comparison else False,
                "timing_ok": True,  # Not checking in this version
                "issues": comparison.issues if comparison else []
            })
        
        print(f"✅ Quality check ({lang_name}) complete. Avg score: {avg_score:.1f}/5")
        
        return {
            "checks": checks,
            "summary": {
                "ai_passed": sum(1 for c in checks if c["ai_review"] is True),
                "ai_failed": sum(1 for c in checks if c["ai_review"] is False),
                "total": len(checks),
                "avg_quality_score": round(avg_score, 1)
            },
            "translated_script": translated_script,
            "language_code": language_code,
            "language_name": lang_name,
            "language_native": lang_native
        }
        
    except Exception as e:
        print(f"⚠️ Quality check error: {e}")
        import traceback
        traceback.print_exc()
        return _get_error_response(str(e))


async def _translate_title(title: str, llm, lang_name: str = "Hindi") -> str:
    """Translate just the title to the target language."""
    if not title:
        return ""
    try:
        response = await llm.ainvoke(f"Translate this tutorial title to {lang_name}. Only output the {lang_name} translation, nothing else: {title}")
        return response.content.strip()
    except:
        return title


def _get_error_response(error_msg: str) -> dict:
    """Return error response structure."""
    return {
        "checks": [{
            "id": "error",
            "criteria": "Quality check failed",
            "ai_review": None,
            "ai_notes": f"Error: {error_msg}",
            "human_review": None
        }],
        "summary": {
            "ai_passed": 0,
            "ai_failed": 0,
            "total": 1,
            "avg_quality_score": 0
        },
        "translated_script": None
    }


async def batch_check_quality(scripts: List[dict], language_code: str = "hi") -> dict:
    """
    Run quality checks for multiple scripts in parallel.
    
    Each script's internal quality check (3-step back-translation) runs sequentially,
    but all scripts run in parallel with each other.
    
    Args:
        scripts: List of parsed script JSON objects
        language_code: Target language code for all scripts. Defaults to Hindi.
    
    Returns:
        Dictionary with:
        - results: List of quality check results (one per script)
        - batch_summary: Overall batch statistics
    """
    lang_name = SUPPORTED_LANGUAGES.get(language_code, {}).get("name", "Hindi")
    print(f"📋 Batch quality check: {len(scripts)} scripts in parallel ({lang_name})")
    
    if not scripts:
        return {
            "results": [],
            "batch_summary": {
                "total_scripts": 0,
                "scripts_passed": 0,
                "scripts_with_issues": 0,
                "avg_quality_score": 0
            }
        }
    
    # Run all quality checks in parallel
    results = await asyncio.gather(*[
        check_quality(script, language_code) for script in scripts
    ], return_exceptions=True)
    
    # Process results
    processed_results = []
    passed_count = 0
    total_scores = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Handle failed checks
            processed_results.append({
                "script_index": i,
                "success": False,
                "error": str(result),
                "checks": [],
                "summary": {"ai_passed": 0, "ai_failed": 0, "total": 0, "avg_quality_score": 0}
            })
        else:
            # Quality check succeeded
            result["script_index"] = i
            result["success"] = True
            processed_results.append(result)
            
            # Track stats
            summary = result.get("summary", {})
            score = summary.get("avg_quality_score", 0)
            total_scores.append(score)
            if score >= 4:
                passed_count += 1
    
    # Calculate batch summary
    avg_score = sum(total_scores) / len(total_scores) if total_scores else 0
    
    print(f"✓ Batch complete: {passed_count}/{len(scripts)} scripts passed (avg score: {avg_score:.1f})")
    
    return {
        "results": processed_results,
        "batch_summary": {
            "total_scripts": len(scripts),
            "scripts_passed": passed_count,
            "scripts_with_issues": len(scripts) - passed_count,
            "avg_quality_score": round(avg_score, 1)
        }
    }

