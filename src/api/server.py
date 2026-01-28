"""FastAPI application server."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.config import settings
from src.api.exceptions import APIException
from src.api.middleware import SecurityHeadersMiddleware, LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get project root
project_root = Path(__file__).parent.parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the LangGraph agent at startup."""
    # Initialize DB
    from src.services.database import init_db
    init_db()
    print("✅ Database initialized")
    
    from src.core.agent import build_graph
    logger.info("Initializing LangGraph agent...")
    app.state.graph = build_graph()
    logger.info("✅ LangGraph agent initialized")
    yield
    logger.info("🔒 Server shutting down")



app = FastAPI(
    title="Spoken Tutorial Generator API",
    description="Professional API for generating Spoken Tutorial educational content with advanced security",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

Instrumentator().instrument(app).expose(app)


# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add logging middleware (only in development or if debug is enabled)
if settings.debug or settings.is_development:
    app.add_middleware(LoggingMiddleware)

# CORS middleware - more restrictive in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
    max_age=86400,
)

# Mount static files to serve generated content
# Use check_dir=False so the app can start even if the directory
# doesn't exist yet on the deployment filesystem.
static_dir = project_root / "static"
app.mount("/static", StaticFiles(directory=str(static_dir), check_dir=False), name="static")

# Mount output directory to serve audio files
output_dir = project_root / "output"
output_dir.mkdir(exist_ok=True)  # Ensure it exists
app.mount("/output", StaticFiles(directory=str(output_dir), check_dir=False), name="output")

# Import routers after app is created (they will use app.state.graph)
from src.api.routes import (
    upload_router,
    generation_router,
    download_router,
    outline_chat_router,
    translation_router,
    timed_script_router,
)
from src.api.routes.auth import router as auth_router

# Include routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(generation_router)
app.include_router(download_router)
app.include_router(outline_chat_router)
app.include_router(translation_router)
app.include_router(timed_script_router)

# Global exception handler for API exceptions
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions with consistent format."""
    headers = exc.headers if hasattr(exc, 'headers') and exc.headers else {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "error_code": exc.error_code,
            "detail": exc.detail,
        },
        headers=headers,
    )


# Global exception handler for general exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "error_code": "INTERNAL_ERROR",
            "detail": "An internal error occurred. Please try again later.",
        },
    )


# Basic health/root endpoints for uptime checks
@app.get("/")
def root():
    """Root endpoint."""
    return {"status": "ok", "service": "Spoken Tutorial Generator API", "version": "1.0.0"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "service": "Spoken Tutorial Generator API",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
