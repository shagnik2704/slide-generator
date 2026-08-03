"""
Voice generation service for Spoken Tutorial scripts.
Uses Sarvam AI TTS (Bulbul v3) for audio narration.
"""
import os
import re
import asyncio
import zipfile
import httpx
import base64
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

from src.utils.audio_utils import concat_wav_bytes, get_wav_duration, silence_wav_like

load_dotenv()

# Map internal 2-letter language codes to Sarvam BCP-47 codes.
# Bulbul v3 has voices for these 11 languages only. Languages the translation
# service offers but Bulbul cannot speak (Assamese) are deliberately absent —
# see resolve_language_code.
SARVAM_LANG_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "kn": "kn-IN",
    "gu": "gu-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "or": "od-IN",  # Odia in Sarvam is od-IN
}

SUPPORTED_SARVAM_CODES = set(SARVAM_LANG_MAP.values())

# Voice configuration constants for Sarvam TTS
# Female voice options: 'kavya' (default), 'shreya', 'neha', 'ritu', 'ishita'
# Male voice options: 'shubh', 'aditya', 'manan'
DEFAULT_SPEAKER = "kavya"
DEFAULT_PACE = 0.9         # Slower pace (1.0 is default)

# Bulbul v3 accepts at most 2500 characters per request. A 3-4 minute tutorial
# runs 2700-3300 characters, so long narration is split and stitched back
# together rather than truncated.
TTS_CHAR_LIMIT = 2500

# Sentence terminators: Latin, plus the Devanagari danda and double danda used
# by Hindi, Marathi, Bengali, Punjabi and Odia.
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?।॥])\s+')
_CLAUSE_SPLIT_RE = re.compile(r'(?<=[,;:])\s+')
_WORD_SPLIT_RE = re.compile(r'\s+')

# Known HTML tags, so markup is stripped from narration while C/C++ includes
# and template parameters (<stdio.h>, <iostream>, <vector>) survive.
_HTML_TAG_RE = re.compile(
    r'</?(?:p|br|hr|div|span|b|i|u|s|em|strong|small|sub|sup|ul|ol|li|dl|dt|dd'
    r'|a|img|h[1-6]|code|pre|blockquote|table|thead|tbody|tr|td|th|figure'
    r'|figcaption|section|article|header|footer|nav|main|form|input|button'
    r'|label|select|option|textarea)\b[^>]*>',
    re.IGNORECASE,
)

_TTS_URL = "https://api.sarvam.ai/text-to-speech"
_TTS_MAX_ATTEMPTS = 3

# How a single combined narration is built. CONTINUOUS synthesizes the script
# as one stream and only breaks where the character limit forces it, so there
# are as few seams as possible. PER_SLIDE synthesizes each slide on its own and
# stitches them, which keeps a file per slide that can be reviewed and redone
# individually, at the cost of a seam at every slide boundary.
CONTINUOUS = "continuous"
PER_SLIDE = "per_slide"
COMBINE_SOURCES = (CONTINUOUS, PER_SLIDE)


class UnsupportedLanguageError(ValueError):
    """
    Raised when a script's language has no Sarvam TTS voice.

    Assamese is the live case: the translation service offers it, Bulbul cannot
    speak it. Falling back to an English voice would read the Bengali script as
    nonsense while still reporting success, so we refuse instead.
    """

    def __init__(self, language_code: str):
        self.language_code = language_code
        supported = ", ".join(sorted(SARVAM_LANG_MAP))
        super().__init__(
            f"No Sarvam TTS voice is available for language '{language_code}'. "
            f"Supported languages: {supported}."
        )


class UnsplittableTextError(ValueError):
    """
    Raised when narration cannot be broken into chunks the TTS API accepts.

    Only happens when a single run of characters longer than the limit has no
    sentence, clause or word boundary in it — a pasted base64 blob or a runaway
    URL, not prose. Cutting it blind would drop or mangle content, so the
    request is refused and the offending text reported instead.
    """

    def __init__(self, token: str, limit: int):
        self.token = token
        preview = token[:60] + "…" if len(token) > 60 else token
        super().__init__(
            f"Cannot split narration for TTS: a {len(token)}-character run has "
            f"no sentence, clause or word boundary to break on (limit is "
            f"{limit} characters). Text starts: {preview!r}"
        )


