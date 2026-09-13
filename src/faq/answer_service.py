"""Grounded answer generation service for Spoken Tutorial FAQ system."""
from dataclasses import dataclass
from typing import Dict, List, Optional

from openai import OpenAI

from src.faq.config import settings
from src.faq.history import HistoryMessage
from src.faq.prompts import ANSWER_USER_TEMPLATE, SYSTEM_PROMPT
from src.faq.query_rewriter import QueryRewriter
from src.faq.retriever import FaqRetriever, SearchResult

REFUSAL_MESSAGE = (
    "I could not find a matching answer in the official Spoken Tutorial FAQ. "
    "Please try rephrasing your question. "
    "For account-specific help, contact your training coordinator or Spoken Tutorial support."
)


@dataclass
class ChatResponse:
    answer: str
    confidence: str
    category: Optional[str]
    sources: List[Dict[str, str]]


class AnswerService:
    def __init__(self, retriever: FaqRetriever) -> None:
        self.retriever = retriever
        self._client: Optional[OpenAI] = None
        self._query_rewriter = QueryRewriter()

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def _format_context(self, results: List[SearchResult]) -> str:
        blocks = []
        for i, result in enumerate(results, start=1):
            entry = result.entry
            blocks.append(
                f"--- Excerpt {i} ({entry.category}) ---\n"
                f"Topic: {entry.question}\n"
                f"Official answer:\n{entry.answer}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _sources_from_results(results: List[SearchResult]) -> List[Dict[str, str]]:
        seen = set()
        sources = []
        for result in results:
            entry = result.entry
            if entry.id in seen:
                continue
            seen.add(entry.id)
            sources.append({"id": entry.id, "question": entry.question})
        return sources

    def _generate_answer(
        self,
        message: str,
        results: List[SearchResult],
        history: List[HistoryMessage],
    ) -> str:
        context = self._format_context(results)
        user_content = ANSWER_USER_TEMPLATE.format(
            context=context,
            question=message,
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in history[-settings.max_history_messages :]:
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": user_content})

        response = self.client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,
            temperature=0.15,
            max_tokens=1024,
        )
        content = response.choices[0].message.content
        return content.strip() if content else REFUSAL_MESSAGE

    @staticmethod
    def _is_clear_match(results: List[SearchResult]) -> bool:
        top = results[0]
        if top.score >= settings.similarity_low:
            return True
        if top.score < settings.similarity_min_absolute:
            return False
        if len(results) < 2:
            return True
        margin = top.score - results[1].score
        return margin >= settings.similarity_margin

    def answer(
        self,
        message: str,
        history: Optional[List[HistoryMessage]] = None,
    ) -> ChatResponse:
        history = history or []
        search_query = self._query_rewriter.rewrite(message, history)
        results = self.retriever.search(
            search_query,
            top_k=settings.retrieval_top_k,
        )

        if not results:
            return ChatResponse(
                answer=REFUSAL_MESSAGE,
                confidence="low",
                category=None,
                sources=[],
            )

        top = results[0]
        sources = self._sources_from_results(results)
        category = top.entry.category

        if not self._is_clear_match(results):
            return ChatResponse(
                answer=REFUSAL_MESSAGE,
                confidence="low",
                category=None,
                sources=sources,
            )

        answer_text = self._generate_answer(message, results, history)
        confidence = "high" if top.score >= settings.similarity_high else "medium"

        return ChatResponse(
            answer=answer_text,
            confidence=confidence,
            category=category,
            sources=sources,
        )
