"""Service to extract text from PDFs and structure into FaqEntry items via LLM."""
import json
import logging
import re
from typing import List, Optional

import fitz  # PyMuPDF
from openai import OpenAI

from src.faq.config import settings
from src.faq.store import FaqEntry

logger = logging.getLogger(__name__)

PDF_FAQ_EXTRACTION_SYSTEM_PROMPT = """You are an expert documentation analyst for the Spoken Tutorial Project at IIT Bombay.
Your job is to read the provided text from an official guide, manual, or FAQ document, and extract ALL actionable questions and answers into structured FAQ entries.

Rules:
1. Extract distinct, clear Q&A pairs. If the document has sections with explanations instead of explicit "Q:" markers, convert them into helpful, natural question-and-answer pairs.
2. Maintain technical accuracy: never hallucinate policies, email limits, minimum scores, browser recommendations, or procedures not stated in the source text.
3. Categorize each item into a concise category name (e.g. 'Master Batch', 'Test & Invigilator', 'Certificates', 'Workshop', 'Technical Requirements', 'General').
4. Include 2-4 natural search aliases or keywords for each question (e.g. for "What is the minimum score?", aliases: ["pass marks", "passing percentage", "assessment cutoff"]).
5. Return strictly valid JSON adhering to the following structure:
{
  "faqs": [
    {
      "category": "Category Name",
      "question": "Clear question phrasing?",
      "answer": "Complete, accurate answer as stated in document.",
      "aliases": ["alias 1", "alias 2"]
    }
  ]
}
"""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract clean text content from PDF bytes using PyMuPDF."""
    if not pdf_bytes:
        raise ValueError("PDF content is empty")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            pages_text.append(f"--- Page {page_num + 1} ---\n{text}")

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        raise ValueError("No extractable text found in PDF (it might be a scanned image)")

    return full_text


def slugify(text: str) -> str:
    """Convert text into a clean snake_case identifier."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return slug[:40] if slug else "faq"


def extract_faqs_from_text(
    text: str,
    filename: str,
    client: Optional[OpenAI] = None,
) -> List[FaqEntry]:
    """Parse extracted document text into structured FaqEntry items using OpenAI."""
    api_key = settings.openai_api_key
    openai_client = client or OpenAI(api_key=api_key)

    # Chunk if excessively long (e.g. > 25k chars)
    max_chunk = 25000
    chunks = [text[i : i + max_chunk] for i in range(0, len(text), max_chunk)] if len(text) > max_chunk else [text]

    extracted_entries: List[FaqEntry] = []
    file_slug = slugify(filename.rsplit(".", 1)[0])

    for chunk_idx, chunk in enumerate(chunks):
        user_prompt = f"Source Document: {filename} (Part {chunk_idx + 1}/{len(chunks)})\n\nContent:\n{chunk}"

        response = openai_client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": PDF_FAQ_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw_content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw_content)
            items = parsed.get("faqs", [])
            for item_idx, item in enumerate(items):
                q = item.get("question", "").strip()
                a = item.get("answer", "").strip()
                cat = item.get("category", "General").strip() or "General"
                aliases = [str(x).strip() for x in item.get("aliases", []) if str(x).strip()]

                if not q or not a:
                    continue

                q_slug = slugify(q)
                faq_id = f"{file_slug}_{chunk_idx}_{item_idx}_{q_slug}"

                extracted_entries.append(
                    FaqEntry(
                        id=faq_id,
                        category=cat,
                        question=q,
                        answer=a,
                        aliases=aliases,
                        source_doc=filename,
                    )
                )
        except Exception as exc:
            logger.error("Failed to parse FAQ extraction response: %s", exc)

    return extracted_entries