def resolve_language_code(raw_lang: Optional[str]) -> str:
    """
    Map an internal language code to Sarvam's BCP-47 code.

    Args:
        raw_lang: Two-letter code ('hi') or BCP-47 code ('hi-IN'). Empty or
            missing values mean an untranslated script, which is English.

    Returns:
        A BCP-47 code Bulbul has a voice for

    Raises:
        UnsupportedLanguageError: if no voice exists for this language
    """
    code = (raw_lang or "en").strip()

    if "-" in code:
        if code not in SUPPORTED_SARVAM_CODES:
            raise UnsupportedLanguageError(code)
        return code

    mapped = SARVAM_LANG_MAP.get(code.lower())
    if mapped is None:
        raise UnsupportedLanguageError(code)
    return mapped

def extract_narration(json_script: dict) -> List[Dict]:
    """
    Extract narration text from each slide.
    
    Returns:
        List of dicts with slide_number and narration text
    """
    slides = json_script.get('slides', [])
    narrations = []
    
    if not slides:
        print("⚠️ No slides found in script")
        return narrations
    
    for i, slide in enumerate(slides):
        narration = slide.get('narration', '')
        
        # Handle list or string
        if isinstance(narration, list):
            # Filter out empty strings and join
            narration = ' '.join(str(n) for n in narration if n and str(n).strip())
        
        # Ensure narration is a string
        if not isinstance(narration, str):
            narration = str(narration) if narration else ''
        
        # Fallback to title if no narration
        if not narration.strip():
            narration = slide.get('title', f'Slide {i+1}')
            if not narration or not narration.strip():
                narration = f'Slide {i+1}'  # Final fallback
        
        # Clean markdown formatting for TTS
        narration = clean_text_for_tts(narration)
        
        # Ensure we have valid narration after cleaning
        if not narration or not narration.strip():
            narration = f'Slide {i+1}'  # Final fallback
        
        slide_number = slide.get('slide_number', i + 1)
        # Ensure slide_number is an integer
        try:
            slide_number = int(slide_number)
        except (ValueError, TypeError):
            slide_number = i + 1
        
        narrations.append({
            'slide_number': slide_number,
            'narration': narration
        })
    
    print(f"📝 Extracted narrations for {len(narrations)} slides")
    return narrations


def clean_text_for_tts(text: str) -> str:
    """
    Remove markdown so narration reads cleanly, without damaging code.

    Narration on this platform routinely names identifiers and commands, so
    markers are stripped only where they are unambiguously markdown. Blanket
    deletion used to turn `my_variable` into "myvariable", `__init__` into
    "init", `*args` into "args" and `#include <stdio.h>` into "include".

    Left deliberately untouched:
      - `_` anywhere: snake_case and dunder names outweigh `_italic_`
      - a lone `*`: `*args` and multiplication outweigh `*italic*`
      - `#` and `-` mid-line: `#include`, `C#`, `apt-get`, `ls -l`
      - `<...>` that is not a known HTML tag: `<stdio.h>`, `<iostream>`
    TTS reads these symbols as silence, so leaving them costs nothing.
    """
    if not text:
        return ""

    # MediaWiki emphasis. This is the markup Spoken Tutorial scripts actually
    # carry ('''Cyberspace'''), and nothing used to strip it — the quotes were
    # being read aloud. Longest marker first.
    text = re.sub(r"'''''(.+?)'''''", r'\1', text)
    text = re.sub(r"'''(.+?)'''", r'\1', text)
    text = re.sub(r"''(.+?)''", r'\1', text)

    # MediaWiki links: [[Page|shown text]] and [[Page]].
    text = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', text)

    # Code fences: keep the code, drop the fence lines.
    text = re.sub(r'^[ \t]*```[^\n]*$', '', text, flags=re.MULTILINE)

    # Inline code: keep the contents, drop the backticks.
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Paired bold only. Requires a non-space, non-asterisk start so that
    # `*args, **kwargs` and `2 ** 3` are not treated as emphasis.
    text = re.sub(r'\*\*(?=\S)([^*]+?)\*\*', r'\1', text)

    # Headings and bullets, only where they lead a line.
    text = re.sub(r'^[ \t]{0,3}#{1,6}[ \t]+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*[-*+][ \t]+', '', text, flags=re.MULTILINE)

    # Bullet glyphs never carry code meaning, so they go anywhere they appear.
    text = text.replace('•', ' ')

    # Real HTML tags only — an angle-bracket expression that is not one of
    # these is far more likely to be a C/C++ header or a template parameter.
    text = _HTML_TAG_RE.sub('', text)

    # Normalize whitespace (remove \n, \t, multiple spaces)
    return ' '.join(text.split()).strip()


