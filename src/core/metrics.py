"""Central Prometheus metrics definitions and telemetry helpers for core features.

Defines RED metrics (Rate, Errors, Duration) and dependency health metrics
across all application services:
  1. TTS / Voice Synthesis (Sarvam AI Bulbul v3)
  2. Script Chat (LangGraph + OpenAI)
  3. Slide Generation (LaTeX / Beamer / Content Extraction)
  4. Timed Script / Audio Transcription (Celery + Whisper)
  5. Translation & Slides Translation (Gemini + XeLaTeX)
  6. Image Generation (Gemini Pro Image Preview)
  7. Compliance & Quality Verification
  8. Document Exporters & MediaWiki
  9. Curriculum Redesign Pipeline
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from prometheus_client import Counter, Histogram

# ==============================================================================
# 1. TTS / VOICE SYNTHESIS METRICS
# ==============================================================================

TTS_REQUESTS_TOTAL = Counter(
    "tts_requests_total",
    "Total user requests for TTS voice narration",
    ["language", "speaker", "status"],
)

TTS_UPSTREAM_REQUESTS_TOTAL = Counter(
    "tts_upstream_requests_total",
    "HTTP requests dispatched to upstream TTS provider",
    ["provider", "http_status"],
)

TTS_UPSTREAM_DURATION_SECONDS = Histogram(
    "tts_upstream_duration_seconds",
    "Latency of upstream TTS chunk synthesis requests",
    ["provider", "language"],
    buckets=(0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0),
)

TTS_RETRIES_TOTAL = Counter(
    "tts_retries_total",
    "Retry attempts encountered during TTS generation",
    ["reason"],
)

TTS_AUDIO_DURATION_SECONDS_TOTAL = Counter(
    "tts_audio_duration_seconds_total",
    "Total duration of audio generated in seconds",
    ["language"],
)

TTS_CHARACTERS_TOTAL = Counter(
    "tts_characters_total",
    "Total text characters sent to TTS engine",
    ["language"],
)

# ==============================================================================
# 2. SCRIPT CHAT (LANGGRAPH + LLM) METRICS
# ==============================================================================

SCRIPT_CHAT_STAGE_TOTAL = Counter(
    "script_chat_stage_total",
    "Transitions through Script Chat agent workflow stages",
    ["stage", "status"],
)

SCRIPT_CHAT_STAGE_DURATION_SECONDS = Histogram(
    "script_chat_stage_duration_seconds",
    "Duration of individual Script Chat workflow stages",
    ["stage"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0),
)

SCRIPT_CHAT_LLM_REQUESTS_TOTAL = Counter(
    "script_chat_llm_requests_total",
    "LLM API requests executed during Script Chat",
    ["model", "call_type", "status"],
)

SCRIPT_CHAT_LLM_DURATION_SECONDS = Histogram(
    "script_chat_llm_duration_seconds",
    "Latency of Script Chat LLM invocations",
    ["model", "call_type"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0, 90.0),
)

SCRIPT_CHAT_LLM_TOKENS_TOTAL = Counter(
    "script_chat_llm_tokens_total",
    "Estimated or reported token usage in Script Chat",
    ["model", "token_type"],
)

# ==============================================================================
# 3. SLIDE GENERATION (LATEX / BEAMER / CONTENT EXTRACTION) METRICS
# ==============================================================================

SLIDE_GEN_REQUESTS_TOTAL = Counter(
    "slide_generation_requests_total",
    "Total slide generation requests processed",
    ["status", "theme"],
)

SLIDE_GEN_DURATION_SECONDS = Histogram(
    "slide_generation_duration_seconds",
    "End-to-end duration of slide generation requests",
    buckets=(1.0, 2.5, 5.0, 10.0, 20.0, 45.0, 90.0, 180.0),
)

SLIDE_EXTRACTION_DURATION_SECONDS = Histogram(
    "slide_extraction_duration_seconds",
    "Duration of slide content extraction from scripts",
    ["provider"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0),
)

SLIDE_EXTRACTION_FALLBACK_TOTAL = Counter(
    "slide_extraction_fallback_total",
    "Fallback events triggered during slide content extraction",
    ["from_provider", "to_provider"],
)

LATEX_COMPILATION_ERRORS_TOTAL = Counter(
    "latex_compilation_errors_total",
    "LaTeX engine compilation errors",
    ["engine", "error_type"],
)

# ==============================================================================
# 4. TIMED SCRIPT / WHISPER TRANSCRIPTION METRICS
# ==============================================================================

TRANSCRIPTION_JOBS_TOTAL = Counter(
    "transcription_jobs_total",
    "Timed script audio transcription jobs",
    ["status"],
)

TRANSCRIPTION_DURATION_SECONDS = Histogram(
    "transcription_duration_seconds",
    "Duration of audio transcription processing in workers",
    buckets=(5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

TRANSCRIPTION_AUDIO_SECONDS_TOTAL = Counter(
    "transcription_audio_seconds_total",
    "Total audio duration transcribed in seconds",
)

# ==============================================================================
# 5. TRANSLATION & SLIDES TRANSLATION METRICS
# ==============================================================================

TRANSLATION_REQUESTS_TOTAL = Counter(
    "translation_requests_total",
    "Batch script translation requests",
    ["target_language", "status"],
)

TRANSLATION_DURATION_SECONDS = Histogram(
    "translation_duration_seconds",
    "Duration of batch script translations",
    ["target_language"],
    buckets=(1.0, 2.5, 5.0, 10.0, 25.0, 60.0),
)

SLIDES_TRANSLATION_REQUESTS_TOTAL = Counter(
    "slides_translation_requests_total",
    "Beamer .tex slide translation requests",
    ["target_language", "status"],
)

SLIDES_TRANSLATION_DURATION_SECONDS = Histogram(
    "slides_translation_duration_seconds",
    "Duration of Beamer .tex slide translations",
    ["target_language"],
    buckets=(2.0, 5.0, 10.0, 25.0, 60.0, 120.0),
)

# ==============================================================================
# 6. IMAGE GENERATION METRICS
# ==============================================================================

IMAGE_GEN_REQUESTS_TOTAL = Counter(
    "image_generation_requests_total",
    "Image generation requests",
    ["status"],
)

IMAGE_GEN_DURATION_SECONDS = Histogram(
    "image_generation_duration_seconds",
    "Latency of image generation from prompts",
    buckets=(1.0, 2.5, 5.0, 10.0, 20.0, 45.0),
)

IMAGE_GEN_QUOTA_ERRORS_TOTAL = Counter(
    "image_generation_quota_errors_total",
    "Image generation rate limit or quota errors",
)

# ==============================================================================
# 7. COMPLIANCE & QUALITY EVALUATION METRICS
# ==============================================================================

COMPLIANCE_EVALUATIONS_TOTAL = Counter(
    "compliance_evaluations_total",
    "Compliance checklist evaluations",
    ["status"],
)

COMPLIANCE_DURATION_SECONDS = Histogram(
    "compliance_duration_seconds",
    "Duration of compliance checklist evaluations",
    buckets=(1.0, 2.5, 5.0, 10.0, 20.0, 45.0),
)

QUALITY_EVALUATIONS_TOTAL = Counter(
    "quality_evaluations_total",
    "Quality back-translation evaluations",
    ["status"],
)

# ==============================================================================
# 8. DOCUMENT EXPORTERS & MEDIAWIKI METRICS
# ==============================================================================

DOCUMENT_EXPORTS_TOTAL = Counter(
    "document_exports_total",
    "Document export requests",
    ["format", "status"],
)

DOCUMENT_EXPORT_DURATION_SECONDS = Histogram(
    "document_export_duration_seconds",
    "Duration of document exports",
    ["format"],
    buckets=(0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ==============================================================================
# 9. CURRICULUM REDESIGN PIPELINE METRICS
# ==============================================================================

REDESIGN_PIPELINE_TOTAL = Counter(
    "redesign_pipeline_total",
    "Curriculum redesign pipeline executions",
    ["status"],
)

REDESIGN_PIPELINE_DURATION_SECONDS = Histogram(
    "redesign_pipeline_duration_seconds",
    "End-to-end duration of curriculum redesign pipeline runs",
    buckets=(5.0, 15.0, 30.0, 60.0, 120.0, 300.0),
)


# ==============================================================================
# CONVENIENCE CONTEXT MANAGERS & HELPERS
# ==============================================================================

@contextmanager
def measure_duration(histogram: Histogram, **labels):
    """Context manager to measure execution time of a code block in seconds."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if labels:
            histogram.labels(**labels).observe(elapsed)
        else:
            histogram.observe(elapsed)
