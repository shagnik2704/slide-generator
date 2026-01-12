"""Constants used across API routes."""
from pathlib import Path
from typing import List

# File size limits
MAX_FILE_SIZE_MB = 50
MAX_IMAGE_SIZE_MB = 10
MAX_UPLOAD_SIZE_MB = 100

# Allowed file extensions
ALLOWED_SCRIPT_EXTENSIONS: List[str] = ['.json', '.docx', '.odt']
ALLOWED_OUTLINE_EXTENSIONS: List[str] = ['.md', '.docx', '.txt', '.odt']
ALLOWED_IMAGE_EXTENSIONS: List[str] = ['.png', '.jpg', '.jpeg', '.gif', '.webp']

# Directory names
UPLOADS_DIR = "uploads"
OUTPUT_DIR = "output"
STATIC_DIR = "static"
IMAGES_DIR = "images"
AUDIO_DIR = "audio"
VIDEO_DIR = "videos"

# Response messages
MESSAGE_UPLOAD_SUCCESS = "File uploaded successfully"
MESSAGE_PARSE_SUCCESS = "File parsed successfully"
MESSAGE_GENERATION_STARTED = "Generation started"
MESSAGE_VALIDATION_SUCCESS = "Validation passed"
