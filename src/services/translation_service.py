"""
Multi-language translation service for Spoken Tutorial scripts.
Supports batch translation to multiple Indian languages using Sarvam AI (sarvam-translate:v1)
with fallback to Google Gemini.
"""
import asyncio
import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple
import httpx
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.metrics import (
    TRANSLATION_REQUESTS_TOTAL,
    TRANSLATION_DURATION_SECONDS,
)

logger = logging.getLogger(__name__)


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
# SUPPORTED LANGUAGES & SARVAM MAPPING
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

# Sarvam translation BCP-47 language codes
# Note: Sarvam uses 'od-IN' for Odia, and 'sarvam-translate:v1' supports all 11 languages including 'as-IN' (Assamese).
SARVAM_TRANSLATE_LANG_MAP = {
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "kn": "kn-IN",
    "gu": "gu-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "or": "od-IN",
    "as": "as-IN",
}

SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
DEFAULT_SARVAM_TRANSLATE_MODEL = "sarvam-translate:v1"
SARVAM_MAX_CHARS = 1800  # Max chars per request (safely under Sarvam's 2000 character limit)
SARVAM_MAX_RETRIES = 2
SARVAM_MAX_CONCURRENCY = 10

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?।])\s+')


def resolve_language_info(target_language: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Resolve target language string to:
    (normalized_code, name, native, sarvam_bcp47)
    
    Accepts 2-letter ISO codes ('hi', 'or') or BCP-47 codes ('hi-IN', 'od-IN').
    """
    if not target_language:
        return None

    code = target_language.strip().lower()

    # Exact match in 2-letter supported languages
    if code in SUPPORTED_LANGUAGES:
        info = SUPPORTED_LANGUAGES[code]
        bcp47 = SARVAM_TRANSLATE_LANG_MAP.get(code, f"{code}-IN")
        return code, info["name"], info["native"], bcp47

    # Check prefix or special cases
    prefix = code.split("-")[0]
    if prefix in SUPPORTED_LANGUAGES:
        info = SUPPORTED_LANGUAGES[prefix]
        bcp47 = SARVAM_TRANSLATE_LANG_MAP.get(prefix, f"{prefix}-IN")
        return prefix, info["name"], info["native"], bcp47

    if prefix == "od" or code == "od-in":
        info = SUPPORTED_LANGUAGES["or"]
        return "or", info["name"], info["native"], "od-IN"

    return None


def _split_text_into_chunks(text: str, max_len: int = SARVAM_MAX_CHARS) -> List[str]:
    """Split long text into chunks at sentence or word boundaries that fit max_len."""
    text = text.strip()
    if not text or len(text) <= max_len:
        return [text] if text else []

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if not sentences:
        sentences = text.split()

    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if sentence_len > max_len:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_len = 0
            for i in range(0, sentence_len, max_len):
                chunks.append(sentence[i:i + max_len])
            continue

        separator_len = 1 if current_chunk else 0
        if current_len + separator_len + sentence_len <= max_len:
            current_chunk.append(sentence)
            current_len += separator_len + sentence_len
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_len = sentence_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


async def _translate_chunk_sarvam(
    client: httpx.AsyncClient,
    text: str,
    target_code: str,
    api_key: str,
    model: str = DEFAULT_SARVAM_TRANSLATE_MODEL,
    source_code: str = "en-IN",
) -> str:
    """Send a single chunk to Sarvam translation API with retry handling."""
    payload = {
        "input": text,
        "source_language_code": source_code,
        "target_language_code": target_code,
        "model": model,
    }
    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": api_key,
    }

    last_error = None
    for attempt in range(SARVAM_MAX_RETRIES + 1):
        try:
            response = await client.post(
                SARVAM_TRANSLATE_URL,
                json=payload,
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("translated_text", "")

            status = response.status_code
            if status != 429 and status < 500:
                err_msg = ""
                try:
                    err_data = response.json()
                    err_msg = err_data.get("message") or err_data.get("detail") or str(err_data)
                except Exception:
                    err_msg = response.text
                raise RuntimeError(f"Sarvam translation error ({status}): {err_msg}")

            if attempt < SARVAM_MAX_RETRIES:
                backoff = (attempt + 1) * 1.0
                logger.warning(
                    "Sarvam translation temporary error (HTTP %s), retrying in %.1fs (attempt %d/%d)...",
                    status, backoff, attempt + 1, SARVAM_MAX_RETRIES
                )
                await asyncio.sleep(backoff)
                continue

            response.raise_for_status()

        except (httpx.RequestError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < SARVAM_MAX_RETRIES:
                backoff = (attempt + 1) * 1.0
                logger.warning(
                    "Sarvam translation network error (%s), retrying in %.1fs (attempt %d/%d)...",
                    str(e), backoff, attempt + 1, SARVAM_MAX_RETRIES
                )
                await asyncio.sleep(backoff)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Sarvam translation failed after retries")


async def _translate_text_sarvam(
    client: httpx.AsyncClient,
    text: str,
    target_code: str,
    api_key: str,
    model: str = DEFAULT_SARVAM_TRANSLATE_MODEL,
    source_code: str = "en-IN",
) -> str:
    """Translate text using Sarvam API, chunking if text exceeds limit."""
    if not text or not text.strip():
        return text

    if len(text) > SARVAM_MAX_CHARS:
        chunks = _split_text_into_chunks(text, max_len=SARVAM_MAX_CHARS)
        translated_chunks = []
        for chunk in chunks:
            trans = await _translate_chunk_sarvam(
                client, chunk, target_code, api_key, model=model, source_code=source_code
            )
            translated_chunks.append(trans)
        return " ".join(translated_chunks)

    return await _translate_chunk_sarvam(
        client, text, target_code, api_key, model=model, source_code=source_code
    )


async def _translate_script_sarvam(
    json_script: dict,
    target_code: str,
    target_bcp47: str,
    lang_name: str,
    lang_native: str,
    api_key: str,
    translate_visual_cues: bool = True,
    model: str = DEFAULT_SARVAM_TRANSLATE_MODEL,
) -> dict:
    """Translate script slides concurrently using Sarvam API."""
    slides = json_script.get("slides", [])
    semaphore = asyncio.Semaphore(SARVAM_MAX_CONCURRENCY)

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        async def translate_single_slide(i: int, slide: dict):
            slide_num = slide.get("slide_number", i + 1)
            narration = slide.get("narration", "")
            cue = slide.get("visual_cue", "") if (translate_visual_cues and slide.get("visual_cue")) else None

            async with semaphore:
                trans_narration = await _translate_text_sarvam(
                    client, narration, target_bcp47, api_key, model=model
                )

            trans_cue = None
            if cue is not None:
                async with semaphore:
                    trans_cue = await _translate_text_sarvam(
                        client, cue, target_bcp47, api_key, model=model
                    )

            return slide_num, trans_narration, trans_cue

        slide_tasks = [translate_single_slide(i, slide) for i, slide in enumerate(slides)]
        slide_results = await asyncio.gather(*slide_tasks)

    lookup = {sn: (nar, cue) for sn, nar, cue in slide_results}
    translated_slides = []
    for i, slide in enumerate(slides):
        slide_num = slide.get("slide_number", i + 1)
        translated_slide = slide.copy()
        if slide_num in lookup:
            nar, cue = lookup[slide_num]
            translated_slide[f"narration_{target_code}"] = nar
            if cue is not None:
                translated_slide[f"visual_cue_{target_code}"] = cue
        translated_slides.append(translated_slide)

    translated_script = json_script.copy()
    translated_script["slides"] = translated_slides
    translated_script["target_language"] = target_code
    translated_script["target_language_name"] = lang_name
    translated_script["target_language_native"] = lang_native
    return translated_script


async def _translate_script_gemini(
    json_script: dict,
    target_code: str,
    lang_name: str,
    lang_native: str,
    translate_visual_cues: bool = True,
) -> dict:
    """Fallback translation using Google Gemini (gemini-2.5-flash)."""
    slides = json_script.get("slides", [])
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
    )

    content_to_translate = []
    for i, slide in enumerate(slides):
        item = {
            "slide_number": slide.get("slide_number", i + 1),
            "narration": slide.get("narration", "")
        }
        if translate_visual_cues and slide.get("visual_cue"):
            item["visual_cue"] = slide.get("visual_cue", "")
        content_to_translate.append(item)

    visual_cue_instruction = ""
    if translate_visual_cues:
        visual_cue_instruction = "- Also translate the visual_cue field if present"

    prompt = f"""You are an expert English-to-{lang_name} translator specializing in educational Spoken Tutorial scripts.

**Translation Guidelines:**
1. Use simple, everyday {lang_name} that a student can easily understand
2. Keep sentences short and natural for speaking aloud (this will be converted to audio)
3. Avoid complex vocabulary - prefer common words over formal/literary ones
4. Preserve **bold** markers exactly - transliterate content inside **markers** to {lang_native} script
   (e.g., Python → पायथन, Terminal → టెర్మినల్, Click → क्लिक)
5. Maintain the original meaning and tone
{visual_cue_instruction}

**Content to translate:**
{json.dumps(content_to_translate, indent=2, ensure_ascii=False)}

Return the {lang_name} translation for each slide. Include both narration and visual_cue if present."""

    translation_llm = llm.with_structured_output(TranslationBatch)
    result = await translation_llm.ainvoke(prompt)

    if not result or not result.slides:
        raise RuntimeError("Gemini translation returned empty result")

    translated_script = json_script.copy()
    translated_slides = []
    translation_lookup = {s.slide_number: s for s in result.slides}

    for i, slide in enumerate(slides):
        slide_num = slide.get("slide_number", i + 1)
        translated_slide = slide.copy()
        if slide_num in translation_lookup:
            trans = translation_lookup[slide_num]
            translated_slide[f"narration_{target_code}"] = trans.narration
            if trans.visual_cue:
                translated_slide[f"visual_cue_{target_code}"] = trans.visual_cue
        translated_slides.append(translated_slide)

    translated_script["slides"] = translated_slides
    translated_script["target_language"] = target_code
    translated_script["target_language_name"] = lang_name
    translated_script["target_language_native"] = lang_native
    return translated_script


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
    Primary engine is Sarvam AI (sarvam-translate:v1), with fallback to Gemini.
    
    Args:
        json_script: The parsed script JSON with slides
        target_language: Language code (e.g., 'hi', 'ta', 'te', 'hi-IN', 'od-IN')
        translate_visual_cues: Whether to also translate visual cues
    
    Returns:
        TranslationResult with translated script or error
    """
    resolved = resolve_language_info(target_language)
    if not resolved:
        return TranslationResult(
            language=target_language,
            language_code=target_language,
            language_native="Unknown",
            translated_script={},
            success=False,
            error=f"Unsupported language: {target_language}"
        )

    lang_code, lang_name, lang_native, target_bcp47 = resolved

    slides = json_script.get("slides", [])
    if not slides:
        return TranslationResult(
            language=lang_name,
            language_code=lang_code,
            language_native=lang_native,
            translated_script={},
            success=False,
            error="No slides found in script"
        )

    print(f"🌐 Translating to {lang_name} ({lang_native})...")
    t0 = time.perf_counter()

    provider = os.getenv("TRANSLATION_PROVIDER", "sarvam").lower().strip()
    sarvam_key = (os.getenv("SARVAM_API_KEY") or "").strip()
    sarvam_model = os.getenv("SARVAM_TRANSLATE_MODEL", DEFAULT_SARVAM_TRANSLATE_MODEL).strip()

    try:
        translated_script = None

        if provider == "sarvam" and sarvam_key:
            try:
                translated_script = await _translate_script_sarvam(
                    json_script=json_script,
                    target_code=lang_code,
                    target_bcp47=target_bcp47,
                    lang_name=lang_name,
                    lang_native=lang_native,
                    api_key=sarvam_key,
                    translate_visual_cues=translate_visual_cues,
                    model=sarvam_model,
                )
            except Exception as sarvam_err:
                logger.warning(
                    "Sarvam translation failed: %s. Attempting Gemini fallback...",
                    sarvam_err,
                )
                if os.getenv("GEMINI_API_KEY"):
                    translated_script = await _translate_script_gemini(
                        json_script=json_script,
                        target_code=lang_code,
                        lang_name=lang_name,
                        lang_native=lang_native,
                        translate_visual_cues=translate_visual_cues,
                    )
                else:
                    raise sarvam_err
        else:
            if not sarvam_key:
                logger.info("SARVAM_API_KEY not configured; using Gemini translation.")
            translated_script = await _translate_script_gemini(
                json_script=json_script,
                target_code=lang_code,
                lang_name=lang_name,
                lang_native=lang_native,
                translate_visual_cues=translate_visual_cues,
            )

        elapsed = time.perf_counter() - t0
        TRANSLATION_DURATION_SECONDS.labels(target_language=lang_code).observe(elapsed)
        TRANSLATION_REQUESTS_TOTAL.labels(target_language=lang_code, status="success").inc()
        print(f"   ✓ Translated {len(slides)} slides to {lang_name}")

        return TranslationResult(
            language=lang_name,
            language_code=lang_code,
            language_native=lang_native,
            translated_script=translated_script,
            success=True,
        )

    except Exception as e:
        TRANSLATION_REQUESTS_TOTAL.labels(target_language=lang_code, status="error").inc()
        print(f"   ❌ Translation failed: {e}")
        return TranslationResult(
            language=lang_name,
            language_code=lang_code,
            language_native=lang_native,
            translated_script={},
            success=False,
            error=str(e),
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
    valid_languages = [lang for lang in languages if resolve_language_info(lang) is not None]

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

    tasks = [
        translate_script(json_script, lang, translate_visual_cues)
        for lang in valid_languages
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            lang = valid_languages[i]
            info = resolve_language_info(lang)
            name = info[1] if info else "Unknown"
            native = info[2] if info else ""
            processed_results.append(TranslationResult(
                language=name,
                language_code=lang,
                language_native=native,
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