def _pack_units(units: List[str], limit: int) -> List[str]:
    """Greedily group units into chunks no longer than `limit` characters."""
    chunks = []
    current = ""

    for unit in units:
        if len(unit) > limit:
            # Too big to pack anywhere — break it down on its own.
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_oversized(unit, limit))
            continue

        candidate = f"{current} {unit}" if current else unit
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = unit

    if current:
        chunks.append(current)

    return chunks


def _split_oversized(unit: str, limit: int) -> List[str]:
    """
    Break a single over-limit unit on progressively weaker boundaries.

    Raises:
        UnsplittableTextError: if no boundary exists. Narration is never cut
            mid-token — a blind slice would split a word, an identifier or a
            command in half and read it as gibberish.
    """
    for pattern in (_CLAUSE_SPLIT_RE, _WORD_SPLIT_RE):
        parts = [p for p in pattern.split(unit) if p]
        if len(parts) > 1:
            return _pack_units(parts, limit)

    raise UnsplittableTextError(unit, limit)


def split_text_for_tts(text: str, limit: int = TTS_CHAR_LIMIT) -> List[str]:
    """
    Split narration into chunks that fit Bulbul's per-request character limit.

    Sentence boundaries are preferred so each seam lands on a natural pause;
    over-long sentences fall back to clause, then word, then hard boundaries.

    Args:
        text: Narration text of any length
        limit: Maximum characters per chunk

    Returns:
        Chunks in playback order (empty list for empty input)
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return _pack_units(sentences, limit)


async def _synthesize_chunk(
    client: httpx.AsyncClient,
    text: str,
    language_code: str,
    speaker: str,
    pace: float,
    api_key: str,
    dict_id: Optional[str] = None,
) -> bytes:
    """
    Send one under-limit chunk to Sarvam and return the raw WAV bytes.

    Retries transient failures (timeouts, connection drops, 429, 5xx). A 4xx is
    a request that will not succeed on a repeat, so it is raised immediately
    rather than burning attempts.
    """
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "target_language_code": language_code,
        "speaker": speaker,
        "model": "bulbul:v3",
        "pace": pace,
        "temperature": 0.01,
        "speech_sample_rate": 48000,
        "output_audio_codec": "wav"
    }
    if dict_id:
        # Swaps registered terms (branding, jargon, mispronounced words) before
        # synthesis. bulbul:v3 only. A dictionary with no entries for this
        # request's language is a harmless no-op, so this is never gated by
        # language_code.
        payload["dict_id"] = dict_id

    last_error = None

    for attempt in range(_TTS_MAX_ATTEMPTS):
        try:
            response = await client.post(_TTS_URL, json=payload, headers=headers)
            response.raise_for_status()

            audios = response.json().get("audios", [])
            if not audios or not audios[0]:
                raise RuntimeError("Sarvam returned no audio data")

            return base64.b64decode(audios[0])

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status != 429 and status < 500:
                raise
            last_error = e
        except (httpx.TimeoutException, httpx.TransportError, RuntimeError) as e:
            last_error = e

        if attempt < _TTS_MAX_ATTEMPTS - 1:
            retry_delay = 2 ** attempt
            print(f"🔄 TTS chunk failed ({last_error}), retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)

    raise last_error


async def synthesize_narration(
    text: str,
    language_code: str,
    speaker: Optional[str] = None,
    pace: Optional[float] = None,
    timeout: float = 60.0,
) -> bytes:
    """
    Synthesize narration of any length into a single WAV.

    Text over Bulbul's per-request limit is split on sentence boundaries and the
    resulting audio is concatenated, so nothing is dropped.

    Args:
        text: Narration text
        language_code: BCP-47 code already validated by resolve_language_code
        speaker: Voice actor name
        pace: Speaking speed
        timeout: Per-request timeout in seconds

    Returns:
        A single WAV file as bytes
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise ValueError("SARVAM_API_KEY not set in environment variables")

    # Optional: id of a Sarvam pronunciation dictionary (branding, jargon,
    # commonly-mispronounced words). Read per-call, not at import time, so
    # tests can set/unset it via the environment like SARVAM_API_KEY above.
    dict_id = os.getenv("SARVAM_PRONUNCIATION_DICT_ID") or None

    chunks = split_text_for_tts(text)
    if not chunks:
        raise ValueError("No narration text to synthesize")

    speaker = speaker or DEFAULT_SPEAKER
    pace = pace if pace is not None else DEFAULT_PACE

    audio_chunks = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        for i, chunk in enumerate(chunks, start=1):
            if len(chunks) > 1:
                print(f"   … TTS chunk {i}/{len(chunks)} ({len(chunk)} chars)")
            audio_chunks.append(
                await _synthesize_chunk(
                    client, chunk, language_code, speaker, pace, api_key, dict_id
                )
            )

    return concat_wav_bytes(audio_chunks)


