"""Helper functions for API routes."""
import time
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get the project root directory.
    
    Returns:
        Path object pointing to project root (3 levels up from src/api/common/)
    """
    return Path(__file__).parent.parent.parent.parent


def ensure_directory_exists(directory: Path) -> Path:
    """Ensure a directory exists, create if it doesn't.
    
    Args:
        directory: Path to directory
    
    Returns:
        Path object to the directory
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def generate_project_id() -> int:
    """Generate a unique project ID based on timestamp.
    
    Returns:
        Integer project ID
    """
    return int(time.time())


def get_output_path(project_id: Optional[int] = None, subdirectory: Optional[str] = None) -> Path:
    """Get output directory path for a project.
    
    Args:
        project_id: Optional project ID
        subdirectory: Optional subdirectory name
    
    Returns:
        Path to output directory
    """
    project_root = get_project_root()
    output_dir = project_root / "output"
    
    if project_id:
        output_dir = output_dir / str(project_id)
    
    if subdirectory:
        output_dir = output_dir / subdirectory
    
    return ensure_directory_exists(output_dir)


def get_upload_path() -> Path:
    """Get upload directory path.
    
    Returns:
        Path to upload directory
    """
    project_root = get_project_root()
    upload_dir = project_root / "uploads"
    return ensure_directory_exists(upload_dir)


def get_static_path() -> Path:
    """Get static files directory path.
    
    Returns:
        Path to static directory
    """
    project_root = get_project_root()
    static_dir = project_root / "static"
    return ensure_directory_exists(static_dir)
