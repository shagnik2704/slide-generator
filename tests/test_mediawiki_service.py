import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.services.mediawiki_service import (
    create_mediawiki_script,
    export_to_mediawiki,
    resolve_metadata,
)


CURRENT_SCRIPT = {
    "metadata": {
        "title": "Introduction to TensorFlow",
        "learning_objectives": ["Use **TensorFlow** in a notebook"],
        "prerequisites": "Basic Python",
        "system_requirements": "Ubuntu 22.04, Python 3.10",
        "outline_topics": ["Tensors", "Constants"],
        "meta_tags": ["tensorflow", "python"],
    },
    "script": [
        {
            "slide_number": 1,
            "slide_type": "Title Slide",
            "visual_cue": "Slide 1\nTitle Slide",
            "narration": "Welcome to the **Spoken Tutorial** on **TensorFlow**.",
        },
        {
            "slide_number": 5,
            "slide_type": "Pre-requisites",
            "visual_cue": "Slide 5\nPre-requisites\nhttp://EduPyramids.org",
            "narration": "You need basic **Python** knowledge.",
        },
        {
            "slide_number": 7,
            "slide_type": "Content",
            "visual_cue": "Click **Save**",
            "narration": "Now click the **Save** button.",
        },
    ],
}

LEGACY_SCRIPT = {
    "presentation_title": "Introduction to TensorFlow",
    "learning_objectives": ["Use TensorFlow in a notebook"],
    "prerequisites": "Basic Python",
    "meta_tags": ["tensorflow"],
    "outline": ["Tensors"],
    "slides": [
        {
            "title": "Title Slide",
            "image_prompt": "Title Slide",
            "narration": "Welcome to the **Spoken Tutorial** on **TensorFlow**.",
        },
        {
            "title": "Pre-requisite",
            "image_prompt": "Pre-requisite Slide\nhttps://EduPyramids.org",
            "narration": "You need basic **Python** knowledge.",
        },
    ],
}


class MediaWikiCurrentFormatTests(unittest.TestCase):
    """The script-chat format uses `script` / `visual_cue` / `slide_type`."""

    def test_every_slide_reaches_the_table(self):
        content = create_mediawiki_script(CURRENT_SCRIPT)

        # One "|-" row separator per slide, plus the header row.
        self.assertEqual(content.count("|-\n||"), len(CURRENT_SCRIPT["script"]))
        self.assertIn("Now click the '''Save''' button.", content)

    def test_metadata_is_read_from_the_nested_metadata_key(self):
        content = create_mediawiki_script(CURRENT_SCRIPT)

        self.assertIn("'''Introduction to TensorFlow'''", content)
        self.assertNotIn("Spoken Tutorial Script", content)  # the fallback title
        self.assertIn("! System Requirements", content)
        self.assertIn("Ubuntu 22.04, Python 3.10", content)
        self.assertIn("* Tensors", content)  # outline_topics -> Outline

    def test_edupyramids_url_survives_on_the_prerequisite_slide(self):
        content = create_mediawiki_script(CURRENT_SCRIPT)

        self.assertIn("http://EduPyramids.org", content)

    def test_multi_line_visual_cue_content_is_preserved(self):
        """A `visual_cue` carries on-screen content, so it must not collapse
        to a bare slide label the way a legacy `image_prompt` does."""
        content = create_mediawiki_script(CURRENT_SCRIPT)

        self.assertIn("'''Slide 5'''", content)
        self.assertIn("'''Pre-requisites'''", content)

    def test_markdown_bold_becomes_wiki_bold(self):
        content = create_mediawiki_script(CURRENT_SCRIPT)

        self.assertIn("Click '''Save'''", content)
        self.assertNotIn("**Save**", content)