async def generate_voice_for_slide(
    text: str,
    slide_num: int,
    output_dir: Path,
    language_code: str = "en-IN",
    speaker: Optional[str] = None,
    pace: Optional[float] = None,
) -> Optional[str]:
    """
    Generate audio for a single slide using Sarvam AI TTS (Bulbul v3).

    Args:
        text: Narration text
        slide_num: Slide number
        output_dir: Directory to save audio
        language_code: Language code (e.g. 'en-IN', 'hi-IN')
        speaker: Voice actor name
        pace: Speaking speed

    Returns:
        Path to generated audio file, or None if failed

    Raises:
        UnsupportedLanguageError: if the language has no Sarvam voice
        ValueError: if SARVAM_API_KEY is unset
    """
    # Validate input text
    if not text or not text.strip():
        print(f"⚠️ Slide {slide_num}: Empty narration text, skipping")
        return None

    if not os.getenv("SARVAM_API_KEY"):
        raise ValueError("SARVAM_API_KEY not set in environment variables")

    # Raises rather than falling back to an English voice for an Indic script
    language_code = resolve_language_code(language_code)

    try:
        print(f"🎤 Generating Sarvam TTS audio for slide {slide_num} ({language_code})...")
        audio_bytes = await synthesize_narration(
            text=text,
            language_code=language_code,
            speaker=speaker,
            pace=pace,
            timeout=30.0,
        )
    except UnsplittableTextError:
        # Content problem, not a transport blip — surface the reason rather
        # than reporting it as a generic "no audio" failure.
        raise
    except Exception as e:
        print(f"❌ Detailed Error for slide {slide_num}: {type(e).__name__}: {str(e)}")
        return None

    wav_path = output_dir / f"slide_{slide_num}.wav"
    wav_path.write_bytes(audio_bytes)

    # Verify file was created and has content
    if wav_path.exists() and wav_path.stat().st_size > 0:
        print(f"✓ Generated audio for slide {slide_num} ({wav_path.stat().st_size} bytes)")
        return str(wav_path)

    print(f"⚠️ Slide {slide_num}: Audio file created but is empty or missing")
    return None


