"""
Spoken Tutorial Generator API Package.

This package contains the FastAPI application, routes, middleware,
and utilities for the Spoken Tutorial Generator API.
"""

__version__ = "1.0.0"

# Note: Exports are minimal to avoid circular imports
# Export the FastAPI app for easier discovery by uvicorn
from .server import app
