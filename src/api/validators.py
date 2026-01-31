"""Input validation utilities."""
import re
from typing import Optional
from pydantic import BaseModel, field_validator, ValidationError


class EmailValidator:
    """Email validation utility."""
    
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format.
        
        Args:
            email: Email address to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        return bool(cls.EMAIL_PATTERN.match(email.strip().lower()))
    
    @classmethod
    def validate_domain(cls, email: str, allowed_domain: str) -> bool:
        """Validate email domain.
        
        Args:
            email: Email address
            allowed_domain: Allowed domain (e.g., '@edupyramids.org')
        
        Returns:
            True if domain matches, False otherwise
        """
        if not cls.validate_email(email):
            return False
        
        email_lower = email.lower()
        domain_lower = allowed_domain.lower()
        return email_lower.endswith(domain_lower)


def validate_pagination(page: int, page_size: int, max_page_size: int = 100) -> tuple[int, int]:
    """Validate and normalize pagination parameters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        max_page_size: Maximum allowed page size
    
    Returns:
        Tuple of (normalized_page, normalized_page_size)
    
    Raises:
        ValueError: If pagination parameters are invalid
    """
    if page < 1:
        raise ValueError("Page must be >= 1")
    
    if page_size < 1:
        raise ValueError("Page size must be >= 1")
    
    if page_size > max_page_size:
        raise ValueError(f"Page size cannot exceed {max_page_size}")
    
    return page, page_size


def validate_project_id(project_id: Optional[int]) -> int:
    """Validate project ID.
    
    Args:
        project_id: Project ID to validate
    
    Returns:
        Validated project ID
    
    Raises:
        ValueError: If project ID is invalid
    """
    if project_id is None:
        raise ValueError("Project ID is required")
    
    if not isinstance(project_id, int) or project_id < 0:
        raise ValueError("Project ID must be a non-negative integer")
    
    return project_id
