"""Unit tests for Script Chat FastAPI routes and endpoints."""
import io
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

from src.api.server import app
from src.api.auth import create_access_token
from src.script_chat.routes import _sse_event, _interrupt_payload


class ScriptChatRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.user_id = str(uuid.uuid4())
        cls.valid_token = create_access_token(
            subject=cls.user_id,
            email="author@edupyramids.org",
            name="Author User",
        )
        cls.auth_headers = {"Authorization": f"Bearer {cls.valid_token}"}

    def setUp(self):
        self.thread_id = str(uuid.uuid4())
        self.sample_script = [
            {
                "slide_number": 1,
                "slide_type": "title",
                "visual_cue": "Slide 1 Cue",
                "narration": "Slide 1 Narration",
            },
            {
                "slide_number": 2,
                "slide_type": "content",
                "visual_cue": "Slide 2 Cue",
                "narration": "Slide 2 Narration",
            },
        ]
        self.sample_metadata = {
            "title": "Tutorial on NumPy Arrays",
            "foss_name": "NumPy",
            "learning_objectives": ["Create 1D arrays", "Create 2D arrays"],
            "prerequisites": "Basic Python",
            "system_requirements": "Python 3.10+",
            "outline_topics": ["Arrays", "Indexing"],
            "meta_tags": ["numpy", "python"],
        }

    # --- Helper Function Tests ---

    def test_sse_event_formatting(self):
        evt = _sse_event("progress", {"status": "generating", "progress": 50})
        self.assertTrue(evt.startswith("event: progress\n"))
        self.assertIn('"progress": 50', evt)
        self.assertTrue(evt.endswith("\n\n"))

    def test_interrupt_payload_helper(self):
        # Empty state
        self.assertIsNone(_interrupt_payload(MagicMock(tasks=[])))

        # State with interrupt
        mock_task = MagicMock()
        mock_task.interrupts = [MagicMock(value={"type": "script_review", "data": 123})]
        state_with_interrupt = MagicMock(tasks=[mock_task])
        self.assertEqual(_interrupt_payload(state_with_interrupt), {"type": "script_review", "data": 123})

    # --- Thread Management Tests ---

    @patch("src.script_chat.routes.list_threads", new_callable=AsyncMock)
    def test_list_threads_endpoint(self, mock_list):
        mock_list.return_value = [
            {"thread_id": self.thread_id, "foss_name": "NumPy", "status": "running"}
        ]
        res = self.client.get("/script-chat/threads", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("threads", data)
        self.assertEqual(len(data["threads"]), 1)
        self.assertEqual(data["threads"][0]["thread_id"], self.thread_id)

    @patch("src.script_chat.routes.archive_thread", new_callable=AsyncMock)
    def test_archive_thread_endpoint(self, mock_archive):
        # Successful archive
        mock_archive.return_value = True
        res = self.client.post(f"/script-chat/threads/{self.thread_id}/archive", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Thread not found
        mock_archive.return_value = False
        res = self.client.post(f"/script-chat/threads/{self.thread_id}/archive", headers=self.auth_headers)
        self.assertEqual(res.status_code, 404)

    # --- Thread History & Ownership ---

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    def test_get_history_not_found(self, mock_get_thread):
        mock_get_thread.return_value = None
        res = self.client.get(f"/script-chat/history/{self.thread_id}", headers=self.auth_headers)
        self.assertEqual(res.status_code, 404)
        self.assertIn("Thread not found", res.text)

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_get_history_success(self, mock_get_graph, mock_get_thread):
        mock_get_thread.return_value = {
            "thread_id": self.thread_id,
            "status": "awaiting_review",
            "created_at": "2026-10-10T00:00:00Z",
            "updated_at": "2026-10-10T00:05:00Z",
        }
        mock_state = MagicMock()
        mock_state.values = {
            "raw_outline": "1. Intro",
            "current_stage": "script_review",
            "foss_name": "NumPy",
            "script_version": 1,
            "script": self.sample_script,
            "metadata": self.sample_metadata,
        }
        mock_state.tasks = []
        mock_get_graph.return_value.aget_state = AsyncMock(return_value=mock_state)

        res = self.client.get(f"/script-chat/history/{self.thread_id}", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["thread_id"], self.thread_id)
        self.assertEqual(data["current_stage"], "script_review")
        self.assertEqual(len(data["script"]), 2)

    # --- Manual Edit (Zero Tokens) ---

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_manual_edit_not_at_script_review_rejected(self, mock_get_graph, mock_get_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        # Not at review interrupt
        mock_state = MagicMock(values={"script": self.sample_script}, tasks=[])
        mock_get_graph.return_value.aget_state = AsyncMock(return_value=mock_state)

        res = self.client.put(
            f"/script-chat/edit/{self.thread_id}",
            headers=self.auth_headers,
            json={"slide_number": 1, "field": "narration", "value": "Updated text"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Manual edits are only allowed during script review", res.text)

    @patch("src.script_chat.routes.update_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_manual_edit_slide_success(self, mock_get_graph, mock_get_thread, mock_update_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}

        mock_task = MagicMock()
        mock_task.interrupts = [MagicMock(value={"type": "script_review"})]
        mock_state = MagicMock(
            values={"script": self.sample_script, "script_version": 1, "current_stage": "script_review"},
            tasks=[mock_task],
        )
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_state)
        mock_graph.aupdate_state = AsyncMock()
        mock_get_graph.return_value = mock_graph

        res = self.client.put(
            f"/script-chat/edit/{self.thread_id}",
            headers=self.auth_headers,
            json={"slide_number": 1, "field": "narration", "value": "Manually patched narration"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["slide_number"], 1)
        self.assertIn("Slide updated", data["message"])
        mock_graph.aupdate_state.assert_called_once()

    # --- Stage Jump ---

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_jump_validation_review_missing_outline(self, mock_get_graph, mock_get_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        mock_state = MagicMock(values={"raw_outline": ""})
        mock_get_graph.return_value.aget_state = AsyncMock(return_value=mock_state)

        res = self.client.post(
            f"/script-chat/jump/{self.thread_id}",
            headers=self.auth_headers,
            json={"target_stage": "validation_review"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Cannot jump to validation review without raw outline", res.text)

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_jump_metadata_review_missing_metadata(self, mock_get_graph, mock_get_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        mock_state = MagicMock(values={"metadata": None})
        mock_get_graph.return_value.aget_state = AsyncMock(return_value=mock_state)

        res = self.client.post(
            f"/script-chat/jump/{self.thread_id}",
            headers=self.auth_headers,
            json={"target_stage": "metadata_review"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Cannot jump to metadata review without metadata", res.text)

    @patch("src.script_chat.routes.update_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_jump_script_review_success(self, mock_get_graph, mock_get_thread, mock_update_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        mock_state = MagicMock(values={"script": self.sample_script})
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_state)
        mock_graph.aupdate_state = AsyncMock()
        mock_get_graph.return_value = mock_graph

        res = self.client.post(
            f"/script-chat/jump/{self.thread_id}",
            headers=self.auth_headers,
            json={"target_stage": "script_review"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])
        self.assertIn("Successfully jumped to script_review", res.json()["message"])

    # --- Revert to Past Checkpoint ---

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_revert_state_checkpoint_not_found(self, mock_get_graph, mock_get_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        current_state = MagicMock(values={"current_stage": "script_review"})
        empty_past_state = MagicMock(values={})

        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(side_effect=[current_state, empty_past_state])
        mock_get_graph.return_value = mock_graph

        res = self.client.post(
            f"/script-chat/revert/{self.thread_id}",
            headers=self.auth_headers,
            json={"checkpoint_id": "nonexistent_chk_123"},
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("Past checkpoint not found", res.text)

    @patch("src.script_chat.routes.update_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_revert_state_success(self, mock_get_graph, mock_get_thread, mock_update_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        current_state = MagicMock(values={"current_stage": "script_review"})
        past_state = MagicMock(values={"script": self.sample_script, "script_version": 2, "current_stage": "review"}, tasks=[])

        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(side_effect=[current_state, past_state])
        mock_graph.aupdate_state = AsyncMock()
        mock_get_graph.return_value = mock_graph

        res = self.client.post(
            f"/script-chat/revert/{self.thread_id}",
            headers=self.auth_headers,
            json={"checkpoint_id": "valid_chk_456"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])
        self.assertIn("reverted to script version 2", res.json()["message"])

    # --- Document Export Endpoints ---

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_export_docx_success(self, mock_get_graph, mock_get_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        mock_state = MagicMock(values={
            "metadata": self.sample_metadata,
            "foss_name": "NumPy",
            "script": self.sample_script,
        })
        mock_get_graph.return_value.aget_state = AsyncMock(return_value=mock_state)

        with patch("src.services.docx_service.json_to_docx") as mock_docx:
            mock_docx.return_value = io.BytesIO(b"fake docx binary")
            res = self.client.get(f"/script-chat/export-docx/{self.thread_id}", headers=self.auth_headers)
            self.assertEqual(res.status_code, 200)
            self.assertIn("wordprocessingml.document", res.headers.get("content-type", ""))

    @patch("src.script_chat.routes.get_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    def test_export_wiki_success(self, mock_get_graph, mock_get_thread):
        mock_get_thread.return_value = {"thread_id": self.thread_id}
        mock_state = MagicMock(values={
            "metadata": self.sample_metadata,
            "foss_name": "NumPy",
            "script": self.sample_script,
        })
        mock_get_graph.return_value.aget_state = AsyncMock(return_value=mock_state)

        with patch("src.services.mediawiki_service.create_mediawiki_script") as mock_wiki:
            mock_wiki.return_value = "{{TutorialScript|NumPy}}"
            res = self.client.get(f"/script-chat/export-wiki/{self.thread_id}", headers=self.auth_headers)
            self.assertEqual(res.status_code, 200)
            self.assertIn("text/plain", res.headers.get("content-type", ""))
            self.assertIn("{{TutorialScript|NumPy}}", res.text)


if __name__ == "__main__":
    unittest.main()
