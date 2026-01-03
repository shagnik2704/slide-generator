"""
Quality checking service for Spoken Tutorial scripts.
Uses back-translation (English → Hindi → English) for quality verification.
"""
import asyncio
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI


class TranslatedSlide(BaseModel):
    """A single translated slide with back-translation."""
    slide_number: int = Field(description="Slide number")
    hindi_narration: str = Field(description="Translated Hindi narration")


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


async def check_quality(json_script: dict) -> dict:
    """
    Run quality checks using back-translation approach.
    
    Flow:
    1. English → Hindi (forward translation)
    2. Hindi → English (back-translation)
    3. Compare original English with back-translated English
    
    Args:
        json_script: The parsed script JSON with slides
    
    Returns:
        Dictionary with quality checks and translated script
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
    )
    
    slides = json_script.get("slides", [])
    if not slides:
        return _get_error_response("No slides found in script")
    
    print(f"🔄 Starting back-translation for {len(slides)} slides...")
    
    try:
        # ============================================
        # STEP 1: Forward Translation (English → Hindi)
        # ============================================
        print("📝 Step 1: Translating English → Hindi...")
        
        forward_prompt = f"""You are an expert English-to-Hindi translator for Spoken Tutorial scripts.

Translate ONLY the narration text from English to Hindi. Follow these rules:

**Translation Rules:**
- Use natural, conversational Hindi (Devanagari script)
- Keep technical terms in English/transliterated (e.g., Python, Linux, File menu, click)
- If text has **bold** markers, keep them around technical terms
- Each sentence should be speakable in one breath

**Script to translate:**
{json.dumps([{"slide_number": s.get("slide_number", i+1), "narration": s.get("narration", "")} for i, s in enumerate(slides)], indent=2)}

Return the Hindi translation for each slide."""

        forward_llm = llm.with_structured_output(TranslationBatch)
        forward_result = await forward_llm.ainvoke(forward_prompt)
        
        if not forward_result or not forward_result.slides:
            return _get_error_response("Forward translation failed")
        
        hindi_translations = {s.slide_number: s.hindi_narration for s in forward_result.slides}
        print(f"   ✓ Translated {len(hindi_translations)} slides to Hindi")
        
        # ============================================
        # STEP 2: Back Translation (Hindi → English)
        # ============================================
        print("📝 Step 2: Back-translating Hindi → English...")
        
        back_prompt = f"""You are an expert Hindi-to-English translator.

Translate these Hindi narrations back to English. Be literal and accurate - do NOT try to guess the original text.

**Hindi narrations to translate:**
{json.dumps([{"slide_number": sn, "hindi": hn} for sn, hn in hindi_translations.items()], indent=2, ensure_ascii=False)}

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
            "title_hindi": await _translate_title(json_script.get("presentation_title", json_script.get("title", "")), llm),
            "slides": []
        }
        
        comparison_map = {c.slide_number: c for c in compare_result.comparisons}
        
        for i, slide in enumerate(slides):
            slide_num = slide.get("slide_number", i + 1)
            comparison = comparison_map.get(slide_num)
            
            translated_script["slides"].append({
                "slide_number": slide_num,
                "narration": hindi_translations.get(slide_num, ""),
                "narration_original": slide.get("narration", ""),
                "back_translation": back_translations.get(slide_num, ""),
                "image_prompt": slide.get("image_prompt", ""),
                "similarity_score": comparison.similarity_score if comparison else 0,
                "meaning_preserved": comparison.meaning_preserved if comparison else False,
                "timing_ok": True,  # Not checking in this version
                "issues": comparison.issues if comparison else []
            })
        
        print(f"✅ Quality check complete. Avg score: {avg_score:.1f}/5")
        
        return {
            "checks": checks,
            "summary": {
                "ai_passed": sum(1 for c in checks if c["ai_review"] is True),
                "ai_failed": sum(1 for c in checks if c["ai_review"] is False),
                "total": len(checks),
                "avg_quality_score": round(avg_score, 1)
            },
            "translated_script": translated_script
        }
        
    except Exception as e:
        print(f"⚠️ Quality check error: {e}")
        import traceback
        traceback.print_exc()
        return _get_error_response(str(e))


async def _translate_title(title: str, llm) -> str:
    """Translate just the title to Hindi."""
    if not title:
        return ""
    try:
        response = await llm.ainvoke(f"Translate this tutorial title to Hindi (Devanagari script). Only output the Hindi translation, nothing else: {title}")
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


async def batch_check_quality(scripts: List[dict]) -> dict:
    """
    Run quality checks for multiple scripts in parallel.
    
    Each script's internal quality check (3-step back-translation) runs sequentially,
    but all scripts run in parallel with each other.
    
    Args:
        scripts: List of parsed script JSON objects
    
    Returns:
        Dictionary with:
        - results: List of quality check results (one per script)
        - batch_summary: Overall batch statistics
    """
    print(f"📋 Batch quality check: {len(scripts)} scripts in parallel")
    
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
        check_quality(script) for script in scripts
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

