"""In-memory and JSON persistence for Spoken Tutorial FAQ items."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.faq.config import settings


@dataclass(frozen=True)
class FaqEntry:
    id: str
    category: str
    question: str
    answer: str
    aliases: List[str]
    source_doc: Optional[str] = None

    def searchable_text(self) -> str:
        alias_text = " ".join(self.aliases)
        return f"{self.category}. {self.question} {alias_text}"


def load_faqs(path: Optional[Path] = None) -> List[FaqEntry]:
    """Load FAQ entries from JSON storage."""
    faq_path = path or settings.faqs_path
    if not faq_path.exists():
        bundled = Path(__file__).resolve().parent / "data" / "spoken_tutorial_faqs.json"
        if bundled.exists():
            faq_path = bundled

    with open(faq_path, encoding="utf-8") as f:
        raw = json.load(f)

    return [
        FaqEntry(
            id=item["id"],
            category=item["category"],
            question=item["question"],
            answer=item["answer"],
            aliases=item.get("aliases", []),
            source_doc=item.get("source_doc"),
        )
        for item in raw
    ]


def save_faqs(entries: List[FaqEntry], path: Optional[Path] = None) -> None:
    """Save FAQ entries to JSON storage."""
    faq_path = path or settings.faqs_path
    if not faq_path.parent.exists():
        faq_path.parent.mkdir(parents=True, exist_ok=True)

    payload = [
        {
            "id": entry.id,
            "category": entry.category,
            "question": entry.question,
            "answer": entry.answer,
            "aliases": entry.aliases,
            "source_doc": entry.source_doc,
        }
        for entry in entries
    ]
    with open(faq_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_documents_dir() -> Path:
    """Directory to store uploaded FAQ PDF documents."""
    docs_dir = settings.faqs_path.parent / "faq_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir


def list_documents() -> List[dict]:
    """Return summary of all indexed source documents."""
    entries = load_faqs()
    doc_counts: dict[str, int] = {}
    for entry in entries:
        doc = entry.source_doc or "Default Corpus (BOT-FAQs.pdf)"
        doc_counts[doc] = doc_counts.get(doc, 0) + 1

    docs_dir = get_documents_dir()
    results = []
    for doc_name, count in doc_counts.items():
        file_path = docs_dir / doc_name
        size_bytes = file_path.stat().st_size if file_path.exists() else None
        modified_at = file_path.stat().st_mtime if file_path.exists() else None
        results.append({
            "name": doc_name,
            "entry_count": count,
            "is_default": doc_name == "Default Corpus (BOT-FAQs.pdf)",
            "size_bytes": size_bytes,
            "modified_at": modified_at,
        })
    return results


def remove_document(doc_name: str) -> int:
    """Remove all FAQ entries associated with a document and delete the file if stored."""
    entries = load_faqs()
    is_default = (doc_name == "Default Corpus (BOT-FAQs.pdf)")
    retained = []
    removed_count = 0
    for entry in entries:
        matches = (entry.source_doc == doc_name) or (is_default and not entry.source_doc)
        if matches:
            removed_count += 1
        else:
            retained.append(entry)

    if removed_count > 0:
        save_faqs(retained)

    docs_dir = get_documents_dir()
    file_path = docs_dir / doc_name
    if file_path.exists():
        file_path.unlink()

    return removed_count


def add_or_replace_document_entries(doc_name: str, new_entries: List[FaqEntry]) -> None:
    """Add or replace all entries for a given source document."""
    entries = load_faqs()
    retained = [e for e in entries if e.source_doc != doc_name]
    retained.extend(new_entries)
    save_faqs(retained)


