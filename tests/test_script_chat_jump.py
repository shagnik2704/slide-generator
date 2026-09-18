import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.script_chat.routes import jump_stage, JumpRequest
from src.api.auth import TokenData


class ScriptChatJumpTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_user = TokenData(
            sub="00000000-0000-0000-0000-000000000001",
            email="test@example.com",
            name="Test User",
        )
        self.thread_id = "test-thread-123"

    @patch("src.script_chat.routes.update_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    @patch("src.script_chat.routes._get_owned_state_or_404", new_callable=AsyncMock)
    async def test_jump_to_validation_review_success(
        self, mock_get_state, mock_get_graph, mock_update_thread
    ):
        mock_graph = MagicMock()
        mock_graph.aupdate_state = AsyncMock()
        mock_get_graph.return_value = mock_graph

        mock_state = MagicMock()
        mock_state.values = {"raw_outline": "1. Introduction to Linux"}
        mock_get_state.return_value = mock_state

        req = JumpRequest(target_stage="validation_review")
        result = await jump_stage(self.thread_id, req, self.mock_user)

        self.assertTrue(result["success"])
        mock_graph.aupdate_state.assert_awaited_once_with(
            {"configurable": {"thread_id": self.thread_id}},
            {"current_stage": "grounding"},
            as_node="ground",
        )
        mock_update_thread.assert_awaited_once_with(
            self.thread_id, current_stage="grounding", status="awaiting_review"
        )

    @patch("src.script_chat.routes.get_graph")
    @patch("src.script_chat.routes._get_owned_state_or_404", new_callable=AsyncMock)
    async def test_jump_to_validation_review_missing_outline(self, mock_get_state, mock_get_graph):
        mock_get_graph.return_value = MagicMock()
        mock_state = MagicMock()
        mock_state.values = {}
        mock_get_state.return_value = mock_state

        req = JumpRequest(target_stage="validation_review")
        with self.assertRaises(HTTPException) as ctx:
            await jump_stage(self.thread_id, req, self.mock_user)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("raw outline", ctx.exception.detail)

    @patch("src.script_chat.routes.update_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    @patch("src.script_chat.routes._get_owned_state_or_404", new_callable=AsyncMock)
    async def test_jump_to_script_review_success(
        self, mock_get_state, mock_get_graph, mock_update_thread
    ):
        mock_graph = MagicMock()
        mock_graph.aupdate_state = AsyncMock()
        mock_get_graph.return_value = mock_graph

        mock_state = MagicMock()
        mock_state.values = {
            "script": [{"slide_number": 1, "narration": "Hello"}],
        }
        mock_get_state.return_value = mock_state

        req = JumpRequest(target_stage="script_review")
        result = await jump_stage(self.thread_id, req, self.mock_user)

        self.assertTrue(result["success"])
        mock_graph.aupdate_state.assert_awaited_once_with(
            {"configurable": {"thread_id": self.thread_id}},
            {"current_stage": "generate"},
            as_node="generate",
        )
        mock_update_thread.assert_awaited_once_with(
            self.thread_id, current_stage="review", status="awaiting_review"
        )

    @patch("src.script_chat.routes.update_thread", new_callable=AsyncMock)
    @patch("src.script_chat.routes.get_graph")
    @patch("src.script_chat.routes._get_owned_state_or_404", new_callable=AsyncMock)
    async def test_jump_to_compliance_success(
        self, mock_get_state, mock_get_graph, mock_update_thread
    ):
        mock_graph = MagicMock()
        mock_graph.aupdate_state = AsyncMock()
        mock_get_graph.return_value = mock_graph

        mock_state = MagicMock()
        mock_state.values = {
            "script": [{"slide_number": 1, "narration": "Hello"}],
        }
        mock_get_state.return_value = mock_state

        req = JumpRequest(target_stage="compliance")
        result = await jump_stage(self.thread_id, req, self.mock_user)

        self.assertTrue(result["success"])
        mock_graph.aupdate_state.assert_awaited_once_with(
            {"configurable": {"thread_id": self.thread_id}},
            {"current_stage": "compliance"},
            as_node="script_review",
        )
        mock_update_thread.assert_awaited_once_with(
            self.thread_id, current_stage="compliance", status="running"
        )

    @patch("src.script_chat.routes.get_graph")
    @patch("src.script_chat.routes._get_owned_state_or_404", new_callable=AsyncMock)
    async def test_jump_to_compliance_missing_script(self, mock_get_state, mock_get_graph):
        mock_get_graph.return_value = MagicMock()
        mock_state = MagicMock()
        mock_state.values = {}
        mock_get_state.return_value = mock_state

        req = JumpRequest(target_stage="compliance")
        with self.assertRaises(HTTPException) as ctx:
            await jump_stage(self.thread_id, req, self.mock_user)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("without script", ctx.exception.detail)
