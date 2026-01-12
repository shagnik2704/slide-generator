"""
Spoken Tutorial Generator API Package.

This package contains the FastAPI application, routes, middleware,
and utilities for the Spoken Tutorial Generator API.
"""
from src.api.config import settings
from src.api.exceptions import (
    APIException,
    AuthenticationError,
    AuthorizationError,
    InternalServerError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "settings",
    "APIException",
    "AuthenticationError",
    "AuthorizationError",
    "InternalServerError",
    "NotFoundError",
    "ValidationError",
]

__version__ = "1.0.0"
