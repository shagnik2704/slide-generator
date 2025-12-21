"""Session management for outline chat."""
import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


def get_session_path(project_id: int) -> Path:
    """Get the session file path for a project."""
    project_root = Path(__file__).parent.parent.parent
    session_dir = project_root / "output" / "outline_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / f"outline_{project_id}.json"


def load_session(project_id: int, default_phase: str = "warmup") -> Tuple[Dict, str, Optional[Dict]]:
    """Load session data from disk."""
    session_path = get_session_path(project_id)
    
    if session_path.exists():
        with open(session_path, "r") as f:
            session_data = json.load(f)
            outline_data = session_data.get("outline_data", {})
            phase = session_data.get("phase", default_phase)
            pending_confirmation = session_data.get("pending_confirmation", None)
            return outline_data, phase, pending_confirmation
    else:
        return {}, default_phase, None


def save_session(project_id: int, outline_data: Dict, phase: str, pending_confirmation: Optional[Dict] = None) -> None:
    """Save session data to disk."""
    session_path = get_session_path(project_id)
    
    with open(session_path, "w") as f:
        json.dump({
            "project_id": project_id,
            "outline_data": outline_data,
            "phase": phase,
            "pending_confirmation": pending_confirmation,
            "updated_at": time.time()
        }, f, indent=2)

