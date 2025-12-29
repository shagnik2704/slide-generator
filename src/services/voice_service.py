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


# === TTS Configuration ===

# Single voice and prompt for consistent narration
DEFAULT_VOICE = "Laomedeia"
DEFAULT_PROMPT = """Speak as an instructor for a Spoken Tutorial video. Use an Indian English accent.
Follow these guidelines:
- Speak clearly, at a pace that allows learners to follow along on their computers.
- Pause briefly after each sentence to give learners time to process.
- Use a tone as if teaching a student one-on-one."""



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


# === Batched TTS Configuration ===
BATCH_SIZE = 5  # Number of slides per batch
PAUSE_MARKER = "... ... ..."  # Creates ~1.5s pause in TTS


def batch_narrations(narrations: List[Dict], batch_size: int = BATCH_SIZE) -> List[Dict]:
    """
    Group narrations into batches for fewer API calls.
    
    Returns:
        List of batches, each with combined text and slide info
    """
    batches = []
    
    for i in range(0, len(narrations), batch_size):
        batch_slides = narrations[i:i + batch_size]
        
        # Combine narrations with pause markers (after each slide's text is cleaned)
        combined_text = f" {PAUSE_MARKER} ".join([s['narration'] for s in batch_slides])
        
        batches.append({
            'batch_num': len(batches) + 1,
            'slide_numbers': [s['slide_number'] for s in batch_slides],
            'combined_text': combined_text,
            'slide_count': len(batch_slides)
        })
    
    return batches


def split_audio_on_silence(audio_path: str, expected_segments: int, output_dir: Path, slide_numbers: List[int]) -> Dict[int, str]:
    """
    Split a single audio file into multiple segments based on silence.
    
    Args:
        audio_path: Path to the combined audio file
        expected_segments: Number of segments we expect to find
        output_dir: Directory to save split audio files
        slide_numbers: List of slide numbers for naming
    
    Returns:
        Dict mapping slide_number to audio file path
    """
    try:
        from pydub import AudioSegment
        from pydub.silence import split_on_silence
    except ImportError:
        print("⚠️ pydub not installed - falling back to individual requests")
        return {}
    
    try:
        # Load the combined audio
        audio = AudioSegment.from_wav(audio_path)
        
        # Split on silence
        segments = split_on_silence(
            audio,
            min_silence_len=800,      # 0.8 second of silence
            silence_thresh=-40,        # dB threshold for silence
            keep_silence=300           # Keep 300ms padding on each side
        )
        
        print(f"📊 Found {len(segments)} segments (expected {expected_segments})")
        
        result = {}
        
        # Map segments to slide numbers
        for i, segment in enumerate(segments):
            if i < len(slide_numbers):
                slide_num = slide_numbers[i]
                segment_path = output_dir / f"slide_{slide_num}.wav"
                segment.export(str(segment_path), format="wav")
                result[slide_num] = str(segment_path)
                print(f"  ✓ Saved slide_{slide_num}.wav ({len(segment)}ms)")
        
        return result
        
    except Exception as e:
        print(f"❌ Error splitting audio: {e}")
        return {}