class PrerequisiteUrlTests(unittest.TestCase):
    """The prerequisite slide must always show the EduPyramids link, since its
    narration says 'visit the website shown on your screen' — even when the
    source cue is only the bare label."""

    def _cue(self, script, visual_cue):
        script = {
            "metadata": {"title": "T", "learning_objectives": ["x"], "prerequisites": "",
                         "system_requirements": "", "outline_topics": ["x"], "meta_tags": ["x"]},
            "script": [{"slide_number": 5, "slide_type": "Pre-requisites",
                        "visual_cue": visual_cue, "narration": "n"}],
        }
        return create_mediawiki_script(script)

    def test_injected_when_cue_is_label_only(self):
        content = self._cue(CURRENT_SCRIPT, "Pre-requisite Slide")
        self.assertIn("EduPyramids.org", content)

    def test_not_duplicated_when_cue_already_has_url(self):
        content = self._cue(CURRENT_SCRIPT, "Slide 5\nPre-requisites\nhttp://EduPyramids.org")
        self.assertEqual(content.lower().count("edupyramids"), 1)

    def test_legacy_label_only_gets_url(self):
        from src.services.mediawiki_service import format_visual_cue
        self.assertIn("EduPyramids.org", format_visual_cue("Pre-requisite Slide", ""))

    def test_not_added_to_non_prerequisite_slides(self):
        from src.services.mediawiki_service import format_visual_cue_text
        self.assertNotIn("edupyramids", format_visual_cue_text("Slide 1\nTitle Slide").lower())
        self.assertNotIn("edupyramids", format_visual_cue_text("Click **Save**").lower())

    def test_injected_even_when_label_is_bold_wrapped_in_source(self):
        """Some source cues wrap the whole label block in markdown bold, so the
        prerequisite label arrives as part of one '''...''' span. The URL must
        still be injected."""
        from src.services.mediawiki_service import format_visual_cue_text
        out = format_visual_cue_text("**Slide 5\nPre-requisite slide**")
        self.assertIn("EduPyramids.org", out)

    def test_bold_wrapped_label_block_splits_into_clean_labels(self):
        from src.services.mediawiki_service import format_visual_cue_text
        out = format_visual_cue_text("**Slide 4\nSystem Requirements Slide**")
        self.assertIn("'''Slide 4'''", out)
        self.assertIn("'''System Requirements Slide'''", out)
        # No stray bold span running across the two lines.
        self.assertNotIn("'''Slide 4<br", out)


class BoilerplateSlideContentTests(unittest.TestCase):
    """Reported bug: Acknowledgement / Disclaimer / Thank-You slides exported to
    wiki showed only the bold title, dropping the names and sentences on them.
    That happened on the legacy (image_prompt) path used by DOCX uploads."""

    def test_legacy_acknowledgement_keeps_the_names(self):
        from src.services.mediawiki_service import format_visual_cue
        out = format_visual_cue(
            "Acknowledgement Slide\nScript Writer: Debosmita\nReviewer: Saisudha", ""
        )
        self.assertIn("'''Acknowledgement Slide'''", out)
        self.assertIn("Script Writer: Debosmita", out)
        self.assertIn("Reviewer: Saisudha", out)

    def test_legacy_disclaimer_keeps_the_sentence(self):
        from src.services.mediawiki_service import format_visual_cue
        out = format_visual_cue("Disclaimer Slide\nAs AI tools evolve, use any AI chatbot.", "")
        self.assertIn("As AI tools evolve, use any AI chatbot.", out)

    def test_legacy_thank_you_keeps_the_credit_sentence(self):
        from src.services.mediawiki_service import format_visual_cue
        out = format_visual_cue(
            "Thank You Slide\nThis Spoken Tutorial is brought to you by EduPyramids, SINE, IIT Bombay.", ""
        )
        self.assertIn("brought to you by EduPyramids, SINE, IIT Bombay.", out)

    def test_single_line_boilerplate_label_is_unchanged(self):
        from src.services.mediawiki_service import format_visual_cue
        self.assertEqual(format_visual_cue("Title Slide", ""), "'''Title Slide'''")


class MediaWikiLegacyFormatTests(unittest.TestCase):
    """The pre-script-chat format must keep working — the docx upload path
    (`docx_to_json`) still produces `slides` / `image_prompt`."""

    def test_slides_and_metadata_still_render(self):
        content = create_mediawiki_script(LEGACY_SCRIPT)

        self.assertEqual(content.count("|-\n||"), len(LEGACY_SCRIPT["slides"]))
        self.assertIn("'''Introduction to TensorFlow'''", content)
        self.assertIn("'''Title Slide'''", content)

    def test_prerequisite_slide_keeps_a_linkable_edupyramids_url(self):
        content = create_mediawiki_script(LEGACY_SCRIPT)

        self.assertIn("'''Pre-requisite Slide'''", content)
        self.assertIn("https://EduPyramids.org", content)


class ExportToMediaWikiTests(unittest.TestCase):
    def test_returns_the_markup_and_writes_the_same_bytes_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = export_to_mediawiki(CURRENT_SCRIPT, output_dir=tmp_dir)

            self.assertIn("== Script Metadata ==", result["content"])
            written = Path(result["file_path"]).read_text(encoding="utf-8")
            self.assertEqual(written, result["content"])

    def test_renders_the_script_only_once(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch(
                "src.services.mediawiki_service.create_mediawiki_script",
                wraps=create_mediawiki_script,
            ) as render:
                export_to_mediawiki(CURRENT_SCRIPT, output_dir=tmp_dir)

            self.assertEqual(render.call_count, 1)


class ResolveMetadataTests(unittest.TestCase):
    def test_flat_keys_win_over_nested_ones(self):
        resolved = resolve_metadata({
            "presentation_title": "Flat title",
            "metadata": {"title": "Nested title"},
        })

        self.assertEqual(resolved["title"], "Flat title")

    def test_falls_back_to_a_default_title(self):
        self.assertEqual(resolve_metadata({})["title"], "Spoken Tutorial Script")


if __name__ == "__main__":
    unittest.main()
