"""Custom exception classes for better error handling."""
import logging
from fastapi import HTTPException, status
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class APIException(HTTPException):
    """Base API exception with consistent structure.
    
    All API exceptions should inherit from this class to ensure
    consistent error response format and proper logging.
    """
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        log_level: int = logging.WARNING,
    ):
        """Initialize API exception.
        
        Args:
            status_code: HTTP status code
            detail: Error message (user-facing)
            error_code: Optional error code for client handling
            headers: Optional HTTP headers
            log_level: Logging level for this exception
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or self.__class__.__name__
        self.log_level = log_level
        self._log_exception()
    
    def _log_exception(self) -> None:
        """Log the exception at appropriate level."""
        message = f"{self.error_code}: {self.detail}"
        logger.log(self.log_level, message)


class ValidationError(APIException):
    """Validation error (400)."""
    
    def __init__(self, detail: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code,
        )


class AuthenticationError(APIException):
    """Authentication error (401)."""
    
    def __init__(self, detail: str = "Authentication required", error_code: str = "AUTH_REQUIRED"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(APIException):
    """Authorization error (403)."""
    
    def __init__(self, detail: str = "Access denied", error_code: str = "FORBIDDEN"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code,
        )


class NotFoundError(APIException):
    """Not found error (404)."""
    
    def __init__(self, resource: str = "Resource", error_code: str = "NOT_FOUND"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
            error_code=error_code,
        )


class InternalServerError(APIException):
    """Internal server error (500)."""
    
    def __init__(
        self,
        detail: str = "An internal error occurred",
        error_code: str = "INTERNAL_ERROR",
        include_details: bool = False,
        details: Optional[str] = None,
    ):
        """Initialize internal server error.
        
        Args:
            detail: User-facing error message
            error_code: Error code for logging
            include_details: Whether to include technical details (only in dev)
            details: Technical error details
        """
        # Only include technical details in development
        if include_details and details:
            detail = f"{detail}: {details}"
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code,
        )
