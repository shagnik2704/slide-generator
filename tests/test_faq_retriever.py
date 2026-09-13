"""Unit and accuracy tests for Spoken Tutorial FAQ retriever."""
import os
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from src.faq.store import FaqEntry, load_faqs
from src.faq.retriever import FaqRetriever

PARAPHRASE_CASES = [
    ("max students in one upload", "master_batch_limit_500"),
    ("same person invigilate and organise", "organiser_invigilator_different"),
    ("minimum marks for certificate", "certificate_minimum_40"),
    ("which browser", "recommended_browser"),
]


class FaqRetrieverTests(unittest.TestCase):
    def test_retriever_search_returns_top_k(self):
        faqs = load_faqs()
        self.assertGreater(len(faqs), 0)
        retriever = FaqRetriever()
        retriever._entries = faqs

        def fake_embed(texts):
            vectors = []
            for text in texts:
                vec = np.zeros(len(faqs), dtype=np.float32)
                lower = text.lower()
                for i, entry in enumerate(faqs):
                    if entry.id in lower or entry.question.lower() in lower:
                        vec[i] = 1.0
                if vec.sum() == 0:
                    vec[0] = 0.1
                vectors.append(vec)
            return np.array(vectors, dtype=np.float32)

        with patch.object(retriever, "_embed", side_effect=fake_embed):
            retriever._vectors = retriever._normalize(
                fake_embed([e.searchable_text() for e in faqs])
            )
            results = retriever.search("master_batch_limit_500", top_k=3)
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0].entry.id, "master_batch_limit_500")

    def test_keyword_score_matching(self):
        entry = FaqEntry(
            id="test_entry",
            category="Master Batch",
            question="What is a Master Batch?",
            answer="Answer here",
            aliases=["participant list", "student list"],
        )
        # Exact alias match gives 1.0
        score = FaqRetriever._keyword_score("where is the participant list?", entry)
        self.assertEqual(score, 1.0)

        # Non-matching gives 0.0
        score_none = FaqRetriever._keyword_score("completely unrelated query", entry)
        self.assertEqual(score_none, 0.0)


if __name__ == "__main__":
    unittest.main()
