"""
Audio utility functions.
"""
import io
import wave
from typing import List, Tuple


def concat_wav_bytes(chunks: List[bytes]) -> bytes:
    """
    Join several in-memory WAV files into one.

    Used to stitch TTS output back together when narration is too long for a
    single request. All chunks must share the same format, which holds when
    they come from the same TTS call parameters.

    Args:
        chunks: Raw WAV file bytes, in playback order

    Returns:
        A single WAV file as bytes
    """
    if not chunks:
        raise ValueError("No audio chunks to concatenate")
    if len(chunks) == 1:
        return chunks[0]

    params = None
    frames = []

    for i, blob in enumerate(chunks):
        with wave.open(io.BytesIO(blob), "rb") as wf:
            current = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
            if params is None:
                params = current
            elif current != params:
                raise ValueError(
                    f"Audio chunk {i} format {current} does not match {params}"
                )
            frames.append(wf.readframes(wf.getnframes()))

    channels, sample_width, framerate = params
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(framerate)
        wf.writeframes(b"".join(frames))

    return out.getvalue()


def silence_wav_like(reference: bytes, seconds: float) -> bytes:
    """
    Build a silent WAV matching another WAV's format.

    Used to place a deliberate pause between stitched segments, so the gap is
    concatenable with the audio around it.

    Args:
        reference: A WAV file whose channel/width/rate should be matched
        seconds: Length of the silence

    Returns:
        A silent WAV file as bytes
    """
    with wave.open(io.BytesIO(reference), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()

    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(framerate)
        wf.writeframes(b"\x00" * int(framerate * seconds) * channels * sample_width)

    return out.getvalue()


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