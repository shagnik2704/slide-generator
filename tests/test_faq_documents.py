"""Unit and integration tests for FAQ PDF upload and document management."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import fitz  # PyMuPDF

from src.faq.pdf_service import extract_faqs_from_text, extract_text_from_pdf, slugify
from src.faq.store import (
    FaqEntry,
    add_or_replace_document_entries,
    list_documents,
    remove_document,
)


def _make_dummy_pdf() -> bytes:
    """Create a minimal valid PDF in memory using fitz."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Master Batch Guidelines\n\n"
        "Q. What is a Master Batch?\n"
        "Answer: Master Batch is the list of participant students.\n\n"
        "Q. How to download certificates?\n"
        "Answer: Students can download certificates after scoring 40%.\n",
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class FaqDocumentTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Hello World! 123"), "hello_world_123")
        self.assertEqual(slugify("???"), "faq")

    def test_extract_text_from_pdf(self):
        pdf_bytes = _make_dummy_pdf()
        text = extract_text_from_pdf(pdf_bytes)
        self.assertIn("Master Batch Guidelines", text)
        self.assertIn("What is a Master Batch?", text)

    def test_extract_text_from_empty_raises(self):
        with self.assertRaises(ValueError):
            extract_text_from_pdf(b"")

    def test_extract_faqs_from_text_with_mock_llm(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = """{
            "faqs": [
                {
                    "category": "Master Batch",
                    "question": "What is a Master Batch?",
                    "answer": "Master Batch is the participant list.",
                    "aliases": ["participant list", "batch upload"]
                }
            ]
        }"""
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        entries = extract_faqs_from_text("Dummy text", "test_guide.pdf", client=mock_client)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].category, "Master Batch")
        self.assertEqual(entries[0].question, "What is a Master Batch?")
        self.assertEqual(entries[0].source_doc, "test_guide.pdf")

    def test_store_document_lifecycle(self):
        initial = [
            FaqEntry("f1", "Cat1", "Q1?", "A1.", [], source_doc="docA.pdf"),
            FaqEntry("f2", "Cat2", "Q2?", "A2.", [], source_doc="docB.pdf"),
        ]
        with patch("src.faq.store.load_faqs", return_value=list(initial)), \
             patch("src.faq.store.save_faqs") as mock_save, \
             patch("src.faq.store.get_documents_dir") as mock_dir:

            dummy_dir = MagicMock()
            mock_file = MagicMock()
            mock_file.exists.return_value = False
            dummy_dir.__truediv__.return_value = mock_file
            mock_dir.return_value = dummy_dir

            docs = list_documents()
            doc_names = [d["name"] for d in docs]
            self.assertIn("docA.pdf", doc_names)
            self.assertIn("docB.pdf", doc_names)

            # Test removal
            removed = remove_document("docA.pdf")
            self.assertEqual(removed, 1)
            mock_save.assert_called_once()
            saved_entries = mock_save.call_args[0][0]
            self.assertEqual(len(saved_entries), 1)
            self.assertEqual(saved_entries[0].id, "f2")


class FaqDocumentRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_documents_route(self):
        from src.api.routes.faq import list_documents_endpoint

        user = SimpleNamespace(sub=str(uuid4()), email="admin@example.com")
        fake_docs = [{"name": "test.pdf", "entry_count": 5, "is_default": False}]
        with patch("src.api.routes.faq.list_documents", return_value=fake_docs):
            res = await list_documents_endpoint(current_user=user)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0].name, "test.pdf")
            self.assertEqual(res[0].entry_count, 5)

    async def test_delete_document_route(self):
        from src.api.routes.faq import delete_document_endpoint

        user = SimpleNamespace(sub=str(uuid4()), email="admin@example.com")
        mock_retriever = MagicMock()
        with patch("src.api.routes.faq.remove_document", return_value=3), \
             patch("src.api.routes.faq.get_faq_retriever", return_value=mock_retriever), \
             patch("src.api.routes.faq.log_activity"):
            res = await delete_document_endpoint("test.pdf", current_user=user)
            self.assertEqual(res.filename, "test.pdf")
            self.assertEqual(res.entries_removed, 3)
            mock_retriever.reload.assert_called_once()


if __name__ == "__main__":
    unittest.main()
