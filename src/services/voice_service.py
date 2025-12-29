"""
Voice generation service for Spoken Tutorial scripts.
Uses Gemini 2.5 Flash TTS for audio narration.

Designed with abstraction layer for easy migration to Google Cloud TTS with SSML.
"""
import os
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
    
    for i, slide in enumerate(slides):
        narration = slide.get('narration', '')
        
        # Handle list or string
        if isinstance(narration, list):
            narration = ' '.join(narration)
        
        # Fallback to title if no narration
        if not narration.strip():
            narration = slide.get('title', f'Slide {i+1}')
        
        # Clean markdown formatting for TTS
        narration = clean_text_for_tts(narration)
        
        narrations.append({
            'slide_number': slide.get('slide_number', i + 1),
            'narration': narration
        })
    
    return narrations


def clean_text_for_tts(text: str) -> str:
    """Remove markdown and special characters not suitable for TTS."""
    # Remove bold/italic markers
    text = text.replace('**', '').replace('__', '')
    text = text.replace('*', '').replace('_', '')
    text = text.replace('#', '')
    # Remove bullet points
    text = text.replace('•', '')
    # Normalize whitespace (remove \n, \t, multiple spaces)
    text = ' '.join(text.split())
    return text.strip()


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
        
        if not response.parts:
            print(f"⚠️ Empty response for batch {batch_num}")
            return None
        
        for part in response.parts:
            if part.inline_data:
                pcm_data = part.inline_data.data
                wav_path = output_dir / f"batch_{batch_num}.wav"
                
                from src.utils.audio_utils import wave_file
                wave_file(str(wav_path), pcm_data)
                
                print(f"✓ Generated batch {batch_num} audio")
                return str(wav_path)
        
        return None
        
    except Exception as e:
        print(f"❌ Failed batch {batch_num}: {e}")
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
        if candidate.finish_reason != 'STOP' and candidate.finish_reason != 'COMPLETE':
             print(f"🛑 Slide {slide_num} Finish Reason: {candidate.finish_reason}")
             if candidate.safety_ratings:
                 print(f"🛡️ Safety Ratings: {[r.category + ': ' + r.probability for r in candidate.safety_ratings]}")
        # --- END DEBUG LOGGING ---

        # Check if response has parts
        if not response.parts:
            print(f"⚠️ Empty response for slide {slide_num} - API may have blocked or failed")
            return None
        
        # Extract audio data
        for part in response.parts:
            if part.inline_data:
                # Gemini returns raw PCM data - use wave_file to add proper WAV headers
                pcm_data = part.inline_data.data
                wav_path = output_dir / f"slide_{slide_num}.wav"
                
                # Use audio_utils to create proper WAV file with headers
                from src.utils.audio_utils import wave_file
                wave_file(str(wav_path), pcm_data)
                
                print(f"✓ Generated audio for slide {slide_num}")
                return str(wav_path)
        
        print(f"⚠️ No audio data returned for slide {slide_num}")
        return None
        
    except Exception as e:
        # Log the full error type and message
        print(f"❌ Detailed Error for slide {slide_num}: {type(e).__name__}: {str(e)}")
        if "429" in str(e):
             print("💡 Suggestion: This is a Rate Limit error. We might need to increase sleep duration.")
        elif "400" in str(e):
             print("💡 Suggestion: Bad Request. Could be malformed text or unsupported characters.")
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
        
        # Rate limit: Gemini TTS has ~10 RPM limit
        await asyncio.sleep(4)
        
        # Retry logic for failed attempts
        max_retries = 3
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
                    break  # Exit retry loop on success
                else:
                    # Empty response - retry after delay
                    if attempt < max_retries - 1:
                        print(f"🔄 Retrying slide {slide_num} (attempt {attempt + 2}/{max_retries}) after delay...")
                        await asyncio.sleep(6)  # Increased delay for reliability
                    else:
                        errors.append(f"Slide {slide_num}: No audio after {max_retries} attempts")
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying slide {slide_num} after error: {e}")
                    await asyncio.sleep(6)
                else:
                    errors.append(f"Slide {slide_num}: {str(e)}")
    
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
        # Rate limit between batches
        await asyncio.sleep(7)
        
        # Generate batch audio
        batch_path = await generate_voice_for_batch(
            combined_text=batch['combined_text'],
            batch_num=batch['batch_num'],
            output_dir=audio_dir,
        )
        
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
            
            # Check for missing slides
            for slide_num in batch['slide_numbers']:
                if slide_num not in audio_map:
                    errors.append(f"Slide {slide_num}: Split failed")
            
            # Clean up batch file after splitting
            Path(batch_path).unlink(missing_ok=True)
        else:
            # Batch failed - fallback to individual generation for this batch
            print(f"⚠️ Batch {batch['batch_num']} failed - trying individual slides...")
            for slide_num in batch['slide_numbers']:
                narration = next((n for n in narrations if n['slide_number'] == slide_num), None)
                if narration:
                    # Retry logic for fallback slides
                    max_fallback_retries = 2
                    for fallback_attempt in range(max_fallback_retries):
                        if fallback_attempt > 0:
                            print(f"🔄 Fallback retry for slide {slide_num} (attempt {fallback_attempt + 1}/{max_fallback_retries})...")
                        
                        await asyncio.sleep(7)
                        audio_path = await generate_voice_for_slide(
                            text=narration['narration'],
                            slide_num=slide_num,
                            output_dir=audio_dir,
                        )
                        if audio_path:
                            relative_path = Path(audio_path).relative_to(project_root / "output")
                            audio_map[slide_num] = f"/output/{relative_path}"
                            break
                        elif fallback_attempt == max_fallback_retries - 1:
                            errors.append(f"Slide {slide_num}: Failed after fallback retries")
    
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
