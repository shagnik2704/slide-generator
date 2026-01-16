"""
Audio utility functions.
"""
import wave
from typing import Tuple


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def get_wav_duration(wav_path: str) -> Tuple[float, str]:
    """
    Get the actual duration of a WAV file.
    
    Args:
        wav_path: Path to the WAV file
        
    Returns:
        Tuple of (duration_seconds, formatted_string)
        e.g., (222.5, "3:42")
    """
    try:
        with wave.open(wav_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration_seconds = frames / float(rate)
            
            # Format as MM:SS
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            formatted = f"{minutes}:{seconds:02d}"
            
            return duration_seconds, formatted
    except Exception as e:
        print(f"⚠️ Could not read WAV duration: {e}")
        return 0.0, "0:00"