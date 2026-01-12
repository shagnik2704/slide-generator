"""Utility functions for API operations."""
import logging
import re
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and other attacks.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename safe for file operations
    """
    # Remove path components
    filename = Path(filename).name
    
    # Remove any non-alphanumeric characters except dots, dashes, underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Prevent hidden files
    if filename.startswith('.'):
        filename = filename[1:]
    
    # Ensure filename is not empty
    if not filename:
        filename = "file"
    
    return filename


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate file extension against allowed list.
    
    Args:
        filename: Filename to validate
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.docx'])
    
    Returns:
        True if extension is allowed, False otherwise
    """
    if not filename:
        return False
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in [ext.lower() for ext in allowed_extensions]


async def validate_upload_file(
    file: UploadFile,
    allowed_extensions: List[str],
    max_size_mb: Optional[int] = None
) -> None:
    """Validate uploaded file.
    
    Args:
        file: Uploaded file
        allowed_extensions: List of allowed extensions
        max_size_mb: Maximum file size in MB (optional)
    
    Raises:
        ValueError: If file validation fails
    """
    if not file.filename:
        raise ValueError("Filename is required")
    
    # Validate extension
    if not validate_file_extension(file.filename, allowed_extensions):
        raise ValueError(
            f"File extension not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size if specified
    if max_size_mb:
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        await file.seek(0)  # Reset file pointer
        
        if file_size_mb > max_size_mb:
            raise ValueError(f"File size exceeds maximum of {max_size_mb}MB")
        
        logger.info(f"File validated: {file.filename} ({file_size_mb:.2f}MB)")


def secure_path_join(base_path: Path, *parts: str) -> Path:
    """Safely join path components, preventing directory traversal.
    
    Args:
        base_path: Base directory path
        *parts: Path components to join
    
    Returns:
        Resolved path within base_path
    
    Raises:
        ValueError: If path escapes base directory
    """
    # Sanitize each part
    sanitized_parts = [sanitize_filename(part) for part in parts]
    
    # Join and resolve
    full_path = base_path.joinpath(*sanitized_parts).resolve()
    base_resolved = base_path.resolve()
    
    # Check if resolved path is within base directory
    try:
        full_path.relative_to(base_resolved)
    except ValueError:
        raise ValueError(f"Path traversal detected: {parts}")
    
    return full_path
