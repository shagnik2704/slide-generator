import io
import unittest
import uuid
from starlette.testclient import TestClient

from src.api.server import app
from src.api.auth import create_access_token


class ApiRouteSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.user_id = str(uuid.uuid4())
        cls.valid_token = create_access_token(
            subject=cls.user_id,
            email="test_user@edupyramids.org",
            name="Test User",
        )
        cls.auth_headers = {"Authorization": f"Bearer {cls.valid_token}"}

    def test_root_endpoint_returns_200_and_metadata(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "Spoken Tutorial Generator API")
        self.assertIn("version", data)

    def test_health_endpoint_returns_json_contract(self):
        response = self.client.get("/health")
        self.assertIn(response.status_code, (200, 503))
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data.get("service"), "Spoken Tutorial Generator API")

    def test_health_status_endpoint_returns_json_contract(self):
        response = self.client.get("/health/status")
        self.assertIn(response.status_code, (200, 503))
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("dependencies", data)
        self.assertIn("postgres", data["dependencies"])
        self.assertIn("redis", data["dependencies"])
        self.assertIn("celery_worker", data["dependencies"])
        self.assertIn("storage", data["dependencies"])

    def test_upload_outline_requires_authentication(self):
        file_data = io.BytesIO(b"# Sample Outline")
        response = self.client.post(
            "/upload_outline",
            files={"file": ("outline.md", file_data, "text/markdown")},
        )
        self.assertIn(response.status_code, (401, 403))

    def test_upload_outline_rejects_invalid_file_extensions(self):
        file_data = io.BytesIO(b"executable content")
        response = self.client.post(
            "/upload_outline",
            headers=self.auth_headers,
            files={"file": ("script.exe", file_data, "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only .md, .txt, .docx, or .odt files are allowed", response.text)

    def test_download_nonexistent_image_returns_404(self):
        response = self.client.get("/download/image/project_nonexistent/sample.png")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Image not found", response.text)

    def test_download_nonexistent_redesign_returns_404(self):
        response = self.client.get("/download/redesign/nonexistent_file.csv")
        self.assertEqual(response.status_code, 404)
        self.assertIn("File not found", response.text)

    def test_invalid_json_payload_triggers_422(self):
        response = self.client.post(
            "/translation/translate",
            json={"unexpected_payload_key": "invalid_value"},
        )
        self.assertIn(response.status_code, (422, 401))

    def test_security_headers_middleware(self):
        response = self.client.get("/")
        headers = response.headers
        self.assertIn("x-content-type-options", headers)
        self.assertEqual(headers["x-content-type-options"], "nosniff")

    # --- Voice API Route Tests ---

    def test_generate_voice_missing_script_returns_400(self):
        response = self.client.post("/generate_voice", headers=self.auth_headers, json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("json_script (or script) is required", response.text)

    def test_generate_voice_success(self):
        from unittest.mock import patch, AsyncMock
        mock_result = {
            "audio_urls": {1: "/output/audio/project_101/slide_1.wav"},
            "generated_slides": 1,
            "total_slides": 1,
            "zip_url": "/output/audio/project_101/all_audio.zip",
        }
        with patch("src.services.voice_service.generate_voice_for_script", new=AsyncMock(return_value=mock_result)):
            response = self.client.post(
                "/generate_voice",
                headers=self.auth_headers,
                json={"json_script": [{"slide_number": 1, "narration": "Hello"}]},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["generated_slides"], 1)
            self.assertIn("/output/audio/project_101/slide_1.wav", str(data["audio_urls"]))

    def test_generate_voice_unsupported_language_returns_400(self):
        from unittest.mock import patch, AsyncMock
        from src.services.voice_service import UnsupportedLanguageError
        with patch("src.services.voice_service.generate_voice_for_script", new=AsyncMock(side_effect=UnsupportedLanguageError("Language xx unsupported"))):
            response = self.client.post(
                "/generate_voice",
                headers=self.auth_headers,
                json={"json_script": [{"slide_number": 1, "narration": "Hello"}], "language_code": "xx"},
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("Language xx unsupported", response.text)

    # --- Compliance Route Tests ---

    def test_check_compliance_missing_script_returns_400(self):
        response = self.client.post("/check_compliance", headers=self.auth_headers, json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("json_script is required", response.text)

    def test_check_compliance_success(self):
        from unittest.mock import patch, AsyncMock
        mock_report = {
            "checks": {"two_column_format": {"passed": True, "notes": "OK"}},
            "tutorial_type": "demo",
            "passed": True,
        }
        with patch("src.services.compliance_service.check_compliance", new=AsyncMock(return_value=mock_report)):
            response = self.client.post(
                "/check_compliance",
                headers=self.auth_headers,
                json={"json_script": {"slides": [{"narration": "Click here"}]}},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["passed"])
            self.assertEqual(data["tutorial_type"], "demo")

    # --- Outline Upload Route Tests ---

    def test_upload_outline_valid_markdown_success(self):
        file_data = io.BytesIO(b"# Python Tutorial\n\n- Define function\n- Call function")
        response = self.client.post(
            "/upload_outline",
            headers=self.auth_headers,
            files={"file": ("python_tutorial.md", file_data, "text/markdown")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("outline", data)
        self.assertIn("Python Tutorial", data["outline"])
        self.assertIn("uploaded successfully", data["message"])

    # --- Activity & Audit Admin Routes Tests ---

    def test_admin_logs_endpoint_returns_data(self):
        response = self.client.get("/activity/admin/logs?limit=5", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, (list, dict))

    def test_admin_types_endpoint_returns_list(self):
        response = self.client.get("/activity/admin/types", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("activity_types", data)
        self.assertIsInstance(data["activity_types"], list)

    def test_admin_export_formats_and_validation(self):
        # CSV format
        csv_res = self.client.get("/activity/admin/export?format=csv", headers=self.auth_headers)
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn("text/csv", csv_res.headers.get("content-type", ""))

        # JSON format
        json_res = self.client.get("/activity/admin/export?format=json", headers=self.auth_headers)
        self.assertEqual(json_res.status_code, 200)
        self.assertIn("application/json", json_res.headers.get("content-type", ""))

        # Invalid format triggers validation error (422)
        invalid_res = self.client.get("/activity/admin/export?format=xml", headers=self.auth_headers)
        self.assertEqual(invalid_res.status_code, 422)


if __name__ == "__main__":
    unittest.main()

