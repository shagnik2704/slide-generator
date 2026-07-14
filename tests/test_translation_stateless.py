"""Regression tests for the stateless translation API."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.api.routes.translation import BatchTranslateRequest, router, translate_batch
from src.services.translation_service import TranslationResult


class StatelessTranslationTests(unittest.IsolatedAsyncioTestCase):
    @patch("src.api.routes.translation.batch_translate", new_callable=AsyncMock)
    async def test_batch_translation_returns_results_without_persistence_id(self, mock_translate):
        mock_translate.return_value = [
            TranslationResult(
                language="Hindi",
                language_code="hi",
                language_native="हिंदी",
                translated_script={"slides": []},
                success=True,
            )
        ]

        result = await translate_batch(
            BatchTranslateRequest(json_script={"slides": []}, languages=["hi"]),
            SimpleNamespace(sub="tester@example.com"),
        )

        self.assertEqual(result.total_success, 1)
        self.assertNotIn("project_id", result.model_dump())

    def test_database_backed_routes_are_removed(self):
        paths = {route.path for route in router.routes}

        self.assertNotIn("/translation/update_cell", paths)
        self.assertNotIn("/translation/project_data/{project_id}", paths)
        self.assertNotIn("/translation/generate_cell_audio", paths)


if __name__ == "__main__":
    unittest.main()