async def generate_voice_for_batch(
    combined_text: str,
    batch_num: int,
    output_dir: Path,
) -> Optional[str]:
    """
    Generate audio for a batch of combined narrations.
    
    Args:
        combined_text: Combined narration text with pause markers
        batch_num: Batch number for logging
        output_dir: Directory to save audio
    
    Returns:
        Path to generated audio file, or None if failed
    """
    # Validate input text
    if not combined_text or not combined_text.strip():
        print(f"⚠️ Batch {batch_num}: Empty combined text, skipping")
        return None
    
    # Ensure text is not too long (API limits)
    if len(combined_text) > 10000:
        print(f"⚠️ Batch {batch_num}: Text too long ({len(combined_text)} chars), truncating to 10000")
        combined_text = combined_text[:10000]
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    full_prompt = f"{DEFAULT_PROMPT}\n\n{combined_text}"
    
    try:
        print(f"🎤 Generating audio for batch {batch_num}...")
        
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
        
        # Check for candidate issues
        if not response.candidates:
            print(f"⚠️ Batch {batch_num}: No candidates returned")
            return None
        
        candidate = response.candidates[0]
        if hasattr(candidate, 'finish_reason'):
            if candidate.finish_reason not in ('STOP', 'COMPLETE'):
                print(f"🛑 Batch {batch_num} Finish Reason: {candidate.finish_reason}")
                return None
        
        if not response.parts:
            print(f"⚠️ Empty response for batch {batch_num}")
            return None
        
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                pcm_data = part.inline_data.data
                
                if not pcm_data or len(pcm_data) == 0:
                    print(f"⚠️ Batch {batch_num}: Empty audio data received")
                    continue
                
                wav_path = output_dir / f"batch_{batch_num}.wav"
                
                from src.utils.audio_utils import wave_file
                wave_file(str(wav_path), pcm_data)
                
                # Verify file was created and has content
                if wav_path.exists() and wav_path.stat().st_size > 0:
                    print(f"✓ Generated batch {batch_num} audio ({wav_path.stat().st_size} bytes)")
                    return str(wav_path)
                else:
                    print(f"⚠️ Batch {batch_num}: Audio file created but is empty or missing")
        
        return None
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed batch {batch_num}: {type(e).__name__}: {error_msg}")
        if "429" in error_msg or "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
            print("💡 Suggestion: Rate limit error - will retry with longer delay")
            raise  # Re-raise to trigger retry logic
        elif "timeout" in error_msg.lower():
            print("💡 Suggestion: Request timed out - will retry")
            raise  # Re-raise to trigger retry logic
        return None


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


