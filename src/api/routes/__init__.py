"""API routes package."""
from src.api.routes.upload import router as upload_router
from src.api.routes.generation import router as generation_router
from src.api.routes.download import router as download_router

__all__ = ["upload_router", "generation_router", "download_router"]
