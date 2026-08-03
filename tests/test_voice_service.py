import base64
import io
import shutil
import unittest
import wave
from pathlib import Path
from unittest import mock

import httpx

from src.services.voice_service import (
    CONTINUOUS,
    PER_SLIDE,
    TTS_CHAR_LIMIT,
    UnsplittableTextError,
    UnsupportedLanguageError,
    clean_text_for_tts,
    generate_voice_combined,
    generate_voice_for_script,
    resolve_language_code,
    split_text_for_tts,
)
from src.utils.audio_utils import concat_wav_bytes, get_wav_duration, silence_wav_like


SENTENCE = "Now we will open the terminal and run the command to install the package. "

# A 3-4 minute tutorial runs past the 2500-char per-request limit, which is
# exactly the case the old code silently truncated.
LONG_NARRATION = (SENTENCE * 12).strip()

RATE = 48000

# Where voice_service writes generated audio, so tests can clean up after
# themselves without reaching into the service's internals.
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"
AUDIO_ROOT = OUTPUT_ROOT / "audio"


def make_wav(seconds: float, rate: int = RATE) -> bytes:
    """A silent WAV of a given duration, for stitching assertions."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x01" * int(rate * seconds))
    return buf.getvalue()


class StubSarvamClient:
    """Stands in for httpx.AsyncClient, recording every TTS request."""

    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        StubSarvamClient.calls.append(json)
        # Duration proportional to text length, so stitched audio is checkable.
        audio = make_wav(len(json["text"]) / 1000)
        return httpx.Response(
            200,
            json={"audios": [base64.b64encode(audio).decode()]},
            request=httpx.Request("POST", url),
        )


class SplitTextForTTSTests(unittest.TestCase):
    def test_short_text_is_untouched(self):
        self.assertEqual(split_text_for_tts("A short line."), ["A short line."])

    def test_blank_text_yields_no_chunks(self):
        self.assertEqual(split_text_for_tts(""), [])
        self.assertEqual(split_text_for_tts("  \n "), [])

    def test_long_text_splits_without_losing_content(self):
        text = SENTENCE * 60
        chunks = split_text_for_tts(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= TTS_CHAR_LIMIT for c in chunks))
        # Seams consume the separating whitespace, so compare without it.
        self.assertEqual(
            "".join(c.replace(" ", "") for c in chunks),
            text.replace(" ", ""),
        )

    def test_splits_on_devanagari_danda(self):
        text = "यह एक हिंदी वाक्य है। हम इसे दोहराते हैं। " * 80
        chunks = split_text_for_tts(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= TTS_CHAR_LIMIT for c in chunks))
        # Every seam should land on a sentence boundary, not mid-clause.
        self.assertTrue(all(c.rstrip().endswith("।") for c in chunks))

    def test_oversized_sentence_falls_back_to_clauses(self):
        text = ("first clause here, second clause here, " * 90).rstrip(", ") + "."
        chunks = split_text_for_tts(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= TTS_CHAR_LIMIT for c in chunks))

    def test_text_without_punctuation_falls_back_to_words(self):
        chunks = split_text_for_tts("word " * 900)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= TTS_CHAR_LIMIT for c in chunks))

    def test_single_oversized_token_is_refused_not_cut(self):
        # Nothing is ever sliced mid-token: a blind cut would split a word or
        # an identifier in half and read it as gibberish.
        with self.assertRaises(UnsplittableTextError):
            split_text_for_tts("x" * 6000)

    def test_unsplittable_error_names_the_offending_text(self):
        with self.assertRaises(UnsplittableTextError) as ctx:
            split_text_for_tts("abcdef" * 500)

        self.assertIn("3000-character", str(ctx.exception))
        self.assertIn("abcdef", str(ctx.exception))


class CleanTextForTTSTests(unittest.TestCase):
    """Narration names code, so cleaning must not eat identifiers."""

    def test_preserves_python_identifiers(self):
        for text in (
            "Define my_variable and set it to 10",
            "The __init__ method runs first",
            "Use *args and **kwargs in the function",
            "In Python, 2 ** 3 is eight",
            "Write a loop over my_list_of_items",
        ):
            with self.subTest(text=text):
                self.assertEqual(clean_text_for_tts(text), text)

    def test_preserves_shell_and_c_syntax(self):
        for text in (
            "Type #include <stdio.h> at the top",
            "Now add #include <iostream> below it",
            "Run sudo apt-get install python3-pip",
            "Use the ls -l command",
            "Learn C# and F# basics",
            "The value is 2 * 3 * 4",
        ):
            with self.subTest(text=text):
                self.assertEqual(clean_text_for_tts(text), text)

    def test_still_strips_markdown(self):
        self.assertEqual(
            clean_text_for_tts("This is **important** to remember"),
            "This is important to remember",
        )
        self.assertEqual(clean_text_for_tts("# Heading here"), "Heading here")
        self.assertEqual(clean_text_for_tts("- First point"), "First point")
        self.assertEqual(clean_text_for_tts("Call `print()` now"), "Call print() now")

    def test_strips_real_html_tags_only(self):
        self.assertEqual(
            clean_text_for_tts("Wrap it in <p>a paragraph</p> tag"),
            "Wrap it in a paragraph tag",
        )
        # Not HTML — a C header, which must survive.
        self.assertEqual(clean_text_for_tts("<vector> here"), "<vector> here")

    def test_strips_mediawiki_markup(self):
        # The markup Spoken Tutorial scripts actually carry.
        self.assertEqual(
            clean_text_for_tts("Define what '''Cyberspace''' is."),
            "Define what Cyberspace is.",
        )
        self.assertEqual(clean_text_for_tts("He said ''hello'' there"), "He said hello there")
        self.assertEqual(clean_text_for_tts("See [[Main Page]] now"), "See Main Page now")
        self.assertEqual(
            clean_text_for_tts("See [[Main Page|the guide]] now"), "See the guide now"
        )

    def test_handles_a_real_script_narration(self):
        raw = (
            "In this tutorial, you will learn to,\n"
            "• Define what '''Cyberspace''' is.\n"
            "• Identify components of '''Cyberspace'''."
        )
        self.assertEqual(
            clean_text_for_tts(raw),
            "In this tutorial, you will learn to, Define what Cyberspace is. "
            "Identify components of Cyberspace.",
        )

    def test_leaves_ordinary_apostrophes_alone(self):
        self.assertEqual(
            clean_text_for_tts("Don't forget the user's password"),
            "Don't forget the user's password",
        )

    def test_normalizes_whitespace(self):
        self.assertEqual(clean_text_for_tts("one\n\ttwo   three"), "one two three")

    def test_blank_input(self):
        self.assertEqual(clean_text_for_tts(""), "")
        self.assertEqual(clean_text_for_tts("   "), "")


class ResolveLanguageCodeTests(unittest.TestCase):
    def test_maps_two_letter_codes(self):
        self.assertEqual(resolve_language_code("hi"), "hi-IN")
        self.assertEqual(resolve_language_code("HI"), "hi-IN")
        self.assertEqual(resolve_language_code("or"), "od-IN")

    def test_missing_language_means_english(self):
        self.assertEqual(resolve_language_code(None), "en-IN")
        self.assertEqual(resolve_language_code(""), "en-IN")

    def test_passes_through_supported_bcp47(self):
        self.assertEqual(resolve_language_code("ta-IN"), "ta-IN")

    def test_rejects_languages_without_a_voice(self):
        # Assamese is offered by the translation service but Bulbul cannot
        # speak it; it must not fall back to an English voice.
        for code in ("as", "as-IN", "ur", "sa", "fr-FR"):
            with self.subTest(code=code):
                with self.assertRaises(UnsupportedLanguageError):
                    resolve_language_code(code)


class ConcatWavBytesTests(unittest.TestCase):
    def test_durations_add_up(self):
        joined = concat_wav_bytes([make_wav(1.0), make_wav(2.0), make_wav(0.5)])

        with wave.open(io.BytesIO(joined), "rb") as wf:
            self.assertEqual(wf.getframerate(), RATE)
            self.assertEqual(wf.getnchannels(), 1)
            self.assertAlmostEqual(wf.getnframes() / wf.getframerate(), 3.5)

    def test_single_chunk_is_returned_as_is(self):
        only = make_wav(1.0)
        self.assertIs(concat_wav_bytes([only]), only)

    def test_rejects_mismatched_formats(self):
        with self.assertRaises(ValueError):
            concat_wav_bytes([make_wav(1.0, rate=48000), make_wav(1.0, rate=24000)])

    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            concat_wav_bytes([])


class VoiceGenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        StubSarvamClient.calls = []

        for patcher in (
            mock.patch("src.services.voice_service.httpx.AsyncClient", StubSarvamClient),
            mock.patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def project(self, name):
        """A project id whose output directory is removed after the test."""
        project_id = f"test_voice_{name}"
        audio_dir = AUDIO_ROOT / f"project_{project_id}"
        self.addCleanup(shutil.rmtree, audio_dir, True)
        return project_id

    def script(self, narration=LONG_NARRATION, language="en", slides=4):
        return {
            "target_language": language,
            "slides": [
                {"slide_number": i, "narration": narration}
                for i in range(1, slides + 1)
            ],
        }

    async def test_combined_audio_covers_the_whole_script(self):
        script = self.script()
        result = await generate_voice_combined(script, project_id=self.project("combined"))

        self.assertTrue(result["success"], result)
        self.assertGreater(len(StubSarvamClient.calls), 1, "expected chunking")

        sent = "".join(call["text"] for call in StubSarvamClient.calls)
        expected = " ".join(
            slide["narration"].rstrip(".") + "." for slide in script["slides"]
        )
        self.assertGreater(len(expected), TTS_CHAR_LIMIT, "fixture must exceed the limit")
        self.assertEqual(sent.replace(" ", ""), expected.replace(" ", ""))

        # The stitched file must be as long as the full narration, not the
        # first 2500 characters of it.
        wav = OUTPUT_ROOT / result["audio_url"].removeprefix("/output/")
        duration, _ = get_wav_duration(str(wav))
        self.assertAlmostEqual(duration, len(expected) / 1000, delta=0.05)

    async def test_no_chunk_exceeds_the_api_limit(self):
        await generate_voice_combined(
            self.script(slides=12), project_id=self.project("limit")
        )

        self.assertTrue(
            all(len(call["text"]) <= TTS_CHAR_LIMIT for call in StubSarvamClient.calls)
        )

    async def test_long_single_slide_is_chunked_not_truncated(self):
        script = self.script(narration=SENTENCE * 60, slides=1)
        result = await generate_voice_for_script(
            script, project_id=self.project("bigslide")
        )

        self.assertTrue(result["success"], result)
        self.assertGreater(len(StubSarvamClient.calls), 1)

    async def test_per_slide_keeps_a_file_per_slide_and_stitches_them(self):
        script = self.script(slides=4)
        result = await generate_voice_combined(
            script, project_id=self.project("perslide"), source=PER_SLIDE
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(sorted(result["slide_audio_urls"]), [1, 2, 3, 4])

        # Every per-slide file is on disk alongside the stitched narration.
        for url in result["slide_audio_urls"].values():
            self.assertTrue((OUTPUT_ROOT / url.removeprefix("/output/")).exists())

        stitched = OUTPUT_ROOT / result["audio_url"].removeprefix("/output/")
        self.assertTrue(stitched.exists())

    async def test_both_sources_produce_the_same_narration_length(self):
        # Seam placement differs; total content must not.
        durations = {}
        for source in (CONTINUOUS, PER_SLIDE):
            StubSarvamClient.calls = []
            result = await generate_voice_combined(
                self.script(slides=4),
                project_id=self.project(f"parity_{source}"),
                source=source,
            )
            self.assertTrue(result["success"], result)
            wav = OUTPUT_ROOT / result["audio_url"].removeprefix("/output/")
            durations[source] = get_wav_duration(str(wav))[0]

        self.assertAlmostEqual(durations[CONTINUOUS], durations[PER_SLIDE], delta=0.05)

    async def test_per_slide_gap_lengthens_the_stitched_audio(self):
        without = await generate_voice_combined(
            self.script(slides=4), project_id=self.project("nogap"), source=PER_SLIDE
        )
        with_gap = await generate_voice_combined(
            self.script(slides=4),
            project_id=self.project("gap"),
            source=PER_SLIDE,
            slide_gap_seconds=0.5,
        )

        plain = get_wav_duration(
            str(OUTPUT_ROOT / without["audio_url"].removeprefix("/output/"))
        )[0]
        spaced = get_wav_duration(
            str(OUTPUT_ROOT / with_gap["audio_url"].removeprefix("/output/"))
        )[0]

        # Three gaps between four slides.
        self.assertAlmostEqual(spaced - plain, 1.5, delta=0.05)

    async def test_per_slide_does_not_stitch_around_a_failed_slide(self):
        script = self.script(slides=4)
        # Mark slide 3 so the stub can fail it on every retry, not just once.
        script["slides"][2]["narration"] = LONG_NARRATION + " BROKEN"

        original_post = StubSarvamClient.post

        async def fail_marked_slide(self, url, json=None, headers=None):
            if "BROKEN" in json["text"]:
                StubSarvamClient.calls.append(json)
                raise httpx.ConnectError("simulated outage")
            return await original_post(self, url, json=json, headers=headers)

        with mock.patch.object(StubSarvamClient, "post", fail_marked_slide):
            result = await generate_voice_combined(
                script, project_id=self.project("partial"), source=PER_SLIDE
            )

        self.assertFalse(result["success"])
        self.assertIsNone(result["audio_url"], "must not stitch a gap-filled narration")
        # Slide 4 succeeded after the failure, but stitching 1-2-4 would sound
        # complete while silently dropping slide 3.
        self.assertEqual(sorted(result["slide_audio_urls"]), [1, 2, 4])

    async def test_unsupported_language_is_refused_before_any_audio(self):
        for label, generate in (
            ("combined", generate_voice_combined),
            ("per-slide", generate_voice_for_script),
        ):
            with self.subTest(mode=label):
                StubSarvamClient.calls = []
                with self.assertRaises(UnsupportedLanguageError):
                    await generate(
                        self.script(language="as"),
                        project_id=self.project(f"as_{label}"),
                    )
                self.assertEqual(
                    StubSarvamClient.calls, [], "no audio should have been requested"
                )


class PronunciationDictionaryTests(unittest.IsolatedAsyncioTestCase):
    """SARVAM_PRONUNCIATION_DICT_ID is optional and read per-call, so a
    dictionary can be added or rotated without a deploy."""

    def setUp(self):
        StubSarvamClient.calls = []
        patcher = mock.patch(
            "src.services.voice_service.httpx.AsyncClient", StubSarvamClient
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def project(self, name):
        project_id = f"test_voice_dict_{name}"
        audio_dir = AUDIO_ROOT / f"project_{project_id}"
        self.addCleanup(shutil.rmtree, audio_dir, True)
        return project_id

    async def test_dict_id_omitted_when_not_configured(self):
        with mock.patch.dict("os.environ", {"SARVAM_API_KEY": "k"}, clear=True):
            result = await generate_voice_combined(
                {"target_language": "en",
                 "slides": [{"slide_number": 1, "narration": "Hello there."}]},
                project_id=self.project("unset"),
            )

        self.assertTrue(result["success"], result)
        self.assertNotIn("dict_id", StubSarvamClient.calls[0])

    async def test_dict_id_included_when_configured(self):
        with mock.patch.dict(
            "os.environ",
            {"SARVAM_API_KEY": "k", "SARVAM_PRONUNCIATION_DICT_ID": "p_fc28888a"},
        ):
            result = await generate_voice_combined(
                {"target_language": "en",
                 "slides": [{"slide_number": 1, "narration": "Hello there."}]},
                project_id=self.project("set"),
            )

        self.assertTrue(result["success"], result)
        self.assertEqual(StubSarvamClient.calls[0]["dict_id"], "p_fc28888a")

    async def test_blank_dict_id_is_treated_as_unset(self):
        # A variable present but empty (e.g. an unfilled deploy template slot)
        # must not be sent as a literal empty dict_id.
        with mock.patch.dict(
            "os.environ", {"SARVAM_API_KEY": "k", "SARVAM_PRONUNCIATION_DICT_ID": ""}
        ):
            await generate_voice_combined(
                {"target_language": "en",
                 "slides": [{"slide_number": 1, "narration": "Hello there."}]},
                project_id=self.project("blank"),
            )

        self.assertNotIn("dict_id", StubSarvamClient.calls[0])

    async def test_dict_id_applies_to_per_slide_synthesis_too(self):
        with mock.patch.dict(
            "os.environ",
            {"SARVAM_API_KEY": "k", "SARVAM_PRONUNCIATION_DICT_ID": "p_fc28888a"},
        ):
            result = await generate_voice_for_script(
                {"target_language": "en",
                 "slides": [{"slide_number": 1, "narration": "Hello there."}]},
                project_id=self.project("rowwise"),
            )

        self.assertTrue(result["success"], result)
        self.assertEqual(StubSarvamClient.calls[0]["dict_id"], "p_fc28888a")


if __name__ == "__main__":
    unittest.main()
