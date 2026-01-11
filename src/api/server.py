"""FastAPI application server."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

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
    app.state.graph = build_graph()
    print("✅ LangGraph agent initialized")
    yield
    print("🔒 Server shutting down")


app = FastAPI(title="Slide Generator API", lifespan=lifespan)

# CORS middleware
# Allow any origin (no credentials used) to avoid preflight failures when
# frontends are served from new hosts or previews.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
)

# Include routers
app.include_router(upload_router)
app.include_router(generation_router)
app.include_router(download_router)
app.include_router(outline_chat_router)
app.include_router(translation_router)

# Basic health/root endpoints for uptime checks
@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
