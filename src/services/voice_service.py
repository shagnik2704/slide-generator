"""
Voice generation service for Spoken Tutorial scripts.
Uses Gemini 2.5 Flash TTS for audio narration.

Designed with abstraction layer for easy migration to Google Cloud TTS with SSML.
"""
import os
import re
import asyncio
import zipfile
import wave
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


# Single voice and prompt for consistent narration
DEFAULT_VOICE = "Leda"
DEFAULT_PROMPT = """Speak as an instructor for a Spoken Tutorial video. Use an Indian English accent.

SPEAKING STYLE:
- Be ENERGETIC and Speak SLOWLY and clearly, at about 135 words per minute.
- Allow learners time to follow along on their computers.
- Pause for 1 full second after each sentence.
- When you see [PAUSE], stop speaking for 2 seconds before continuing.
- Use a calm, patient, teaching tone as if guiding a beginner one-on-one.
"""

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


PAUSE_MARKER = "\n[PAUSE]\n"  # Explicit pause marker



async def generate_voice_for_slide(
    text: str, 
    slide_num: int, 
    output_dir: Path,
) -> Optional[str]:
    """
    Generate audio for a single slide.
    
    Args:
        text: Narration text
        slide_num: Slide number
        output_dir: Directory to save audio
    
    Returns:
        Path to generated audio file, or None if failed
    """
    # Validate input text
    if not text or not text.strip():
        print(f"⚠️ Slide {slide_num}: Empty narration text, skipping")
        return None
    
    # Ensure text is not too long (API limits)
    if len(text) > 5000:
        print(f"⚠️ Slide {slide_num}: Text too long ({len(text)} chars), truncating to 5000")
        text = text[:5000]
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    full_prompt = f"{DEFAULT_PROMPT} {text}"
    
    try:
        print(f"🎤 Generating audio for slide {slide_num}...")
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=DEFAULT_VOICE
                        )
                    )
                )
            )
        )
        
        # --- DEBUG LOGGING ---
        # 1. Check prompt feedback (Blocking before generation)
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            print(f"🔍 Slide {slide_num} Prompt Feedback: {response.prompt_feedback}")
            
        # 2. Check for candidate issues
        if not response.candidates:
            print(f"⚠️ Slide {slide_num}: No candidates returned. This usually means the safety filter blocked the prompt.")
            return None
            
        candidate = response.candidates[0]
        
        # Check finish reason - if not successful, return None
        if hasattr(candidate, 'finish_reason'):
            if candidate.finish_reason not in ('STOP', 'COMPLETE'):
                print(f"🛑 Slide {slide_num} Finish Reason: {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    print(f"🛡️ Safety Ratings: {[r.category + ': ' + r.probability for r in candidate.safety_ratings]}")
                return None
        # --- END DEBUG LOGGING ---

        # Check if response has parts
        if not response.parts:
            print(f"⚠️ Empty response for slide {slide_num} - API may have blocked or failed")
            return None
        
        # Extract audio data
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                # Gemini returns raw PCM data - use wave_file to add proper WAV headers
                pcm_data = part.inline_data.data
                
                if not pcm_data or len(pcm_data) == 0:
                    print(f"⚠️ Slide {slide_num}: Empty audio data received")
                    continue
                
                wav_path = output_dir / f"slide_{slide_num}.wav"
                
                # Use audio_utils to create proper WAV file with headers
                from src.utils.audio_utils import wave_file
                wave_file(str(wav_path), pcm_data)
                
                # Verify file was created and has content
                if wav_path.exists() and wav_path.stat().st_size > 0:
                    print(f"✓ Generated audio for slide {slide_num} ({wav_path.stat().st_size} bytes)")
                    return str(wav_path)
                else:
                    print(f"⚠️ Slide {slide_num}: Audio file created but is empty or missing")
        
        print(f"⚠️ No audio data returned for slide {slide_num}")
        return None
        
    except Exception as e:
        # Log the full error type and message
        error_msg = str(e)
        print(f"❌ Detailed Error for slide {slide_num}: {type(e).__name__}: {error_msg}")
        if "429" in error_msg or "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
             print("💡 Suggestion: This is a Rate Limit error. Retrying with longer delay...")
             raise  # Re-raise to trigger retry logic
        elif "400" in error_msg or "bad request" in error_msg.lower():
             print("💡 Suggestion: Bad Request. Could be malformed text or unsupported characters.")
        elif "timeout" in error_msg.lower():
             print("💡 Suggestion: Request timed out. Retrying...")
             raise  # Re-raise to trigger retry logic
        return None


async def generate_voice_for_script(
    json_script: dict,
    project_id: Optional[int] = None,
) -> Dict:
    """
    Generate audio narration for all slides in a script.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID for file naming
    
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
    
    for item in narrations:
        slide_num = item['slide_number']
        text = item['narration']
        
        # Validate text before processing
        if not text or not text.strip():
            errors.append(f"Slide {slide_num}: Empty narration text")
            continue
        
        # Rate limit: Gemini TTS has ~10 RPM limit, use 7 seconds to be safe
        await asyncio.sleep(7)
        
        # Retry logic for failed attempts
        max_retries = 5  # Increased retries for better reliability
        audio_path = None
        
        for attempt in range(max_retries):
            try:
                audio_path = await generate_voice_for_slide(
                    text=text,
                    slide_num=slide_num,
                    output_dir=audio_dir,
                )
                
                if audio_path:
                    # Success - convert to URL path
                    relative_path = Path(audio_path).relative_to(project_root / "output")
                    audio_map[slide_num] = f"/output/{relative_path}"
                    print(f"✅ Successfully generated audio for slide {slide_num}")
                    break  # Exit retry loop on success
                else:
                    # Empty response - retry after delay with exponential backoff
                    if attempt < max_retries - 1:
                        retry_delay = 8 + (attempt * 2)  # 8, 10, 12, 14 seconds
                        print(f"🔄 Retrying slide {slide_num} (attempt {attempt + 2}/{max_retries}) after {retry_delay}s delay...")
                        await asyncio.sleep(retry_delay)
                    else:
                        errors.append(f"Slide {slide_num}: No audio after {max_retries} attempts")
                        
            except Exception as e:
                error_msg = str(e)
                # Check if it's a rate limit or timeout error that should be retried
                if attempt < max_retries - 1 and ("429" in error_msg or "rate limit" in error_msg.lower() or "timeout" in error_msg.lower() or "quota" in error_msg.lower()):
                    retry_delay = 10 + (attempt * 3)  # 10, 13, 16, 19 seconds for rate limits
                    print(f"🔄 Retrying slide {slide_num} after rate limit/timeout error (attempt {attempt + 2}/{max_retries}) after {retry_delay}s delay...")
                    await asyncio.sleep(retry_delay)
                elif attempt < max_retries - 1:
                    retry_delay = 8 + (attempt * 2)
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
) -> Dict:
    """
    Generate a SINGLE audio file for the entire script.
    
    Combines all slide narrations with pauses between them into one audio file.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID for file naming
    
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
    
    # Combine all narrations with pause markers
    combined_text = f" {PAUSE_MARKER} ".join([n['narration'] for n in narrations])
    
    # Estimate duration (~150 words per minute for clear speech)
    word_count = len(combined_text.split())
    duration_minutes = word_count / 150
    
    print(f"📝 Combining {len(narrations)} slides into single audio (~{duration_minutes:.1f} min, {word_count} words)")
    
    # Check text length - Gemini TTS has limits
    if len(combined_text) > 10000:
        print(f"⚠️ Text too long ({len(combined_text)} chars), may need to be chunked")
        # For now, truncate (you could also split into multiple TTS calls and concatenate)
        combined_text = combined_text[:10000]
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"audio_url": None, "success": False, "error": "GOOGLE_API_KEY not set"}
    
    client = genai.Client(api_key=api_key)
    
    full_prompt = f"{DEFAULT_PROMPT}\n\n{combined_text}"
    
    # DEBUG: Print exactly what we're sending to TTS
    print("\n" + "="*80)
    print("🔍 DEBUG: Full prompt being sent to TTS:")
    print("="*80)
    print(full_prompt[:2000])  # First 2000 chars
    if len(full_prompt) > 2000:
        print(f"\n... [{len(full_prompt) - 2000} more characters]")
    print("="*80 + "\n")
    
    try:
        print(f"🎤 Generating combined audio for {len(narrations)} slides...")

        
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=DEFAULT_VOICE
                        )
                    )
                )
            )
        )
        
        if not response.candidates or not response.parts:
            return {
                "audio_url": None,
                "success": False,
                "error": "No audio returned from TTS API",
                "total_slides": len(narrations)
            }
        
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                pcm_data = part.inline_data.data
                
                if not pcm_data or len(pcm_data) == 0:
                    continue
                
                wav_path = audio_dir / f"full_narration.wav"
                
                from src.utils.audio_utils import wave_file, get_wav_duration
                wave_file(str(wav_path), pcm_data)
                
                if wav_path.exists() and wav_path.stat().st_size > 0:
                    relative_path = wav_path.relative_to(project_root / "output")
                    
                    # Get actual duration from the WAV file
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
            "error": "No audio data in response",
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
