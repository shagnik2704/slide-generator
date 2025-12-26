"""
Quality checking service for Spoken Tutorial scripts.
Translates scripts to Hindi and evaluates translation quality.
"""
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI


class QualityCheckResult(BaseModel):
    """Result for a single quality check."""
    passed: bool = Field(description="Whether the check passed (true) or failed (false)")
    notes: str = Field(description="Brief explanation of the result")


class TranslatedSlide(BaseModel):
    """A single translated slide."""
    slide_number: int = Field(description="Slide number")
    original_narration: str = Field(description="Original English narration")
    hindi_narration: str = Field(description="Translated Hindi narration")
    quality_score: int = Field(description="Quality score 1-5 (5=excellent, 1=poor)")
    timing_ok: bool = Field(description="Whether sentence fits time frame")
    issues: List[str] = Field(description="List of specific issues found", default_factory=list)


class QualityResults(BaseModel):
    """Complete quality check results with translation."""
    # Quality checks
    translation_quality: QualityCheckResult = Field(
        description="Does the Hindi translation preserve the original meaning?"
    )
    sentence_timing: QualityCheckResult = Field(
        description="Do all sentences fit within their time frames for speaking?"
    )
    transliteration: QualityCheckResult = Field(
        description="Are technical terms (in **bold**) preserved for transliteration?"
    )
    
    # Translated slides
    translated_slides: List[TranslatedSlide] = Field(
        description="All slides with Hindi translation and individual assessments"
    )


def check_quality(json_script: dict) -> dict:
    """
    Run quality checks and translate script to Hindi.
    
    Args:
        json_script: The parsed script JSON with slides
    
    Returns:
        Dictionary with quality checks and translated script
    """
    # Initialize LLM with structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
    )
    structured_llm = llm.with_structured_output(QualityResults)
    
    # Build the prompt
    prompt = f"""You are a bilingual (English-Hindi) expert translator and quality assessor for Spoken Tutorial scripts.

Use British English spelling and conventions in all English text.

Your task is to:
1. Translate the English narration to natural, spoken Hindi
2. Assess the translation quality
3. Check if technical terms are properly marked for transliteration

=== SCRIPT TO TRANSLATE AND ASSESS ===
{json.dumps(json_script, indent=2)}

=== TRANSLATION GUIDELINES ===

**Language Style:**
- Use simple, conversational Hindi suitable for spoken tutorials
- The Hindi should sound natural when read aloud
- Avoid overly formal or literary Hindi
- Use Devanagari script

**Technical Terms (Transliteration):**
- Words marked in **bold** in English should be kept as-is (transliterated, not translated)
- Examples: **Python**, **Linux**, **File menu**, **click** → keep in English/transliterated form
- If a bold term is missing in the original but should be there, note it as an issue

**Sentence Timing:**
- Hindi translations are typically 10-20% longer than English
- If a sentence seems too long to speak in ~5-6 seconds, flag it
- Each narration line should be speakable in one breath

=== QUALITY CHECKS ===

1. **Translation Quality**: 
   - Does the Hindi preserve the EXACT meaning of the English?
   - Is it natural spoken Hindi (not machine-translated sounding)?
   - Score each slide 1-5 (5=excellent)
   - Overall PASSED if average score >= 4

2. **Sentence Timing**:
   - Are sentences short enough to speak comfortably?
   - PASSED if all sentences are reasonable length
   - FAILED if any sentence is too long (>100 Hindi characters per line)

3. **Transliteration**:
   - Are all **bold** technical terms preserved in the translation?
   - PASSED if all bold terms kept as-is
   - FAILED if any bold term was incorrectly translated

For each slide, provide:
- slide_number: the slide number
- original_narration: the original English text
- hindi_narration: your Hindi translation
- quality_score: 1-5 rating
- timing_ok: true/false
- issues: list any specific problems (empty if none)
"""

    try:
        result = structured_llm.invoke(prompt)
        
        if result is None:
            return _get_error_response("AI returned no result")
        
        # Format checks for display (same structure as compliance)
        checks = [
            _format_check(
                "translation_quality",
                "Does Hindi translation preserve original meaning?",
                result.translation_quality
            ),
            _format_check(
                "sentence_timing",
                "Are all sentences within speakable time frames?",
                result.sentence_timing
            ),
            _format_check(
                "transliteration",
                "Are technical terms (**bold**) preserved for transliteration?",
                result.transliteration
            ),
        ]
        
        # Build translated script
        translated_script = {
            "title": json_script.get("title", "Untitled"),
            "title_hindi": _translate_title(json_script.get("title", ""), llm),
            "slides": []
        }
        
        for ts in result.translated_slides:
            # Find original slide to get visual cue
            original_slide = next(
                (s for s in json_script.get("slides", []) 
                 if s.get("slide_number") == ts.slide_number),
                {}
            )
            
            translated_script["slides"].append({
                "slide_number": ts.slide_number,
                "narration": ts.hindi_narration,
                "narration_original": ts.original_narration,
                "image_prompt": original_slide.get("image_prompt", ""),
                "quality_score": ts.quality_score,
                "timing_ok": ts.timing_ok,
                "issues": ts.issues
            })
        
        # Calculate summary
        ai_passed = sum(1 for c in checks if c["ai_review"] is True)
        ai_failed = sum(1 for c in checks if c["ai_review"] is False)
        
        # Calculate average quality score
        scores = [ts.quality_score for ts in result.translated_slides]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "checks": checks,
            "summary": {
                "ai_passed": ai_passed,
                "ai_failed": ai_failed,
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


def _translate_title(title: str, llm) -> str:
    """Translate just the title to Hindi."""
    if not title:
        return ""
    try:
        response = llm.invoke(f"Translate this tutorial title to Hindi (Devanagari script). Only output the Hindi translation, nothing else: {title}")
        return response.content.strip()
    except:
        return title


def _format_check(check_id: str, criteria: str, result: QualityCheckResult) -> dict:
    """Format a single check result."""
    return {
        "id": check_id,
        "criteria": criteria,
        "ai_review": result.passed,
        "ai_notes": result.notes,
        "human_review": None
    }


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
