"""
Voice generation service for Spoken Tutorial scripts.
Uses Sarvam AI TTS (Bulbul v3) for audio narration.
"""
import os
import re
import asyncio
import zipfile
import wave
import httpx
import base64
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Map internal 2-letter language codes to Sarvam BCP-47 codes
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
    "as": "en-IN",  # Assamese fallback to English (Indian accent)
}

# Voice configuration constants for Sarvam TTS
# Female voice options: 'shreya', 'neha', 'ritu', 'ishita'
# Male voice options: 'shubh' (default), 'aditya', 'manan'
DEFAULT_SPEAKER = "kavya"
DEFAULT_PACE = 0.9         # Slower pace (1.0 is default)

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
    """Remove markdown and special characters not suitable for TTS."""
    if not text:
        return ""
    
    # Remove bold/italic markers
    text = text.replace('**', '').replace('__', '')
    text = text.replace('*', '').replace('_', '')
    text = text.replace('#', '')
    # Remove bullet points but keep the text
    text = text.replace('•', '')
    text = text.replace('- ', '')  # Remove markdown list markers
    # Remove code blocks
    text = text.replace('`', '')
    # Remove HTML-like tags if any
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace (remove \n, \t, multiple spaces)
    text = ' '.join(text.split())
    # Remove any remaining special characters that might cause issues
    text = text.strip()
    
    # Ensure we have valid text
    if not text:
        return ""
    
    return text


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
    """
    # Validate input text
    if not text or not text.strip():
        print(f"⚠️ Slide {slide_num}: Empty narration text, skipping")
        return None
    
    # Ensure text is not too long (API limits: 2500 chars for bulbul:v3)
    if len(text) > 2500:
        print(f"⚠️ Slide {slide_num}: Text too long ({len(text)} chars), truncating to 2500")
        text = text[:2500]
    
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise ValueError("SARVAM_API_KEY not set in environment variables")
    
    # Map 2-letter code to BCP-47 if needed
    if "-" not in language_code:
        language_code = SARVAM_LANG_MAP.get(language_code.lower(), "en-IN")
        
    # Use custom speaker/pace or fall back to defaults
    speaker = speaker or DEFAULT_SPEAKER
    pace = pace if pace is not None else DEFAULT_PACE
    
    url = "https://api.sarvam.ai/text-to-speech"
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
        "temperature": 0.6,
        "speech_sample_rate": 24000,
        "output_audio_codec": "wav"
    }
    
    try:
        print(f"🎤 Generating Sarvam TTS audio for slide {slide_num} ({language_code})...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            response_data = response.json()
            audios = response_data.get("audios", [])
            
            if not audios or not audios[0]:
                print(f"⚠️ Slide {slide_num}: Empty audio data received")
                return None
                
            audio_base64 = audios[0]
            audio_bytes = base64.b64decode(audio_base64)
            
            wav_path = output_dir / f"slide_{slide_num}.wav"
            with open(wav_path, "wb") as f:
                f.write(audio_bytes)
                
            # Verify file was created and has content
            if wav_path.exists() and wav_path.stat().st_size > 0:
                print(f"✓ Generated audio for slide {slide_num} ({wav_path.stat().st_size} bytes)")
                return str(wav_path)
            else:
                print(f"⚠️ Slide {slide_num}: Audio file created but is empty or missing")
                return None
                
    except Exception as e:
        print(f"❌ Detailed Error for slide {slide_num}: {type(e).__name__}: {str(e)}")
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
    
    # Retrieve script language
    raw_lang = json_script.get("target_language", "en")
    
    for item in narrations:
        slide_num = item['slide_number']
        text = item['narration']
        
        # Validate text before processing
        if not text or not text.strip():
            errors.append(f"Slide {slide_num}: Empty narration text")
            continue
        
        # A tiny delay to avoid hitting any burst limits
        await asyncio.sleep(0.1)
        
        # Retry logic for failed attempts
        max_retries = 3
        audio_path = None
        
        for attempt in range(max_retries):
            try:
                audio_path = await generate_voice_for_slide(
                    text=text,
                    slide_num=slide_num,
                    output_dir=audio_dir,
                    language_code=raw_lang,
                    speaker=speaker,
                    pace=pace
                )
                
                if audio_path:
                    # Success - convert to URL path
                    relative_path = Path(audio_path).relative_to(project_root / "output")
                    audio_map[slide_num] = f"/output/{relative_path}"
                    print(f"✅ Successfully generated audio for slide {slide_num}")
                    break  # Exit retry loop on success
                else:
                    # Empty response - retry after delay
                    if attempt < max_retries - 1:
                        retry_delay = 2 + attempt
                        print(f"🔄 Retrying slide {slide_num} (attempt {attempt + 2}/{max_retries}) after {retry_delay}s delay...")
                        await asyncio.sleep(retry_delay)
                    else:
                        errors.append(f"Slide {slide_num}: No audio after {max_retries} attempts")
                        
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    retry_delay = 2 + attempt
                    print(f"🔄 Retrying slide {slide_num} after error: {e} (attempt {attempt + 2}/{max_retries}) after {retry_delay}s delay...")
                    await asyncio.sleep(retry_delay)
                else:
                    errors.append(f"Slide {slide_num}: {error_msg}")
    
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


async def generate_voice_combined(
    json_script: dict,
    project_id: Optional[int] = None,
    speaker: Optional[str] = None,
    pace: Optional[float] = None,
) -> Dict:
    """
    Generate a SINGLE audio file for the entire script using a single Sarvam AI call.
    
    Combines all slide narrations into one audio file.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID for file naming
        speaker: Optional voice actor name
        pace: Optional speaking speed
    
    Returns:
        {
            "audio_url": "/output/audio/project_123/full_narration.wav",
            "success": True/False,
            "total_slides": 15,
            "duration_estimate": "~5 minutes"
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
    
    # Check text length - Sarvam TTS has a strict 2,500 character limit
    if len(combined_text) > 2500:
        print(f"⚠️ Combined script too long ({len(combined_text)} chars), truncating to 2500 to fit Sarvam API limits.")
        combined_text = combined_text[:2500]
        word_count = len(combined_text.split())
    
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        return {
            "audio_url": None,
            "success": False,
            "error": "SARVAM_API_KEY not set",
            "total_slides": len(narrations)
        }
        
    raw_lang = json_script.get("target_language", "en")
    lang_code = SARVAM_LANG_MAP.get(raw_lang.lower(), "en-IN") if "-" not in raw_lang else raw_lang
    
    # Use custom values or fall back to defaults
    speaker = speaker or DEFAULT_SPEAKER
    pace = pace if pace is not None else DEFAULT_PACE
    
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": combined_text,
        "target_language_code": lang_code,
        "speaker": speaker,
        "model": "bulbul:v3",
        "pace": pace,
        "temperature": 0.6,
        "speech_sample_rate": 24000,
        "output_audio_codec": "wav"
    }
    
    # DEBUG: Print exactly what we're sending to TTS
    print("\n" + "="*80)
    print("🔍 DEBUG: Full prompt being sent to Sarvam TTS:")
    print("="*80)
    print(combined_text)
    print("="*80 + "\n")
    
    try:
        print(f"🎤 Generating combined audio for {len(narrations)} slides...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            response_data = response.json()
            audios = response_data.get("audios", [])
            
            if not audios or not audios[0]:
                return {
                    "audio_url": None,
                    "success": False,
                    "error": "No audio returned from Sarvam API",
                    "total_slides": len(narrations)
                }
                
            audio_base64 = audios[0]
            audio_bytes = base64.b64decode(audio_base64)
            
            wav_path = audio_dir / "full_narration.wav"
            with open(wav_path, "wb") as f:
                f.write(audio_bytes)
                
            if wav_path.exists() and wav_path.stat().st_size > 0:
                relative_path = wav_path.relative_to(project_root / "output")
                
                from src.utils.audio_utils import get_wav_duration
                duration_seconds, duration_formatted = get_wav_duration(str(wav_path))
                print(f"✅ Generated combined audio ({wav_path.stat().st_size} bytes, {duration_formatted})")
                
                return {
                    "audio_url": f"/output/{relative_path}",
                    "project_id": project_id,
                    "success": True,
                    "total_slides": len(narrations),
                    "word_count": word_count,
                    "duration_seconds": duration_seconds,
                    "duration_estimate": duration_formatted
                }
            
            return {
                "audio_url": None,
                "success": False,
                "error": "Generated file is empty",
                "total_slides": len(narrations)
            }
            
    except Exception as e:
        print(f"❌ Combined voice generation failed: {e}")
        return {
            "audio_url": None,
            "success": False,
            "error": str(e),
            "total_slides": len(narrations)
        }

