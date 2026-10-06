"""Tests for slide content extractor and Beamer slides route."""
import unittest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient

from src.services.content_extractor import (
    get_candidate_extractors,
    extract_slide_content,
    extract_slide_content_with_fallback,
    _fallback_extraction,
    _rule_based_slide_content,
    ExtractedSlideContent,
    SectionContent,
)
from src.api.server import app
from src.api.auth import create_access_token


class ContentExtractorUnitTests(unittest.TestCase):
    def setUp(self):
        self.sample_script = {
            "title": "Introduction to Python Programming",
            "slides": [
                {
                    "slide_num": 1,
                    "title": "Title Slide",
                    "narration": "Welcome to Python tutorial."
                },
                {
                    "slide_num": 2,
                    "title": "Learning Objectives",
                    "narration": "In this tutorial, you will learn how to:\n• Write print statements\n• Declare variables\n• Run python files"
                },
                {
                    "slide_num": 3,
                    "title": "System Requirements",
                    "narration": "For this tutorial, you will need:\n• Python 3.11\n• VS Code editor"
                },
                {
                    "slide_num": 4,
                    "title": "Prerequisites",
                    "narration": "To follow this tutorial, you should be:\n• Familiar with terminal commands\nFor the prerequisite tutorials please visit this website."
                },
                {
                    "slide_num": 5,
                    "title": "Content 1",
                    "narration": "Variables in Python are dynamically typed."
                },
                {
                    "slide_num": 6,
                    "title": "Summary",
                    "narration": "In this tutorial, you learned about:\n• Declaring variables\n• Printing output"
                },
                {
                    "slide_num": 7,
                    "title": "Assignment",
                    "narration": "As an assignment, please:\n• Create a script that prints your name\n• Calculate sum of two numbers"
                },
                {
                    "slide_num": 8,
                    "title": "Acknowledgement",
                    "narration": "Domain Expert: Dr. Rajesh Sharma from IIT Bombay."
                }
            ]
        }

    def test_candidate_extractors_includes_sarvam(self):
        with patch.dict("os.environ", {"SARVAM_API_KEY": "valid-sarvam-key-12345"}, clear=True):
            candidates = get_candidate_extractors()
            provider_names = [name for name, _ in candidates]
            self.assertIn("Sarvam GLM-5.3", provider_names)
            
            # Verify the model configuration for Sarvam
            sarvam_llm = next(llm for name, llm in candidates if name == "Sarvam GLM-5.3")
            self.assertEqual(sarvam_llm.model_name, "glm5.3")
            self.assertEqual(str(sarvam_llm.openai_api_base), "https://api.sarvam.ai/v2")
            self.assertEqual(sarvam_llm.default_headers.get("api-subscription-key"), "valid-sarvam-key-12345")

    def test_candidate_extractors_skips_mock_keys(self):
        with patch.dict(
            "os.environ",
            {
                "SARVAM_API_KEY": "mock-sarvam-key-for-ci",
                "OPENAI_API_KEY": "mock-openai-key-for-ci",
                "GOOGLE_API_KEY": "mock-google-key-for-ci",
            },
            clear=True
        ):
            candidates = get_candidate_extractors()
            self.assertEqual(len(candidates), 0)

    def test_rule_based_fallback_extraction(self):
        data = _fallback_extraction(self.sample_script)
        self.assertEqual(data["tutorial_name"], "Introduction to Python Programming")
        self.assertTrue(len(data["learning_objectives"]) >= 2)
        self.assertTrue(len(data["system_requirements"]) >= 1)
        self.assertTrue(len(data["summary_points"]) >= 1)
        self.assertTrue(len(data["assignment_items"]) >= 1)
        self.assertEqual(data["domain_expert"], "Dr. Rajesh Sharma")
        self.assertEqual(data["domain_expert_org"], "IIT Bombay")

    def test_extract_slide_content_with_fallback_offline(self):
        with patch("src.services.content_extractor.get_candidate_extractors", return_value=[]):
            res = extract_slide_content_with_fallback(self.sample_script)
            self.assertIn("tutorial_name", res)
            self.assertIn("learning_objectives", res)
            self.assertIn("learning_objectives_intro", res)
            self.assertEqual(res["tutorial_name"], "Introduction to Python Programming")
            self.assertEqual(res["domain_expert"], "Dr. Rajesh Sharma")

    def test_extract_slide_content_llm_success(self):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.invoke.return_value = ExtractedSlideContent(
            tutorial_name="Python Quickstart",
            learning_objectives=SectionContent(
                intro="In this tutorial, you will learn to",
                items=["Define functions", "Call functions"]
            ),
            prerequisites=SectionContent(
                intro="To follow this tutorial, you should be",
                items=["Familiar with syntax"]
            ),
            system_requirements=SectionContent(
                intro="For this tutorial, you will need",
                items=["Python 3"]
            ),
            summary=SectionContent(
                intro="In this tutorial, you learned about",
                items=["Functions"]
            ),
            assignment=SectionContent(
                intro="As an assignment",
                items=["Write a factorial function"]
            ),
            domain_expert="Jane Doe",
            domain_expert_org="Open Tech Institute",
            code_file_info=None,
        )

        with patch("src.services.content_extractor.get_candidate_extractors", return_value=[("Mock Sarvam", mock_llm)]):
            res = extract_slide_content_with_fallback(self.sample_script)
            self.assertEqual(res["tutorial_name"], "Python Quickstart")
            self.assertEqual(res["learning_objectives"], ["Define functions", "Call functions"])
            self.assertEqual(res["domain_expert"], "Jane Doe")


import uuid


class SlidesRouteEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.token = create_access_token(
            subject=str(uuid.uuid4()),
            email="test_slides@edupyramids.org",
            name="Test User",
        )
        cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}

    def test_generate_slides_endpoint_contract(self):
        payload = {
            "tutorial_name": "Test Tutorial",
            "num_content_slides": 5,
            "theme_color": "#1F4E79"
        }
        response = self.client.post("/generate_slides", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tex_content", data)
        self.assertIn("filename", data)
        self.assertIn("zip_filename", data)
        self.assertIn("zip_url", data)
        self.assertEqual(data["num_boilerplate_slides"], 8)
        self.assertEqual(data["num_content_slides"], 5)
        self.assertEqual(data["total_slides"], 13)
        self.assertFalse(data["auto_filled"])

    def test_generate_slides_endpoint_with_script(self):
        script = {
            "title": "Script Driven Tutorial",
            "slides": [
                {"slide_num": 1, "title": "Intro", "narration": "Intro text"},
                {"slide_num": 2, "title": "Objectives", "narration": "• Obj 1\n• Obj 2"},
                {"slide_num": 3, "title": "Content A", "narration": "Body A"},
                {"slide_num": 4, "title": "Content B", "narration": "Body B"},
                {"slide_num": 5, "title": "Summary", "narration": "• Sum 1"},
            ]
        }
        payload = {
            "json_script": script,
            "theme_color": "#708094"
        }
        response = self.client.post("/generate_slides", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["auto_filled"])
        self.assertEqual(data["num_boilerplate_slides"], 8)
        self.assertGreaterEqual(data["total_slides"], 9)
        self.assertIn("Script_Driven_Tutorial", data["filename"])


if __name__ == "__main__":
    unittest.main()
