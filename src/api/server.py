"""FastAPI application server."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Get project root
project_root = Path(__file__).parent.parent.parent
DB_PATH = str(project_root / "checkpoints.sqlite")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize AsyncSqliteSaver at startup, cleanup at shutdown."""
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        # Store checkpointer in app.state for routes to access
        app.state.checkpointer = checkpointer
        
        # Rebuild graph with checkpointer (lazy import to avoid circular deps)
        from src.core.agent import build_graph
        app.state.graph = build_graph(checkpointer)
        
        print(f"✅ Checkpointer initialized: {DB_PATH}")
        yield
        print("🔒 Checkpointer closed")


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
)

# Include routers
app.include_router(upload_router)
app.include_router(generation_router)
app.include_router(download_router)
app.include_router(outline_chat_router)

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