async def generate_voice_for_script(
    json_script: dict,
    project_id: Optional[int] = None,
    speaker: Optional[str] = None,
    pace: Optional[float] = None,
) -> Dict:
    """
    Generate audio narration for all slides in a script.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID for file naming
        speaker: Optional voice actor name
        pace: Optional speaking speed
    
    Returns:
        {
            "audio_urls": {0: "/static/audio/...", 1: "...", ...},
            "zip_url": "/static/audio/project_123.zip",
            "success": True/False,
            "errors": []
        }
    """
    import time
    
    if project_id is None:
        project_id = int(time.time())
    
    # Setup output directory
    project_root = Path(__file__).parent.parent.parent
    audio_dir = project_root / "output" / "audio" / f"project_{project_id}"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract narrations
    narrations = extract_narration(json_script)
    
    # Generate audio for each slide
    audio_map = {}
    errors = []

    # Resolve the script language once, before any work — an unsupported
    # language fails the whole request instead of producing wrong-voice audio.
    language_code = resolve_language_code(json_script.get("target_language"))

    if not os.getenv("SARVAM_API_KEY"):
        raise ValueError("SARVAM_API_KEY not set in environment variables")

    for item in narrations:
        slide_num = item['slide_number']
        text = item['narration']

        # Validate text before processing
        if not text or not text.strip():
            errors.append(f"Slide {slide_num}: Empty narration text")
            continue

        # A tiny delay to avoid hitting any burst limits
        await asyncio.sleep(0.1)

        # Retries live in _synthesize_chunk, which retries only transient
        # failures and never re-sends chunks that already succeeded.
        try:
            audio_path = await generate_voice_for_slide(
                text=text,
                slide_num=slide_num,
                output_dir=audio_dir,
                language_code=language_code,
                speaker=speaker,
                pace=pace
            )
        except Exception as e:
            errors.append(f"Slide {slide_num}: {e}")
            continue

        if audio_path:
            relative_path = Path(audio_path).relative_to(project_root / "output")
            audio_map[slide_num] = f"/output/{relative_path}"
            print(f"✅ Successfully generated audio for slide {slide_num}")
        else:
            errors.append(f"Slide {slide_num}: No audio after {_TTS_MAX_ATTEMPTS} attempts")

    # Create ZIP of all audio files
    zip_path = audio_dir / f"audio_project_{project_id}.zip"
    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
        for wav_file in audio_dir.glob("*.wav"):
            zf.write(wav_file, wav_file.name)
    
    zip_relative = zip_path.relative_to(project_root / "output")
    
    print(f"✅ Voice generation complete: {len(audio_map)}/{len(narrations)} slides")
    
    return {
        "audio_urls": audio_map,
        "zip_url": f"/output/{zip_relative}",
        "project_id": project_id,
        "success": len(errors) == 0,
        "errors": errors,
        "total_slides": len(narrations),
        "generated_slides": len(audio_map)
    }


async def _synthesize_slides(
    narrations: List[Dict],
    audio_dir: Path,
    project_root: Path,
    language_code: str,
    speaker: Optional[str],
    pace: Optional[float],
) -> tuple:
    """
    Synthesize each slide into its own file, keeping the audio for stitching.

    Returns:
        (audio_bytes in slide order, {slide_number: url}, errors)
    """
    audio_parts = []
    slide_urls = {}
    errors = []

    for item in narrations:
        slide_num = item['slide_number']
        text = item['narration']

        if not text or not text.strip():
            errors.append(f"Slide {slide_num}: Empty narration text")
            continue

        # A tiny delay to avoid hitting any burst limits
        await asyncio.sleep(0.1)

        try:
            audio_bytes = await synthesize_narration(
                text=text,
                language_code=language_code,
                speaker=speaker,
                pace=pace,
                timeout=30.0,
            )
        except Exception as e:
            errors.append(f"Slide {slide_num}: {type(e).__name__}: {e}")
            continue

        wav_path = audio_dir / f"slide_{slide_num}.wav"
        wav_path.write_bytes(audio_bytes)

        audio_parts.append(audio_bytes)
        slide_urls[slide_num] = f"/output/{wav_path.relative_to(project_root / 'output')}"
        print(f"✓ Generated audio for slide {slide_num} ({len(audio_bytes)} bytes)")

    return audio_parts, slide_urls, errors


def _join_with_gaps(audio_parts: List[bytes], gap_seconds: float) -> bytes:
    """Concatenate audio, optionally inserting a pause between each part."""
    if gap_seconds <= 0 or len(audio_parts) < 2:
        return concat_wav_bytes(audio_parts)

    gap = silence_wav_like(audio_parts[0], gap_seconds)
    spaced = []
    for i, part in enumerate(audio_parts):
        if i:
            spaced.append(gap)
        spaced.append(part)

    return concat_wav_bytes(spaced)


