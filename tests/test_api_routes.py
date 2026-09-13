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


if __name__ == "__main__":
    unittest.main()
