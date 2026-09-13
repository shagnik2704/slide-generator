"""API endpoints for Spoken Tutorial FAQ Chatbot, Voice STT/TTS, and Admin CRUD."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.activity.tracker import log_activity
from src.api.auth import TokenData, get_current_user
from src.faq.answer_service import AnswerService
from src.faq.history import HistoryMessage
from src.faq.retriever import FaqRetriever
from src.faq.sarvam import SarvamError, SarvamService
from src.faq.store import FaqEntry, load_faqs, save_faqs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faq", tags=["faq"])

_retriever: Optional[FaqRetriever] = None
_answer_service: Optional[AnswerService] = None
_sarvam: SarvamService = SarvamService()


def get_faq_retriever() -> FaqRetriever:
    global _retriever
    if _retriever is None:
        _retriever = FaqRetriever()
    return _retriever


def get_answer_service() -> AnswerService:
    global _retriever, _answer_service
    if _answer_service is None:
        if _retriever is None:
            _retriever = FaqRetriever()
        _answer_service = AnswerService(_retriever)
    return _answer_service


def set_answer_service(service: Optional[AnswerService]) -> None:
    global _answer_service
    _answer_service = service


# ==========================================
# Pydantic Request / Response Models
# ==========================================

class HistoryItem(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: List[HistoryItem] = Field(default_factory=list, max_length=20)


class SourceItem(BaseModel):
    id: str
    question: str


class ChatResponseModel(BaseModel):
    answer: str
    confidence: str
    category: Optional[str] = None
    sources: List[SourceItem]


class CategoriesResponse(BaseModel):
    categories: List[str]


class VoiceStatusResponse(BaseModel):
    enabled: bool


class TranscribeResponse(BaseModel):
    transcript: str


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class SynthesizeResponse(BaseModel):
    audio_base64: str
    content_type: str


class FaqItemModel(BaseModel):
    id: str
    category: str
    question: str
    answer: str
    aliases: List[str] = Field(default_factory=list)


class FaqUpdateRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=120)
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1, max_length=8000)
    aliases: List[str] = Field(default_factory=list, max_length=20)


def _to_model(entry: FaqEntry) -> FaqItemModel:
    return FaqItemModel(
        id=entry.id,
        category=entry.category,
        question=entry.question,
        answer=entry.answer,
        aliases=entry.aliases,
    )


# ==========================================
# Chat & Categories Endpoints
# ==========================================

@router.post("/chat", response_model=ChatResponseModel)
async def chat_endpoint(
    request: ChatRequest,
    current_user: Optional[TokenData] = Depends(get_current_user),
) -> ChatResponseModel:
    """Answer a user question grounded in official Spoken Tutorial FAQs."""
    service = get_answer_service()
    history = [
        HistoryMessage(role=item.role, content=item.content.strip())
        for item in request.history[-20:]
    ]

    result = service.answer(request.message.strip(), history=history)

    # Observability: Log query to PostgreSQL for Grafana dashboards
    user_id = getattr(current_user, "sub", None) if current_user else None
    email = getattr(current_user, "email", None) if current_user else None
    log_activity(
        user_id=user_id,
        email=email,
        activity_type="faq_chat",
        detail=request.message.strip()[:100],
        status=result.confidence,
        metadata={"category": result.category, "sources_count": len(result.sources)},
    )

    return ChatResponseModel(
        answer=result.answer,
        confidence=result.confidence,
        category=result.category,
        sources=[SourceItem(**source) for source in result.sources],
    )


@router.get("/categories", response_model=CategoriesResponse)
async def get_categories() -> CategoriesResponse:
    """Return all unique FAQ categories."""
    retriever = get_faq_retriever()
    categories_set = set(entry.category for entry in retriever.entries)
    return CategoriesResponse(categories=sorted(categories_set))


# ==========================================
# Voice STT / TTS Endpoints (Sarvam AI)
# ==========================================

@router.get("/voice/status", response_model=VoiceStatusResponse)
async def voice_status() -> VoiceStatusResponse:
    """Return whether voice capability (Sarvam AI key) is enabled."""
    return VoiceStatusResponse(enabled=_sarvam.enabled)


@router.post("/voice/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(file: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe uploaded user speech audio into text via Sarvam STT."""
    if not _sarvam.enabled:
        raise HTTPException(
            status_code=503,
            detail="Voice input is not configured. Set SARVAM_API_KEY in environment variables.",
        )

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(audio) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large (max 10 MB)")

    content_type = file.content_type or "audio/webm"
    filename = file.filename or "recording.webm"

    try:
        transcript = await _sarvam.transcribe(
            audio,
            filename=filename,
            content_type=content_type,
        )
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranscribeResponse(transcript=transcript)


@router.post("/voice/synthesize", response_model=SynthesizeResponse)
async def synthesize_endpoint(body: SynthesizeRequest) -> SynthesizeResponse:
    """Synthesize bot answer text to natural speech audio via Sarvam TTS."""
    if not _sarvam.enabled:
        raise HTTPException(
            status_code=503,
            detail="Voice output is not configured. Set SARVAM_API_KEY in environment variables.",
        )

    try:
        audio_base64, content_type = await _sarvam.synthesize(body.text)
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SynthesizeResponse(
        audio_base64=audio_base64,
        content_type=content_type,
    )


# ==========================================
# Admin FAQ CRUD Endpoints
# ==========================================

@router.get("/admin/list", response_model=List[FaqItemModel])
async def list_admin_faqs(
    current_user: TokenData = Depends(get_current_user),
) -> List[FaqItemModel]:
    """List all FAQ items for admin editing."""
    return [_to_model(entry) for entry in load_faqs()]


@router.put("/admin/{faq_id}", response_model=FaqItemModel)
async def update_admin_faq(
    faq_id: str,
    request: FaqUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
) -> FaqItemModel:
    """Update a specific FAQ item and trigger instant in-memory re-indexing."""
    entries = load_faqs()
    index = next((i for i, entry in enumerate(entries) if entry.id == faq_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="FAQ entry not found")

    updated = FaqEntry(
        id=faq_id,
        category=request.category.strip(),
        question=request.question.strip(),
        answer=request.answer.strip(),
        aliases=[alias.strip() for alias in request.aliases if alias.strip()],
    )
    entries[index] = updated
    save_faqs(entries)

    # Instant in-memory re-index
    retriever = get_faq_retriever()
    retriever.reload()

    return _to_model(updated)
