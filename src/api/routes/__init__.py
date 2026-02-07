"""
API Routes Package.

Centralized exports for all route routers.
"""
from src.api.routes.upload import router as upload_router
from src.api.routes.generation import router as generation_router
from src.api.routes.download import router as download_router
from src.api.routes.outline_chat import router as outline_chat_router
from src.api.routes.translation import router as translation_router
from src.api.routes.redesign import router as redesign_router
from src.api.routes.timed_script import router as timed_script_router
from src.api.routes.slides_translation import router as slides_translation_router

__all__ = [
    "upload_router",
    "generation_router",
    "download_router",
    "outline_chat_router",
    "translation_router",
    "redesign_router",
    "timed_script_router",
    "slides_translation_router",
]

