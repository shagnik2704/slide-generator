"""Custom middleware for security, logging, and request processing."""
import time
import logging
from typing import Callable
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import JSONResponse

from src.api.config import settings

# Configure logger
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.
    
    Implements security best practices including:
    - Content type protection
    - Clickjacking protection
    - XSS protection
    - Referrer policy
    - HSTS (in production)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Content type protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (restrictive by default)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        
        # HSTS in production only (prevents HTTPS downgrade attacks)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Remove server header for security
        response.headers.pop("Server", None)
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP requests and responses with structured logging.
    
    Provides:
    - Request logging (method, path, client IP)
    - Response logging (status code, processing time)
    - Error logging with full tracebacks
    - Performance metrics (X-Process-Time header)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response with timing information."""
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "query_params": str(request.query_params),
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Determine log level based on status code
            log_level = logging.INFO
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING
            
            # Log response
            logger.log(
                log_level,
                f"← {request.method} {request.url.path} {response.status_code} "
                f"({process_time:.3f}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "client_ip": client_ip,
                }
            )
            
            # Add performance header
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"✗ {request.method} {request.url.path} - Error: {type(e).__name__}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "client_ip": client_ip,
                },
                exc_info=True,
            )
            raise
