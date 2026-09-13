"""Configuration settings for Spoken Tutorial FAQ RAG module."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FaqSettings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    sarvam_stt_model: str = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
    sarvam_stt_language: str = os.getenv("SARVAM_STT_LANGUAGE", "en-IN")
    sarvam_tts_model: str = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
    sarvam_tts_speaker: str = os.getenv("SARVAM_TTS_SPEAKER", "shubh")
    sarvam_tts_language: str = os.getenv("SARVAM_TTS_LANGUAGE", "en-IN")
    sarvam_tts_codec: str = os.getenv("SARVAM_TTS_CODEC", "mp3")
    sarvam_tts_pace: float = float(os.getenv("SARVAM_TTS_PACE", "0.85"))
    sarvam_tts_temperature: float = float(os.getenv("SARVAM_TTS_TEMPERATURE", "0.4"))

    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    keyword_weight: float = float(os.getenv("KEYWORD_WEIGHT", "0.35"))

    similarity_high: float = float(os.getenv("SIMILARITY_HIGH", "0.82"))
    similarity_low: float = float(os.getenv("SIMILARITY_LOW", "0.65"))
    similarity_min_absolute: float = float(os.getenv("SIMILARITY_MIN_ABSOLUTE", "0.50"))
    similarity_margin: float = float(os.getenv("SIMILARITY_MARGIN", "0.18"))

    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))

    faqs_path: Path = Path(__file__).resolve().parents[2] / "data" / "spoken_tutorial_faqs.json"


def get_faq_settings() -> FaqSettings:
    """Return an active settings instance, picking up any updated env vars."""
    return FaqSettings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        sarvam_api_key=os.getenv("SARVAM_API_KEY", ""),
    )


settings = get_faq_settings()
