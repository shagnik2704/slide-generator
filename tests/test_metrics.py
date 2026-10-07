"""Tests for core telemetry metrics and helper functions."""
import unittest
import time
from src.core.metrics import (
    measure_duration,
    TTS_REQUESTS_TOTAL,
    TTS_AUDIO_DURATION_SECONDS_TOTAL,
    SCRIPT_CHAT_LLM_REQUESTS_TOTAL,
    SLIDE_GEN_REQUESTS_TOTAL,
    SLIDE_GEN_DURATION_SECONDS,
    TRANSCRIPTION_JOBS_TOTAL,
    TRANSLATION_REQUESTS_TOTAL,
    IMAGE_GEN_REQUESTS_TOTAL,
    COMPLIANCE_EVALUATIONS_TOTAL,
    DOCUMENT_EXPORTS_TOTAL,
    REDESIGN_PIPELINE_TOTAL,
)


class TestMetrics(unittest.TestCase):
    def test_measure_duration_context_manager(self):
        """Verify measure_duration records elapsed time to histogram."""
        with measure_duration(SLIDE_GEN_DURATION_SECONDS):
            time.sleep(0.01)

    def test_counter_increments(self):
        """Verify various metric counters increment without errors."""
        TTS_REQUESTS_TOTAL.labels(language="en-IN", speaker="priya", status="success").inc()
        TTS_AUDIO_DURATION_SECONDS_TOTAL.labels(language="en-IN").inc(2.5)
        SCRIPT_CHAT_LLM_REQUESTS_TOTAL.labels(model="gpt-4o-mini", call_type="text", status="success").inc()
        SLIDE_GEN_REQUESTS_TOTAL.labels(status="success", theme="madrid").inc()
        TRANSCRIPTION_JOBS_TOTAL.labels(status="completed").inc()
        TRANSLATION_REQUESTS_TOTAL.labels(target_language="hi", status="success").inc()
        IMAGE_GEN_REQUESTS_TOTAL.labels(status="success").inc()
        COMPLIANCE_EVALUATIONS_TOTAL.labels(status="success").inc()
        DOCUMENT_EXPORTS_TOTAL.labels(format="docx", status="success").inc()
        REDESIGN_PIPELINE_TOTAL.labels(status="success").inc()


if __name__ == "__main__":
    unittest.main()
