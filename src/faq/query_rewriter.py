"""Contextual search query rewriting using conversation history."""
from typing import List, Optional
from openai import OpenAI

from src.faq.config import settings
from src.faq.history import HistoryMessage, build_search_query
from src.faq.prompts import QUERY_REWRITE_PROMPT


class QueryRewriter:
    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def rewrite(self, message: str, history: List[HistoryMessage]) -> str:
        if not history:
            return message

        messages = [
            {"role": "system", "content": QUERY_REWRITE_PROMPT},
        ]
        for item in history[-8:]:
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": message})

        try:
            response = self.client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=messages,
                temperature=0,
                max_tokens=80,
            )
            rewritten = response.choices[0].message.content
            if rewritten and rewritten.strip():
                return rewritten.strip()
        except Exception:
            pass

        return build_search_query(message, history)
