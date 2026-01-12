"""Decorators for API routes."""
import functools
import logging
from typing import Callable, Any
from fastapi import Request
from src.api.exceptions import InternalServerError
from src.api.config import settings

logger = logging.getLogger(__name__)


def handle_errors(func: Callable) -> Callable:
    """Decorator to handle errors in route handlers.
    
    Catches exceptions and converts them to appropriate HTTP exceptions
    with proper logging.
    
    Usage:
        @router.post("/endpoint")
        @handle_errors
        async def my_endpoint():
            # Your code here
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Log the error with context
            logger.error(
                f"Error in {func.__name__}: {str(e)}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            
            # Re-raise if it's already an HTTPException
            from fastapi import HTTPException
            if isinstance(e, HTTPException):
                raise
            
            # Convert to internal server error
            raise InternalServerError(
                "An error occurred processing your request",
                include_details=settings.debug if 'settings' in globals() else False,
                details=str(e),
            )
    
    return wrapper


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log execution time of route handlers.
    
    Usage:
        @router.post("/endpoint")
        @log_execution_time
        async def my_endpoint():
            # Your code here
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        import time
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(
                f"{func.__name__} executed in {execution_time:.3f}s",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                }
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.warning(
                f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "error": str(e),
                }
            )
            raise
    
    return wrapper
