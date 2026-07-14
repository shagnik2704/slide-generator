"""
Spoken Tutorial Generator API Package.

This package contains the FastAPI application, routes, middleware,
and utilities for the Spoken Tutorial Generator API.
"""

__version__ = "1.0.0"

# Keep package import side-effect free. Route modules import authentication and
# configuration from this package during server construction; importing the app
# eagerly here would re-enter server.py and create a circular import.
def __getattr__(name: str):
    if name == "app":
        from .server import app
        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
