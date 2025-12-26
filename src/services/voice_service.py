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

TTS_PROMPTS = {
    'kids': "Speak in a friendly, enthusiastic tone suitable for children. Use simple words and clear pronunciation.",
    'students': "Speak clearly and at a moderate pace, suitable for educational content. Be engaging but professional.",
    'professionals': "Speak in a professional, authoritative tone. Be concise and clear.",
    'general': "Speak clearly and naturally, as if explaining to a friend. Use a warm, engaging tone."
}

VOICE_MAPPING = {
    'kids': "Tevel",
    'students': "Kore", 
    'professionals': "Ophir",
    'general': "Kore"
}


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
    return text.strip()


async def generate_voice_for_slide(
    text: str, 
    slide_num: int, 
    output_dir: Path,
    voice: str = "Kore",
    audience: str = "general"
) -> Optional[str]:
    """
    Generate audio for a single slide.
    
    Args:
        text: Narration text
        slide_num: Slide number
        output_dir: Directory to save audio
        voice: Voice name (Kore, Tevel, Ophir, etc.)
        audience: Target audience for prompt styling
    
    Returns:
        Path to generated audio file, or None if failed
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    voice_instruction = TTS_PROMPTS.get(audience, TTS_PROMPTS['general'])
    full_prompt = f"{voice_instruction} {text}"
    
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
                            voice_name=voice
                        )
                    )
                )
            )
        )
        
        # Extract audio data
        for part in response.parts:
            if part.inline_data:
                # Gemini returns WAV data - save directly
                wav_data = part.inline_data.data
                wav_path = output_dir / f"slide_{slide_num}.wav"
                
                # Save WAV file directly
                with open(str(wav_path), 'wb') as f:
                    f.write(wav_data)
                
                print(f"✓ Generated audio for slide {slide_num}")
                return str(wav_path)
        
        print(f"⚠️ No audio data returned for slide {slide_num}")
        return None
        
    except Exception as e:
        print(f"❌ Failed audio for slide {slide_num}: {e}")
        return None


async def generate_voice_for_script(
    json_script: dict,
    project_id: Optional[int] = None,
    target_audience: str = "general"
) -> Dict:
    """
    Generate audio narration for all slides in a script.
    
    Args:
        json_script: The parsed script JSON
        project_id: Optional project ID for file naming
        target_audience: kids, students, professionals, or general
    
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
    
    # Select voice based on audience
    voice = VOICE_MAPPING.get(target_audience, "Kore")
    
    # Generate audio for each slide
    audio_map = {}
    errors = []
    
    for item in narrations:
        slide_num = item['slide_number']
        text = item['narration']
        
        # Rate limit: Gemini TTS has ~10 RPM limit
        await asyncio.sleep(7)
        
        try:
            audio_path = await generate_voice_for_slide(
                text=text,
                slide_num=slide_num,
                output_dir=audio_dir,
                voice=voice,
                audience=target_audience
            )
            
            if audio_path:
                # Convert to URL path
                relative_path = Path(audio_path).relative_to(project_root)
                audio_map[slide_num] = f"/static/{relative_path}"
            else:
                errors.append(f"Slide {slide_num}: No audio generated")
                
        except Exception as e:
            errors.append(f"Slide {slide_num}: {str(e)}")
    
    # Create ZIP of all audio files
    zip_path = audio_dir / f"audio_project_{project_id}.zip"
    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
        for wav_file in audio_dir.glob("*.wav"):
            zf.write(wav_file, wav_file.name)
    
    zip_relative = zip_path.relative_to(project_root)
    
    print(f"✅ Voice generation complete: {len(audio_map)}/{len(narrations)} slides")
    
    return {
        "audio_urls": audio_map,
        "zip_url": f"/static/{zip_relative}",
        "project_id": project_id,
        "success": len(errors) == 0,
        "errors": errors,
        "total_slides": len(narrations),
        "generated_slides": len(audio_map)
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