async def generate_voice_for_script_batched(
    json_script: dict,
    project_id: Optional[int] = None,
) -> Dict:
    """
    Generate audio using BATCHED approach - fewer API calls!
    
    Combines multiple slide narrations into batches, generates fewer audio files,
    then splits them using silence detection.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID for file naming
    
    Returns:
        Same format as generate_voice_for_script
    """
    import time
    
    if project_id is None:
        project_id = int(time.time())
    
    # Setup output directory
    project_root = Path(__file__).parent.parent.parent
    audio_dir = project_root / "output" / "audio" / f"project_{project_id}"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract and batch narrations
    narrations = extract_narration(json_script)
    batches = batch_narrations(narrations, BATCH_SIZE)
    
    print(f"📦 Batched {len(narrations)} slides into {len(batches)} batches")
    
    audio_map = {}
    errors = []
    
    for batch in batches:
        # Rate limit between batches - increased delay
        await asyncio.sleep(8)
        
        # Generate batch audio with retry logic
        max_batch_retries = 3
        batch_path = None
        
        for batch_attempt in range(max_batch_retries):
            try:
                batch_path = await generate_voice_for_batch(
                    combined_text=batch['combined_text'],
                    batch_num=batch['batch_num'],
                    output_dir=audio_dir,
                )
                
                if batch_path:
                    break  # Success
                elif batch_attempt < max_batch_retries - 1:
                    retry_delay = 10 + (batch_attempt * 2)
                    print(f"🔄 Retrying batch {batch['batch_num']} (attempt {batch_attempt + 2}/{max_batch_retries}) after {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
            except Exception as e:
                if batch_attempt < max_batch_retries - 1:
                    retry_delay = 10 + (batch_attempt * 2)
                    print(f"🔄 Retrying batch {batch['batch_num']} after error: {e} (attempt {batch_attempt + 2}/{max_batch_retries}) after {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"❌ Batch {batch['batch_num']} failed after {max_batch_retries} attempts: {e}")
        
        if batch_path:
            # Split the batch audio into individual slide audios
            split_results = split_audio_on_silence(
                audio_path=batch_path,
                expected_segments=batch['slide_count'],
                output_dir=audio_dir,
                slide_numbers=batch['slide_numbers']
            )
            
            # Update audio map with split results
            for slide_num, audio_path in split_results.items():
                relative_path = Path(audio_path).relative_to(project_root / "output")
                audio_map[slide_num] = f"/output/{relative_path}"
            
            # Check for missing slides and fallback to individual generation
            for slide_num in batch['slide_numbers']:
                if slide_num not in audio_map:
                    print(f"⚠️ Slide {slide_num}: Split failed, trying individual generation...")
                    narration = next((n for n in narrations if n['slide_number'] == slide_num), None)
                    if narration:
                        # Retry logic for fallback slides
                        max_fallback_retries = 3
                        for fallback_attempt in range(max_fallback_retries):
                            if fallback_attempt > 0:
                                print(f"🔄 Fallback retry for slide {slide_num} (attempt {fallback_attempt + 1}/{max_fallback_retries})...")
                            
                            await asyncio.sleep(7)
                            try:
                                audio_path = await generate_voice_for_slide(
                                    text=narration['narration'],
                                    slide_num=slide_num,
                                    output_dir=audio_dir,
                                )
                                if audio_path:
                                    relative_path = Path(audio_path).relative_to(project_root / "output")
                                    audio_map[slide_num] = f"/output/{relative_path}"
                                    print(f"✅ Fallback generation succeeded for slide {slide_num}")
                                    break
                            except Exception as e:
                                if fallback_attempt == max_fallback_retries - 1:
                                    errors.append(f"Slide {slide_num}: Failed after {max_fallback_retries} fallback attempts: {str(e)}")
                                else:
                                    await asyncio.sleep(8)
                    else:
                        errors.append(f"Slide {slide_num}: Narration not found for fallback")
            
            # Clean up batch file after splitting
            Path(batch_path).unlink(missing_ok=True)
        else:
            # Batch failed - fallback to individual generation for this batch
            print(f"⚠️ Batch {batch['batch_num']} failed - trying individual slides...")
            for slide_num in batch['slide_numbers']:
                narration = next((n for n in narrations if n['slide_number'] == slide_num), None)
                if narration:
                    # Retry logic for fallback slides
                    max_fallback_retries = 3
                    for fallback_attempt in range(max_fallback_retries):
                        if fallback_attempt > 0:
                            print(f"🔄 Fallback retry for slide {slide_num} (attempt {fallback_attempt + 1}/{max_fallback_retries})...")
                        
                        await asyncio.sleep(7)
                        try:
                            audio_path = await generate_voice_for_slide(
                                text=narration['narration'],
                                slide_num=slide_num,
                                output_dir=audio_dir,
                            )
                            if audio_path:
                                relative_path = Path(audio_path).relative_to(project_root / "output")
                                audio_map[slide_num] = f"/output/{relative_path}"
                                print(f"✅ Fallback generation succeeded for slide {slide_num}")
                                break
                            elif fallback_attempt == max_fallback_retries - 1:
                                errors.append(f"Slide {slide_num}: Failed after {max_fallback_retries} fallback attempts")
                        except Exception as e:
                            if fallback_attempt == max_fallback_retries - 1:
                                errors.append(f"Slide {slide_num}: Failed after {max_fallback_retries} fallback attempts: {str(e)}")
                            else:
                                await asyncio.sleep(8)
                else:
                    errors.append(f"Slide {slide_num}: Narration not found")
    
    # Create ZIP of all audio files
    zip_path = audio_dir / f"audio_project_{project_id}.zip"
    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
        for wav_file in audio_dir.glob("slide_*.wav"):
            zf.write(wav_file, wav_file.name)
    
    zip_relative = zip_path.relative_to(project_root / "output")
    
    print(f"✅ Batched voice generation complete: {len(audio_map)}/{len(narrations)} slides")
    print(f"📊 Used {len(batches)} API calls instead of {len(narrations)}")
    
    return {
        "audio_urls": audio_map,
        "zip_url": f"/output/{zip_relative}",
        "project_id": project_id,
        "success": len(errors) == 0,
        "errors": errors,
        "total_slides": len(narrations),
        "generated_slides": len(audio_map),
        "batches_used": len(batches),
        "api_calls_saved": len(narrations) - len(batches)
    }


# === Future: Google Cloud TTS with SSML ===
# 
# To switch to Google Cloud TTS:
# 1. Install: pip install google-cloud-texttospeech
# 2. Set GOOGLE_APPLICATION_CREDENTIALS env var
# 3. Replace generate_voice_for_slide with:
#
# async def generate_voice_for_slide_gcloud(ssml_text: str, ...):
#     from google.cloud import texttospeech
#     client = texttospeech.TextToSpeechClient()
#     synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
#     voice = texttospeech.VoiceSelectionParams(
#         language_code="en-IN", name="en-IN-Wavenet-D"
#     )
#     audio_config = texttospeech.AudioConfig(
#         audio_encoding=texttospeech.AudioEncoding.MP3
#     )
#     response = client.synthesize_speech(
#         input=synthesis_input, voice=voice, audio_config=audio_config
#     )
#     with open(output_path, "wb") as f:
#         f.write(response.audio_content)
