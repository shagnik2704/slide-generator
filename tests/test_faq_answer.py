"""Unit tests for FAQ AnswerService and grounding logic."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.faq.answer_service import AnswerService, REFUSAL_MESSAGE
from src.faq.retriever import SearchResult
from src.faq.store import FaqEntry


def _entry(faq_id: str) -> FaqEntry:
    return FaqEntry(
        id=faq_id,
        category="Test Category",
        question=f"Question for {faq_id}?",
        answer=f"Answer for {faq_id}.",
        aliases=[],
    )


def _make_service(top_score: float) -> AnswerService:
    retriever = MagicMock()
    retriever.search.return_value = [
        SearchResult(entry=_entry("test_faq"), score=top_score),
    ]
    service = AnswerService(retriever)
    service._query_rewriter.rewrite = lambda msg, hist: msg
    return service


class FaqAnswerServiceTests(unittest.TestCase):
    def test_high_confidence_uses_llm_synthesis(self):
        service = _make_service(0.9)

        def fake_generate(message, results, history=None):
            return (
                "Master Batch must be uploaded in .csv format only.\n\n"
                "- Use only the required columns\n"
                "- Do not add headers"
            )

        service._generate_answer = fake_generate
        response = service.answer("any question")
        self.assertEqual(response.confidence, "high")
        self.assertIn("csv", response.answer.lower())
        self.assertEqual(response.category, "Test Category")

    def test_low_confidence_returns_refusal(self):
        service = _make_service(0.5)
        service.retriever.search.return_value = [
            SearchResult(entry=_entry("test_faq"), score=0.5),
            SearchResult(entry=_entry("other_faq"), score=0.48),
        ]
        response = service.answer("any question")
        self.assertEqual(response.confidence, "low")
        self.assertEqual(response.answer, REFUSAL_MESSAGE)

    def test_clear_match_with_margin_accepts_below_low_threshold(self):
        service = AnswerService(MagicMock())
        service._query_rewriter.rewrite = lambda msg, hist: msg
        service.retriever.search.return_value = [
            SearchResult(entry=_entry("certificate_minimum_40"), score=0.55),
            SearchResult(entry=_entry("other_faq"), score=0.28),
        ]

        def fake_generate(message, results, history=None):
            return "You need at least 40% on the online assessment to receive the certificate."

        service._generate_answer = fake_generate
        response = service.answer("what is minimum pass score")
        self.assertEqual(response.confidence, "medium")
        self.assertIn("40", response.answer)


class FaqRouteIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_endpoint_calls_answer_and_logs_activity(self):
        from src.api.routes.faq import chat_endpoint, ChatRequest
        from src.faq.answer_service import ChatResponse

        mock_service = MagicMock()
        mock_service.answer.return_value = ChatResponse(
            answer="Test answer",
            confidence="high",
            category="Master Batch",
            sources=[{"id": "test_id", "question": "Test question"}],
        )

        user = SimpleNamespace(sub=str(uuid4()), email="faq_tester@example.com")
        req = ChatRequest(message="How to upload master batch?", history=[])

        with patch("src.api.routes.faq.get_answer_service", return_value=mock_service), \
             patch("src.api.routes.faq.log_activity") as mock_log:
            resp = await chat_endpoint(request=req, current_user=user)
            self.assertEqual(resp.answer, "Test answer")
            self.assertEqual(resp.confidence, "high")
            self.assertEqual(resp.category, "Master Batch")
            self.assertEqual(len(resp.sources), 1)
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            self.assertEqual(call_kwargs["activity_type"], "faq_chat")
            self.assertEqual(call_kwargs["status"], "high")

    async def test_get_categories(self):
        from src.api.routes.faq import get_categories

        mock_retriever = MagicMock()
        mock_retriever.entries = [
            _entry("faq_1"),
            _entry("faq_2"),
        ]
        with patch("src.api.routes.faq.get_faq_retriever", return_value=mock_retriever):
            res = await get_categories()
            self.assertIn("Test Category", res.categories)

    async def test_voice_status(self):
        from src.api.routes.faq import voice_status
        from src.faq.sarvam import SarvamService

        with patch.object(SarvamService, "enabled", new_callable=MagicMock(return_value=True)):
            res = await voice_status()
            self.assertTrue(res.enabled)

    async def test_synthesize_endpoint(self):
        from src.api.routes.faq import synthesize_endpoint, SynthesizeRequest, _sarvam
        from src.faq.sarvam import SarvamService

        req = SynthesizeRequest(text="Hello spoken tutorial")
        with patch.object(SarvamService, "enabled", new_callable=MagicMock(return_value=True)), \
             patch.object(_sarvam, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = ("base64audiodata", "audio/mpeg")
            res = await synthesize_endpoint(req)
            self.assertEqual(res.audio_base64, "base64audiodata")
            self.assertEqual(res.content_type, "audio/mpeg")

    async def test_admin_list_and_update(self):
        from src.api.routes.faq import list_admin_faqs, update_admin_faq, FaqUpdateRequest

        user = SimpleNamespace(sub=str(uuid4()), email="admin@example.com")
        fake_faqs = [_entry("test_faq")]

        with patch("src.api.routes.faq.load_faqs", return_value=fake_faqs), \
             patch("src.api.routes.faq.save_faqs") as mock_save, \
             patch("src.api.routes.faq.get_faq_retriever") as mock_get_retriever:
            mock_retriever = MagicMock()
            mock_get_retriever.return_value = mock_retriever

            listing = await list_admin_faqs(current_user=user)
            self.assertEqual(len(listing), 1)
            self.assertEqual(listing[0].id, "test_faq")

            update_req = FaqUpdateRequest(
                category="Updated Category",
                question="Updated Question?",
                answer="Updated Answer.",
                aliases=["alias1"],
            )
            updated_item = await update_admin_faq("test_faq", update_req, current_user=user)
            self.assertEqual(updated_item.question, "Updated Question?")
            mock_save.assert_called_once()
            mock_retriever.reload.assert_called_once()


if __name__ == "__main__":
    unittest.main()