async def generate_voice_combined(
    json_script: dict,
    project_id: Optional[int] = None,
    speaker: Optional[str] = None,
    pace: Optional[float] = None,
    source: str = CONTINUOUS,
    slide_gap_seconds: float = 0.0,
) -> Dict:
    """
    Generate a SINGLE audio file for the entire script.

    Two ways to build it, trading off seam count against control:

    - CONTINUOUS: the whole narration is synthesized as one stream, split only
      where Bulbul's character limit forces it. Fewest seams, so the most
      consistent delivery, but no per-slide files to inspect or redo.
    - PER_SLIDE: each slide is synthesized and saved separately, then stitched.
      Seams land exactly on slide boundaries and you keep every slide's file,
      so a slide that reads badly can be regenerated on its own. More separate
      TTS calls means more places tone or level can drift.

    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID for file naming
        speaker: Optional voice actor name
        pace: Optional speaking speed
        source: CONTINUOUS or PER_SLIDE
        slide_gap_seconds: Pause inserted between slides (PER_SLIDE only)

    Returns:
        {
            "audio_url": "/output/audio/project_123/full_narration.wav",
            "success": True/False,
            "total_slides": 15,
            "duration_estimate": "~5 minutes",
            "slide_audio_urls": {...}   # PER_SLIDE only
        }
    """
    import time
    
    if project_id is None:
        project_id = int(time.time())
    
    # Setup output directory
    project_root = Path(__file__).parent.parent.parent
    audio_dir = project_root / "output" / "audio" / f"project_{project_id}"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract all narrations
    narrations = extract_narration(json_script)
    
    if not narrations:
        return {
            "audio_url": None,
            "success": False,
            "error": "No narrations found in script",
            "total_slides": 0
        }
    
    # Combine all narrations, using space and periods to separate slide narrations naturally
    combined_text = " ".join([n['narration'].rstrip('.') + '.' for n in narrations])
    
    # Estimate duration (~135 words per minute for clear speech)
    word_count = len(combined_text.split())
    duration_minutes = word_count / 135
    
    print(f"📝 Combining {len(narrations)} slides into single audio (~{duration_minutes:.1f} min, {word_count} words)")

    if source not in COMBINE_SOURCES:
        raise ValueError(
            f"Unknown source '{source}'. Expected one of: {', '.join(COMBINE_SOURCES)}."
        )

    # Resolved before any work — an unsupported language fails the whole
    # request rather than producing audio in the wrong voice.
    language_code = resolve_language_code(json_script.get("target_language"))

    slide_urls = {}

    try:
        if source == PER_SLIDE:
            print(f"🎤 Generating audio slide by slide for {len(narrations)} slides...")

            audio_parts, slide_urls, errors = await _synthesize_slides(
                narrations=narrations,
                audio_dir=audio_dir,
                project_root=project_root,
                language_code=language_code,
                speaker=speaker,
                pace=pace,
            )

            # Stitching around a missing slide would produce audio that sounds
            # complete but silently skips content — the failure mode this whole
            # path exists to avoid. Hand back what succeeded instead.
            if errors:
                print(f"❌ {len(errors)} slide(s) failed; not stitching a partial narration")
                return {
                    "audio_url": None,
                    "success": False,
                    "error": "; ".join(errors),
                    "errors": errors,
                    "slide_audio_urls": slide_urls,
                    "project_id": project_id,
                    "total_slides": len(narrations),
                    "generated_slides": len(slide_urls),
                }

            audio_bytes = _join_with_gaps(audio_parts, slide_gap_seconds)
            print(f"🔗 Stitched {len(audio_parts)} slide files into one narration")

        else:
            chunk_count = len(split_text_for_tts(combined_text))
            print(
                f"🎤 Generating continuous audio for {len(narrations)} slides "
                f"({len(combined_text)} chars, {chunk_count} TTS request(s))..."
            )

            audio_bytes = await synthesize_narration(
                text=combined_text,
                language_code=language_code,
                speaker=speaker,
                pace=pace,
                timeout=60.0,
            )

    except Exception as e:
        print(f"❌ Combined voice generation failed: {e}")
        return {
            "audio_url": None,
            "success": False,
            "error": str(e),
            "slide_audio_urls": slide_urls,
            "total_slides": len(narrations)
        }

    wav_path = audio_dir / "full_narration.wav"
    wav_path.write_bytes(audio_bytes)

    if not (wav_path.exists() and wav_path.stat().st_size > 0):
        return {
            "audio_url": None,
            "success": False,
            "error": "Generated file is empty",
            "slide_audio_urls": slide_urls,
            "total_slides": len(narrations)
        }

    relative_path = wav_path.relative_to(project_root / "output")
    duration_seconds, duration_formatted = get_wav_duration(str(wav_path))
    print(f"✅ Generated combined audio ({wav_path.stat().st_size} bytes, {duration_formatted})")

    return {
        "audio_url": f"/output/{relative_path}",
        "project_id": project_id,
        "success": True,
        "source": source,
        "slide_audio_urls": slide_urls,
        "total_slides": len(narrations),
        "generated_slides": len(slide_urls) or len(narrations),
        "word_count": word_count,
        "duration_seconds": duration_seconds,
        "duration_estimate": duration_formatted
    }

