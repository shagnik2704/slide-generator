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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files to serve generated content
static_dir = project_root / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
