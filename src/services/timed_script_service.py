"""
Timed Script Service - Generate sentence-level timestamps from audio.

Uses OpenAI Whisper to transcribe audio and extract timestamps.
Designed for use with TTS-generated audio from the voice_service.
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Model configuration
# 'tiny' is fastest and accurate enough for clean TTS audio
# Options: tiny (75MB), base (145MB), small (485MB), medium (1.5GB), large (2.9GB)
MODEL_SIZE = "base"

# Global model instance (lazy loaded)
_whisper_model = None


def get_whisper_model():
    """
    Get or load the Whisper model (singleton pattern).
    Model is loaded once and reused for all transcriptions.
    """
    global _whisper_model

    if _whisper_model is None:
        # Imported lazily so modules that only enqueue work (API, Celery task
        # dispatch) can import this service without the heavy whisper-worker dep.
        import whisper

        logger.info(f"Loading Whisper '{MODEL_SIZE}' model...")
        _whisper_model = whisper.load_model(MODEL_SIZE)
        logger.info(f"✅ Whisper model loaded")
    
    return _whisper_model


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to MM:SS format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string (e.g., "01:23")
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def generate_timed_script(
    audio_path: str | Path,
    language: Optional[str] = None
) -> dict:
    """
    Generate a timed script from an audio file.
    
    Transcribes the audio and returns sentence-level timestamps.
    
    Args:
        audio_path: Path to the audio file (WAV, MP3, etc.)
        language: Language code (default: None for auto-detect)
        
    Returns:
        {
            "success": True/False,
            "audio_file": "path/to/audio.wav",
            "total_duration": "04:05",
            "total_duration_seconds": 245.0,
            "total_sentences": 59,
            "sentences": [
                {
                    "sentence_number": 1,
                    "text": "Welcome to this tutorial...",
                    "time_range": "00:00 - 00:07",
                    "start_seconds": 0.0,
                    "end_seconds": 7.0
                },
                ...
            ],
            "error": None  # or error message if failed
        }
    """
    audio_path = Path(audio_path)
    
    # Validate file exists
    if not audio_path.exists():
        logger.error(f"Audio file not found: {audio_path}")
        return {
            "success": False,
            "audio_file": str(audio_path),
            "error": f"Audio file not found: {audio_path}"
        }
    
    try:
        # Load model
        model = get_whisper_model()
        
        # Transcribe (language=None for auto-detect)
        # word_timestamps=True gives us timestamps for every individual word
        logger.info(f"Transcribing: {audio_path} (language: {'auto' if language is None else language})")
        result = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            verbose=False
        )
        
        # Extract sentences with precision word groupings
        sentences = []
        current_sentence_words = []
        sentence_count = 1
        
        # Punctuation marks that indicate the end of a sentence
        sentence_enders = {'.', '!', '?', '।'} # Added Hindi sentence ender too
        
        for segment in result["segments"]:
            if "words" not in segment:
                # Fallback if word timestamps failed for some reason
                start = segment["start"]
                end = segment["end"]
                sentences.append({
                    "sentence_number": sentence_count,
                    "text": segment["text"].strip(),
                    "time_range": f"{format_timestamp(start)} - {format_timestamp(end)}",
                    "start_seconds": round(start, 2),
                    "end_seconds": round(end, 2),
                })
                sentence_count += 1
                continue
                
            for word_info in segment["words"]:
                word_text = word_info["word"]
                current_sentence_words.append(word_info)
                
                # Check if the word ends with a sentence-ending punctuation
                # We strip spaces but keep internal punctuation
                clean_word = word_text.strip()
                if any(clean_word.endswith(ender) for ender in sentence_enders):
                    # End of sentence detected!
                    start_time = current_sentence_words[0]["start"]
                    end_time = current_sentence_words[-1]["end"]
                    
                    full_text = "".join([w["word"] for w in current_sentence_words]).strip()
                    
                    sentences.append({
                        "sentence_number": sentence_count,
                        "text": full_text,
                        "time_range": f"{format_timestamp(start_time)} - {format_timestamp(end_time)}",
                        "start_seconds": round(start_time, 2),
                        "end_seconds": round(end_time, 2),
                    })
                    
                    sentence_count += 1
                    current_sentence_words = []
        
        # Handle any trailing words that didn't end with punctuation
        if current_sentence_words:
            start_time = current_sentence_words[0]["start"]
            end_time = current_sentence_words[-1]["end"]
            full_text = "".join([w["word"] for w in current_sentence_words]).strip()
            
            sentences.append({
                "sentence_number": sentence_count,
                "text": full_text,
                "time_range": f"{format_timestamp(start_time)} - {format_timestamp(end_time)}",
                "start_seconds": round(start_time, 2),
                "end_seconds": round(end_time, 2),
            })

        # Calculate total duration
        total_duration = result["segments"][-1]["end"] if result["segments"] else 0
        
        logger.info(f"✅ Generated Precision Timed Script: {len(sentences)} sentences, {format_timestamp(total_duration)}")
        
        return {
            "success": True,
            "audio_file": str(audio_path),
            "total_duration": format_timestamp(total_duration),
            "total_duration_seconds": round(total_duration, 2),
            "total_sentences": len(sentences),
            "sentences": sentences,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error generating timed script: {e}")
        return {
            "success": False,
            "audio_file": str(audio_path),
            "error": str(e)
        }


def generate_timed_script_for_slides(
    audio_dir: str | Path,
    slide_pattern: str = "slide_*.wav"
) -> dict:
    """
    Generate timed scripts for all slide audio files in a directory.
    
    Args:
        audio_dir: Directory containing slide audio files
        slide_pattern: Glob pattern for audio files (default: "slide_*.wav")
        
    Returns:
        {
            "success": True/False,
            "audio_dir": "path/to/audio/",
            "total_slides": 15,
            "slides": [
                {
                    "slide_number": 1,
                    "audio_file": "slide_1.wav",
                    "sentences": [...],
                    "total_duration": "00:45"
                },
                ...
            ],
            "errors": []
        }
    """
    audio_dir = Path(audio_dir)
    
    if not audio_dir.exists():
        return {
            "success": False,
            "audio_dir": str(audio_dir),
            "error": f"Directory not found: {audio_dir}"
        }
    
    # Find all audio files
    audio_files = sorted(audio_dir.glob(slide_pattern))
    
    if not audio_files:
        return {
            "success": False,
            "audio_dir": str(audio_dir),
            "error": f"No audio files matching '{slide_pattern}' found"
        }
    
    slides = []
    errors = []
    
    for audio_file in audio_files:
        # Extract slide number from filename (e.g., "slide_1.wav" -> 1)
        try:
            slide_num = int(audio_file.stem.split("_")[1])
        except (IndexError, ValueError):
            slide_num = len(slides) + 1
        
        result = generate_timed_script(audio_file)
        
        if result["success"]:
            slides.append({
                "slide_number": slide_num,
                "audio_file": audio_file.name,
                "sentences": result["sentences"],
                "total_duration": result["total_duration"],
                "total_duration_seconds": result["total_duration_seconds"]
            })
        else:
            errors.append({
                "slide_number": slide_num,
                "audio_file": audio_file.name,
                "error": result.get("error", "Unknown error")
            })
    
    # Sort by slide number
    slides.sort(key=lambda x: x["slide_number"])
    
    return {
        "success": len(errors) == 0,
        "audio_dir": str(audio_dir),
        "total_slides": len(slides),
        "slides": slides,
        "errors": errors
    }
