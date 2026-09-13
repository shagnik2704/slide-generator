import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.script_chat.nodes.compliance import compliance_node, compliance_review_node
from src.script_chat.nodes.edit import _compliance_edit_context
from src.script_chat.schemas import ScriptMetadata, ScriptSlide


class ScriptChatComplianceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_script = [
            ScriptSlide(
                slide_number=1,
                slide_type="Title Slide",
                visual_cue="Title slide",
                narration="Welcome to this Spoken Tutorial on Python.",
            ),
            ScriptSlide(
                slide_number=2,
                slide_type="Learning Objectives",
                visual_cue="Display objectives",
                narration="In this tutorial, we will learn basic syntax.",
            ),
        ]
        self.mock_metadata = ScriptMetadata(
            title="Introduction to Python",
            learning_objectives=["Learn basic syntax"],
            prerequisites="None",
            system_requirements="Python 3.11",
            outline_topics=["Overview", "Syntax"],
            meta_tags=["python", "programming"],
        )

    @patch("src.script_chat.nodes.compliance.run_admin_script_compliance")
    @patch("src.script_chat.nodes.compliance.get_stream_writer")
    async def test_compliance_node_preserves_metadata_and_invokes_admin_compliance(
        self, mock_writer_getter, mock_run_compliance
    ):
        mock_writer = MagicMock()
        mock_writer_getter.return_value = mock_writer

        mock_report = {
            "checks": [
                {
                    "id": "two_column_format",
                    "criteria": "Two column format",
                    "ai_review": True,
                    "ai_notes": "Format is valid",
                    "severity": "blocker",
                },
                {
                    "id": "sentence_hard_limit",
                    "criteria": "Sentence under 80 chars",
                    "ai_review": False,
                    "ai_notes": "Row 2 exceeds 80 characters",
                    "severity": "major",
                },
            ],
            "summary": {
                "ai_passed": 1,
                "ai_failed": 1,
                "ai_skipped": 0,
                "total": 2,
                "blockers": 0,
                "major": 1,
                "minor": 0,
            },
            "issues": [
                {
                    "id": "issue-1",
                    "criteria_id": "sentence_hard_limit",
                    "severity": "major",
                    "message": "Sentence length exceeded",
                    "suggested_action": "Split sentence across multiple rows",
                    "evidence": [{"row_number": 2, "field": "narration", "text": "Long text...", "reason": "Length 95"}],
                }
            ],
        }
        mock_run_compliance.return_value = mock_report

        state = {
            "script": [s.model_dump() for s in self.mock_script],
            "metadata": self.mock_metadata.model_dump(),
            "raw_outline": "Overview\nSyntax",
            "foss_name": "Python",
        }

        result = await compliance_node(state)

        # Assert run_admin_script_compliance was called
        mock_run_compliance.assert_called_once()
        call_args = mock_run_compliance.call_args[0][0]

        # Verify full metadata was preserved
        self.assertEqual(call_args["title"], "Introduction to Python")
        self.assertEqual(call_args["domain"], "Python")
        self.assertEqual(call_args["learning_objectives"], ["Learn basic syntax"])
        self.assertEqual(call_args["prerequisites"], "None")
        self.assertEqual(call_args["system_requirements"], "Python 3.11")
        self.assertEqual(call_args["meta_tags"], ["python", "programming"])
        self.assertEqual(len(call_args["slides"]), 2)

        # Verify result contains the full report
        self.assertIn("compliance_results", result)
        self.assertEqual(result["compliance_results"]["summary"]["ai_passed"], 1)
        self.assertEqual(result["compliance_results"]["summary"]["major"], 1)

    @patch("src.script_chat.nodes.compliance.get_stream_writer")
    async def test_compliance_node_returns_error_on_empty_script(self, mock_writer_getter):
        mock_writer_getter.return_value = MagicMock()
        state = {"script": []}
        result = await compliance_node(state)
        self.assertEqual(result.get("current_stage"), "error")

    @patch("src.script_chat.nodes.compliance.interrupt")
    def test_compliance_review_node_handles_approve_and_edit(self, mock_interrupt):
        # Case 1: User approves
        mock_interrupt.return_value = {"action": "approve"}
        state = {
            "compliance_results": {
                "summary": {"ai_passed": 25, "ai_failed": 0},
                "issues": [],
            }
        }
        res_approve = compliance_review_node(state)
        self.assertEqual(res_approve.get("current_stage"), "done")

        # Case 2: User requests edit
        mock_interrupt.return_value = {
            "action": "edit",
            "instruction": "Fix sentence length in row 4",
        }
        res_edit = compliance_review_node(state)
        self.assertEqual(res_edit.get("current_stage"), "edit")
        self.assertEqual(res_edit.get("edit_instruction"), "Fix sentence length in row 4")
        self.assertEqual(len(res_edit.get("messages", [])), 1)

    def test_compliance_edit_context_formats_issues_and_severities(self):
        compliance_results = {
            "checks": [
                {
                    "id": "sentence_hard_limit",
                    "criteria": "Sentences must be under 80 chars",
                    "ai_review": False,
                    "ai_notes": "Row 3 sentence too long",
                    "severity": "major",
                }
            ],
            "issues": [
                {
                    "criteria_id": "sentence_hard_limit",
                    "severity": "major",
                    "message": "Sentence length 92 exceeds limit of 80",
                    "suggested_action": "Split sentence",
                    "evidence": [{"row_number": 3, "field": "narration", "text": "Too long text", "reason": "92 chars"}],
                }
            ],
        }
        context_str = _compliance_edit_context(compliance_results)
        self.assertIn("sentence_hard_limit", context_str)
        self.assertIn("major", context_str)
        self.assertIn("Split sentence", context_str)
        self.assertIn("Too long text", context_str)

    async def test_run_admin_script_compliance_handles_fractional_duration_evidence(self):
        from src.compliance.workflow import run_admin_script_compliance
        script_payload = {
            "presentation_title": "Python Basics",
            "title": "Python Basics",
            "domain": "Python",
            "tutorial": "Python Basics",
            "learning_objectives": ["Understand syntax"],
            "prerequisites": "None",
            "system_requirements": "Python 3.11",
            "outline": ["Syntax"],
            "keywords": ["python"],
            "meta_tags": ["python"],
            "slides": [
                {
                    "slide_number": 1,
                    "slide_type": "Title Slide",
                    "visual_cue": "Show title",
                    "narration": "Welcome to Python Basics Spoken Tutorial.",
                },
                {
                    "slide_number": 2,
                    "slide_type": "Learning Objectives",
                    "visual_cue": "Show objectives",
                    "narration": "In this tutorial we will learn basic Python syntax.",
                },
            ],
        }
        report = await run_admin_script_compliance(script_payload, tutorial_type="demo")
        self.assertIn("checks", report)
        self.assertIn("summary", report)
        self.assertEqual(report["summary"]["total"], 25)
        # Ensure duration_compliance check ran without throwing ValidationError
        duration_check = next((c for c in report["checks"] if c["id"] == "duration_compliance"), None)
        self.assertIsNotNone(duration_check)


if __name__ == "__main__":
    unittest.main()
