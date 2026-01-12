"""Security utilities and helpers."""
import hashlib
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes (default: 32)
    
    Returns:
        Hexadecimal token string
    """
    return secrets.token_hex(length)


def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
    """Hash sensitive data using SHA-256.
    
    Args:
        data: Data to hash
        salt: Optional salt (if None, generates random salt)
    
    Returns:
        Hexadecimal hash string
    """
    if salt is None:
        salt = generate_secure_token(16)
    
    hash_obj = hashlib.sha256()
    hash_obj.update(f"{salt}{data}".encode('utf-8'))
    return f"{salt}:{hash_obj.hexdigest()}"


def verify_hash(data: str, hash_string: str) -> bool:
    """Verify data against a hash.
    
    Args:
        data: Data to verify
        hash_string: Hash string (format: "salt:hash")
    
    Returns:
        True if data matches hash, False otherwise
    """
    try:
        salt, stored_hash = hash_string.split(':', 1)
        computed_hash = hashlib.sha256(f"{salt}{data}".encode('utf-8')).hexdigest()
        return secrets.compare_digest(computed_hash, stored_hash)
    except (ValueError, AttributeError):
        return False


def sanitize_user_input(input_string: str, max_length: Optional[int] = None) -> str:
    """Sanitize user input to prevent injection attacks.
    
    Args:
        input_string: User input string
        max_length: Maximum allowed length (optional)
    
    Returns:
        Sanitized string
    """
    if not isinstance(input_string, str):
        return ""
    
    # Strip whitespace
    sanitized = input_string.strip()
    
    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')
    
    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.warning(f"Input truncated to {max_length} characters")
    
    return sanitized


class RateLimitTracker:
    """Simple in-memory rate limit tracker (for production, use Redis)."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """Initialize rate limit tracker.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[datetime]] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed.
        
        Args:
            identifier: Unique identifier (e.g., user ID, IP address)
        
        Returns:
            True if request is allowed, False otherwise
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Get or create request list for identifier
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        # Remove old requests outside window
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier]
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self._requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # Record new request
        self._requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier.
        
        Args:
            identifier: Unique identifier
        
        Returns:
            Number of remaining requests
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if identifier not in self._requests:
            return self.max_requests
        
        # Count requests in current window
        recent_requests = [
            req_time for req_time in self._requests[identifier]
            if req_time > window_start
        ]
        
        return max(0, self.max_requests - len(recent_requests))
