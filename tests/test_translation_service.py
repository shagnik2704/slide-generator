"""Unit tests for the Sarvam-backed script translation service."""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.services.translation_service import (
    SUPPORTED_LANGUAGES,
    SARVAM_TRANSLATE_LANG_MAP,
    resolve_language_info,
    _split_text_into_chunks,
    _translate_chunk_sarvam,
    _translate_text_sarvam,
    translate_script,
    batch_translate,
    get_supported_languages,
    TranslationResult,
)


class TranslationServiceTests(unittest.IsolatedAsyncioTestCase):

    def test_supported_languages_and_mapping(self):
        """All 11 Spoken Tutorial languages must be present and mapped in Sarvam."""
        self.assertEqual(len(SUPPORTED_LANGUAGES), 11)
        expected_languages = {"hi", "ta", "te", "mr", "bn", "kn", "gu", "ml", "pa", "or", "as"}
        self.assertEqual(set(SUPPORTED_LANGUAGES.keys()), expected_languages)

        # Check Sarvam mapping
        for code in expected_languages:
            self.assertIn(code, SARVAM_TRANSLATE_LANG_MAP)
        self.assertEqual(SARVAM_TRANSLATE_LANG_MAP["or"], "od-IN")
        self.assertEqual(SARVAM_TRANSLATE_LANG_MAP["as"], "as-IN")
        self.assertEqual(get_supported_languages(), SUPPORTED_LANGUAGES)

    def test_resolve_language_info(self):
        """Language resolver should handle 2-letter codes, BCP-47 codes, and Odia variants."""
        hi_info = resolve_language_info("hi")
        self.assertIsNotNone(hi_info)
        self.assertEqual(hi_info, ("hi", "Hindi", "हिंदी", "hi-IN"))

        hi_in_info = resolve_language_info("hi-IN")
        self.assertEqual(hi_in_info, ("hi", "Hindi", "हिंदी", "hi-IN"))

        or_info = resolve_language_info("or")
        self.assertEqual(or_info, ("or", "Odia", "ଓଡ଼ିଆ", "od-IN"))

        od_info = resolve_language_info("od")
        self.assertEqual(od_info, ("or", "Odia", "ଓଡ଼ିଆ", "od-IN"))

        as_info = resolve_language_info("as")
        self.assertEqual(as_info, ("as", "Assamese", "অসমীয়া", "as-IN"))

        # English language names & case-insensitivity
        self.assertEqual(resolve_language_info("Hindi"), ("hi", "Hindi", "हिंदी", "hi-IN"))
        self.assertEqual(resolve_language_info("hindi"), ("hi", "Hindi", "हिंदी", "hi-IN"))
        self.assertEqual(resolve_language_info("Tamil"), ("ta", "Tamil", "தமிழ்", "ta-IN"))
        self.assertEqual(resolve_language_info("Telugu"), ("te", "Telugu", "తెలుగు", "te-IN"))
        self.assertEqual(resolve_language_info("Assamese"), ("as", "Assamese", "অসমীয়া", "as-IN"))
        self.assertEqual(resolve_language_info("Odia"), ("or", "Odia", "ଓଡ଼ିଆ", "od-IN"))
        self.assertEqual(resolve_language_info("oriya"), ("or", "Odia", "ଓଡ଼ିଆ", "od-IN"))

        # Native script
        self.assertEqual(resolve_language_info("हिंदी"), ("hi", "Hindi", "हिंदी", "hi-IN"))
        self.assertEqual(resolve_language_info("தமிழ்"), ("ta", "Tamil", "தமிழ்", "ta-IN"))

        # Punctuation/quotes/brackets wrapped
        self.assertEqual(resolve_language_info('"hi"'), ("hi", "Hindi", "हिंदी", "hi-IN"))
        self.assertEqual(resolve_language_info('["hi"]'), ("hi", "Hindi", "हिंदी", "hi-IN"))

        # Invalid
        self.assertIsNone(resolve_language_info("unsupported_lang"))
        self.assertIsNone(resolve_language_info(""))
        self.assertIsNone(resolve_language_info(None))

    def test_split_text_into_chunks(self):
        """Text splitting should preserve sentences and obey chunk limits."""
        self.assertEqual(_split_text_into_chunks(""), [])
        self.assertEqual(_split_text_into_chunks("   "), [])

        short_text = "Welcome to Python tutorial."
        self.assertEqual(_split_text_into_chunks(short_text), [short_text])

        # Multi-sentence under limit
        two_sentences = "First sentence. Second sentence!"
        self.assertEqual(_split_text_into_chunks(two_sentences, max_len=50), [two_sentences])

        # Multi-sentence exceeding limit
        chunks = _split_text_into_chunks(two_sentences, max_len=20)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], "First sentence.")
        self.assertEqual(chunks[1], "Second sentence!")

    @patch("src.services.translation_service.httpx.AsyncClient.post")
    async def test_translate_chunk_sarvam_success(self, mock_post):
        """A single chunk translates successfully with Sarvam."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"translated_text": "पायथन ट्यूटोरियल में आपका स्वागत है।"}
        mock_post.return_value = mock_response

        async with httpx.AsyncClient() as client:
            res = await _translate_chunk_sarvam(
                client=client,
                text="Welcome to Python tutorial.",
                target_code="hi-IN",
                api_key="test-sarvam-key",
                model="sarvam-translate:v1",
            )
            self.assertEqual(res, "पायथन ट्यूटोरियल में आपका स्वागत है।")

    @patch("src.services.translation_service.httpx.AsyncClient.post")
    async def test_translate_chunk_sarvam_400_raises_without_retry(self, mock_post):
        """A 400 Bad Request raises immediately without retrying."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid language code"}
        mock_post.return_value = mock_response

        async with httpx.AsyncClient() as client:
            with self.assertRaises(RuntimeError) as ctx:
                await _translate_chunk_sarvam(
                    client=client,
                    text="Hello",
                    target_code="invalid-code",
                    api_key="test-key",
                )
            self.assertIn("Invalid language code", str(ctx.exception))
            self.assertEqual(mock_post.call_count, 1)

    @patch("src.services.translation_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.services.translation_service.httpx.AsyncClient.post")
    async def test_translate_chunk_sarvam_retries_transient_error(self, mock_post, mock_sleep):
        """Transient error (500) retries and succeeds on subsequent attempt."""
        err_response = MagicMock()
        err_response.status_code = 500

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"translated_text": "सफल अनुवाद"}

        mock_post.side_effect = [err_response, ok_response]

        async with httpx.AsyncClient() as client:
            res = await _translate_chunk_sarvam(
                client=client,
                text="Hello world",
                target_code="hi-IN",
                api_key="test-key",
            )
            self.assertEqual(res, "सफल अनुवाद")
            self.assertEqual(mock_post.call_count, 2)
            mock_sleep.assert_awaited_once()

    @patch("src.services.translation_service._translate_text_sarvam", new_callable=AsyncMock)
    async def test_translate_script_sarvam_full_script(self, mock_translate_text):
        """translate_script translates all slides in parallel with Sarvam."""
        mock_translate_text.side_effect = lambda client, text, target_code, api_key, **kwargs: (
            f"[{target_code}] {text}"
        )

        test_script = {
            "presentation_title": "Python Basics",
            "slides": [
                {
                    "slide_number": 1,
                    "title": "Introduction",
                    "narration": "Welcome to Python.",
                    "visual_cue": "Show title slide"
                },
                {
                    "slide_number": 2,
                    "title": "Variables",
                    "narration": "A variable stores data.",
                    "visual_cue": "Show variable diagram"
                }
            ]
        }

        with patch.dict("os.environ", {"SARVAM_API_KEY": "valid-sarvam-key", "TRANSLATION_PROVIDER": "sarvam"}):
            res = await translate_script(test_script, "hi", translate_visual_cues=True)

        self.assertTrue(res.success)
        self.assertEqual(res.language, "Hindi")
        self.assertEqual(res.language_code, "hi")
        self.assertEqual(res.language_native, "हिंदी")

        slides = res.translated_script["slides"]
        self.assertEqual(len(slides), 2)
        self.assertEqual(slides[0]["narration_hi"], "[hi-IN] Welcome to Python.")
        self.assertEqual(slides[0]["visual_cue_hi"], "[hi-IN] Show title slide")
        self.assertEqual(slides[1]["narration_hi"], "[hi-IN] A variable stores data.")
        self.assertEqual(slides[1]["visual_cue_hi"], "[hi-IN] Show variable diagram")

        # Original fields remain intact
        self.assertEqual(slides[0]["narration"], "Welcome to Python.")
        self.assertEqual(res.translated_script["presentation_title"], "Python Basics")

    @patch("src.services.translation_service._translate_text_sarvam", new_callable=AsyncMock)
    async def test_translate_script_without_visual_cues(self, mock_translate_text):
        """translate_script obeys translate_visual_cues=False."""
        mock_translate_text.side_effect = lambda client, text, target_code, api_key, **kwargs: f"Trans: {text}"

        test_script = {
            "slides": [
                {"slide_number": 1, "narration": "Hello", "visual_cue": "Cue 1"}
            ]
        }

        with patch.dict("os.environ", {"SARVAM_API_KEY": "valid-sarvam-key"}):
            res = await translate_script(test_script, "ta", translate_visual_cues=False)

        self.assertTrue(res.success)
        self.assertEqual(res.language_code, "ta")
        slide = res.translated_script["slides"][0]
        self.assertEqual(slide["narration_ta"], "Trans: Hello")
        self.assertNotIn("visual_cue_ta", slide)

    async def test_translate_script_unsupported_language(self):
        """translate_script handles invalid language code gracefully."""
        test_script = {"slides": [{"slide_number": 1, "narration": "Hello"}]}
        res = await translate_script(test_script, "klingon")
        self.assertFalse(res.success)
        self.assertIn("Unsupported language", res.error)

    async def test_translate_script_no_slides(self):
        """translate_script returns error when slides array is empty."""
        test_script = {"slides": []}
        res = await translate_script(test_script, "hi")
        self.assertFalse(res.success)
        self.assertIn("No slides found", res.error)

    @patch("src.services.translation_service._translate_script_gemini", new_callable=AsyncMock)
    @patch("src.services.translation_service._translate_script_sarvam", new_callable=AsyncMock)
    async def test_translate_script_fallback_to_gemini_on_sarvam_failure(
        self, mock_sarvam, mock_gemini
    ):
        """When Sarvam fails, translate_script falls back to Gemini if GEMINI_API_KEY is present."""
        mock_sarvam.side_effect = RuntimeError("Sarvam 503 Service Unavailable")
        mock_gemini.return_value = {
            "slides": [{"slide_number": 1, "narration": "Hello", "narration_hi": "नमस्ते"}],
            "target_language": "hi",
            "target_language_name": "Hindi",
            "target_language_native": "हिंदी"
        }

        with patch.dict("os.environ", {
            "SARVAM_API_KEY": "valid-key",
            "GEMINI_API_KEY": "gemini-key",
            "TRANSLATION_PROVIDER": "sarvam"
        }):
            res = await translate_script({"slides": [{"slide_number": 1, "narration": "Hello"}]}, "hi")

        self.assertTrue(res.success)
        mock_sarvam.assert_awaited_once()
        mock_gemini.assert_awaited_once()
        self.assertEqual(res.translated_script["slides"][0]["narration_hi"], "नमस्ते")

    @patch("src.services.translation_service._translate_script_gemini", new_callable=AsyncMock)
    async def test_translate_script_uses_gemini_when_sarvam_key_absent(self, mock_gemini):
        """When SARVAM_API_KEY is absent, fallback to Gemini directly."""
        mock_gemini.return_value = {
            "slides": [{"slide_number": 1, "narration": "Hello", "narration_te": "హలో"}],
            "target_language": "te",
            "target_language_name": "Telugu",
            "target_language_native": "తెలుగు"
        }

        with patch.dict("os.environ", {"SARVAM_API_KEY": ""}, clear=False):
            res = await translate_script({"slides": [{"slide_number": 1, "narration": "Hello"}]}, "te")

        self.assertTrue(res.success)
        self.assertEqual(res.language_code, "te")
        mock_gemini.assert_awaited_once()

    @patch("src.services.translation_service.translate_script", new_callable=AsyncMock)
    async def test_batch_translate_multiple_languages(self, mock_translate):
        """batch_translate executes parallel translation across requested languages."""
        async def fake_translate(script, lang, translate_visual_cues=True, **kwargs):
            return TranslationResult(
                language="Lang",
                language_code=lang,
                language_native="Native",
                translated_script={"slides": []},
                success=True
            )
        mock_translate.side_effect = fake_translate

        test_script = {"slides": [{"slide_number": 1, "narration": "Hello"}]}
        results = await batch_translate(test_script, ["hi", "ta", "mr"])

        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.success for r in results))
        self.assertEqual([r.language_code for r in results], ["hi", "ta", "mr"])

    async def test_batch_translate_no_valid_languages(self):
        """batch_translate returns single failure when all languages are invalid."""
        test_script = {"slides": [{"slide_number": 1, "narration": "Hello"}]}
        results = await batch_translate(test_script, ["unknown1", "unknown2"])

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIn("No valid languages", results[0].error)


if __name__ == "__main__":
    unittest.main()
