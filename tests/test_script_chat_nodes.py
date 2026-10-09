"""Unit tests for Script Chat LangGraph nodes: generate, review, edit, and metadata_edit."""
import unittest
from unittest.mock import MagicMock, patch

from src.script_chat.nodes.generate import generate_node, script_review_node
from src.script_chat.nodes.edit import edit_node, _compliance_edit_context, _recent_edit_context
from src.script_chat.nodes.metadata_edit import metadata_edit_node
from src.script_chat.schemas import ScriptSlide, ScriptMetadata, ScriptResult


class ScriptChatNodesTests(unittest.TestCase):
    """Test suite for script chat execution nodes and error branches."""

    def setUp(self):
        self.sample_metadata = {
            "title": "Introduction to Python Functions",
            "learning_objectives": ["Define a function", "Call a function"],
            "prerequisites": "Basic Python syntax",
            "system_requirements": "Python 3.10+",
            "outline_topics": ["Overview", "Functions"],
            "meta_tags": ["python", "functions"],
        }
        self.sample_script = [
            {
                "slide_number": 1,
                "slide_type": "title",
                "visual_cue": "Title slide: Python Functions",
                "narration": "Welcome to this tutorial on Python functions.",
            },
            {
                "slide_number": 2,
                "slide_type": "content",
                "visual_cue": "Code editor showing def greet(): print('Hello')",
                "narration": "In Python, we define a function using the def keyword.",
            },
        ]

    # --- Generate Node Tests ---

    @patch("src.script_chat.nodes.generate.get_stream_writer")
    @patch("src.script_chat.nodes.generate.invoke_structured_with_responses_tools")
    def test_generate_node_success(self, mock_llm, mock_writer):
        """generate_node successfully calls LLM and returns review stage."""
        mock_writer.return_value = MagicMock()
        mock_llm.return_value = ScriptResult(
            script=[
                ScriptSlide(slide_number=1, slide_type="title", visual_cue="Slide 1", narration="Narration 1"),
                ScriptSlide(slide_number=2, slide_type="content", visual_cue="Slide 2", narration="Narration 2"),
            ],
            message="Script generated successfully.",
        )

        state = {
            "metadata": self.sample_metadata,
            "raw_outline": "1. Introduction\n2. Function definition",
            "script_version": 1,
        }

        result = generate_node(state)
        self.assertEqual(result["current_stage"], "review")
        self.assertEqual(result["script_version"], 2)
        self.assertEqual(len(result["script"]), 2)
        self.assertEqual(result["messages"][0]["content"], "Script generated successfully.")

    @patch("src.script_chat.nodes.generate.get_stream_writer")
    def test_generate_node_invalid_metadata_returns_error(self, mock_writer):
        """generate_node with corrupt metadata structure returns error stage."""
        mock_writer.return_value = MagicMock()
        state = {
            "metadata": "not a dictionary or invalid metadata",
            "raw_outline": "outline",
        }
        result = generate_node(state)
        self.assertEqual(result.get("current_stage"), "error")

    @patch("src.script_chat.nodes.generate.get_stream_writer")
    @patch("src.script_chat.nodes.generate.invoke_structured_with_responses_tools")
    def test_generate_node_llm_failure_returns_error(self, mock_llm, mock_writer):
        """generate_node handles LLM exception gracefully."""
        mock_writer.return_value = MagicMock()
        mock_llm.side_effect = RuntimeError("OpenAI rate limit exceeded")

        state = {
            "metadata": self.sample_metadata,
            "raw_outline": "outline",
        }
        result = generate_node(state)
        self.assertEqual(result.get("current_stage"), "error")

    # --- Script Review Node Tests ---

    @patch("src.script_chat.nodes.generate.interrupt")
    def test_script_review_node_approve(self, mock_interrupt):
        """User approval advances current_stage to compliance."""
        mock_interrupt.return_value = {"action": "approve"}

        state = {
            "script": self.sample_script,
            "messages": [{"role": "ai", "content": "Please review your script."}],
        }
        result = script_review_node(state)
        self.assertEqual(result["current_stage"], "compliance")

    @patch("src.script_chat.nodes.generate.interrupt")
    def test_script_review_node_edit(self, mock_interrupt):
        """User edit request transitions to edit stage with instruction."""
        mock_interrupt.return_value = {
            "action": "edit",
            "instruction": "Add a slide explaining return statements.",
        }

        state = {
            "script": self.sample_script,
            "messages": [],
        }
        result = script_review_node(state)
        self.assertEqual(result["current_stage"], "edit")
        self.assertEqual(result["edit_instruction"], "Add a slide explaining return statements.")
        self.assertEqual(len(result["messages"]), 1)

    @patch("src.script_chat.nodes.generate.interrupt")
    def test_script_review_node_invalid_action(self, mock_interrupt):
        """Unknown user action results in error stage."""
        mock_interrupt.return_value = {"action": "unrecognized_action"}

        state = {"script": self.sample_script}
        result = script_review_node(state)
        self.assertEqual(result["current_stage"], "error")

    def test_script_review_node_corrupted_script(self):
        """Corrupted script data fails fast with error stage."""
        state = {"script": "not a list"}
        result = script_review_node(state)
        self.assertEqual(result["current_stage"], "error")

    # --- Edit Node Tests ---

    @patch("src.script_chat.nodes.edit.get_stream_writer")
    def test_edit_node_no_instruction(self, mock_writer):
        """edit_node with empty edit_instruction returns empty dict."""
        mock_writer.return_value = MagicMock()
        state = {"script": self.sample_script, "edit_instruction": ""}
        result = edit_node(state)
        self.assertEqual(result, {})

    @patch("src.script_chat.nodes.edit.get_stream_writer")
    def test_edit_node_invalid_script_state(self, mock_writer):
        """edit_node with invalid script data returns error stage."""
        mock_writer.return_value = MagicMock()
        state = {"script": "invalid", "edit_instruction": "fix slide 1"}
        result = edit_node(state)
        self.assertEqual(result.get("current_stage"), "error")

    @patch("src.script_chat.nodes.edit.get_stream_writer")
    @patch("src.script_chat.nodes.edit.invoke_structured_with_responses_tools")
    def test_edit_node_success(self, mock_llm, mock_writer):
        """edit_node successfully invokes LLM and updates script and version."""
        mock_writer.return_value = MagicMock()
        mock_llm.return_value = ScriptResult(
            script=[
                ScriptSlide(slide_number=1, slide_type="title", visual_cue="Updated Slide 1", narration="Updated Narration"),
            ],
            message="Edit applied.",
        )

        state = {
            "script": self.sample_script,
            "edit_instruction": "Shorten slide 1 narration",
            "script_version": 2,
            "messages": [{"role": "user", "content": "Please edit slide 1"}],
        }

        result = edit_node(state)
        self.assertEqual(result["current_stage"], "review")
        self.assertEqual(result["script_version"], 3)
        self.assertIsNone(result["edit_instruction"])
        self.assertEqual(result["script"][0]["visual_cue"], "Updated Slide 1")

    @patch("src.script_chat.nodes.edit.get_stream_writer")
    @patch("src.script_chat.nodes.edit.invoke_structured_with_responses_tools")
    def test_edit_node_llm_failure(self, mock_llm, mock_writer):
        """edit_node catches LLM exception and returns error stage."""
        mock_writer.return_value = MagicMock()
        mock_llm.side_effect = Exception("Model service down")

        state = {
            "script": self.sample_script,
            "edit_instruction": "Add examples",
        }
        result = edit_node(state)
        self.assertEqual(result.get("current_stage"), "error")

    def test_edit_context_helpers(self):
        """Test _compliance_edit_context and _recent_edit_context helper functions."""
        # Empty compliance
        self.assertEqual(_compliance_edit_context(None), "(No compliance results yet)")

        # Compliance with issues
        compliance_results = {
            "checks": [
                {"id": "check_1", "criteria": "Two-column format", "ai_notes": "Passed", "ai_review": True},
                {"id": "check_2", "criteria": "Demonstration time", "ai_notes": "Needs more code", "ai_review": False},
            ],
            "issues": [
                {"criteria_id": "check_2", "severity": "warning", "message": "Add more steps", "evidence": []}
            ],
        }
        ctx = _compliance_edit_context(compliance_results)
        self.assertIn("Demonstration time", ctx)
        self.assertIn("Needs more code", ctx)

        # Message history formatting
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "ai", "content": "Welcome to script builder"},
        ]
        history = _recent_edit_context(messages)
        self.assertIn("USER: Hello", history)
        self.assertIn("AI: Welcome to script builder", history)

    # --- Metadata Edit Node Tests ---

    @patch("src.script_chat.nodes.metadata_edit.get_stream_writer")
    def test_metadata_edit_no_instruction(self, mock_writer):
        """metadata_edit_node with empty instruction returns empty dict."""
        mock_writer.return_value = MagicMock()
        state = {"metadata": self.sample_metadata, "edit_instruction": ""}
        result = metadata_edit_node(state)
        self.assertEqual(result, {})

    @patch("src.script_chat.nodes.metadata_edit.get_stream_writer")
    @patch("src.script_chat.nodes.metadata_edit.invoke_structured")
    def test_metadata_edit_success(self, mock_llm, mock_writer):
        """metadata_edit_node updates metadata via LLM and clears instruction."""
        mock_writer.return_value = MagicMock()
        mock_llm.return_value = ScriptMetadata(
            title="Updated Title",
            learning_objectives=["New objective"],
            prerequisites="None",
            system_requirements="Any",
            outline_topics=["Topic 1"],
            meta_tags=["tag1"],
        )

        state = {
            "metadata": self.sample_metadata,
            "edit_instruction": "Change title to Updated Title",
        }
        result = metadata_edit_node(state)
        self.assertIsNone(result["edit_instruction"])
        self.assertEqual(result["metadata"]["title"], "Updated Title")

    @patch("src.script_chat.nodes.metadata_edit.get_stream_writer")
    @patch("src.script_chat.nodes.metadata_edit.invoke_structured")
    def test_metadata_edit_llm_failure(self, mock_llm, mock_writer):
        """metadata_edit_node handles LLM failure with error stage."""
        mock_writer.return_value = MagicMock()
        mock_llm.side_effect = Exception("Service unavailable")

        state = {
            "metadata": self.sample_metadata,
            "edit_instruction": "Update title",
        }
        result = metadata_edit_node(state)
        self.assertEqual(result.get("current_stage"), "error")


if __name__ == "__main__":
    unittest.main()
