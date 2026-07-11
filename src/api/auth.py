"""Authentication utilities for Google OAuth and JWT token handling."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from src.api.config import settings
from src.api.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data."""
    email: str
    name: str
    sub: str  # Stable application user UUID
    picture: str = ""  # Google profile picture URL


def validate_email_domain(email: str) -> bool:
    """Validate that email ends with the allowed domain."""
    if not email:
        return False
    email_lower = email.lower()
    domain_lower = settings.allowed_email_domain.lower()
    return email_lower.endswith(domain_lower)


def create_access_token(subject: str, email: str, name: str, picture: str = "") -> str:
    """Create a JWT access token.
    
    Args:
        subject: Stable user ID assigned by this application
        email: User email address
        name: User display name
        picture: User profile picture URL
    
    Returns:
        Encoded JWT token string
    """
    normalized_subject = str(UUID(subject))
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "sub": normalized_subject,
        "email": email,
        "name": name,
        "picture": picture,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        email: str = payload.get("email")
        name: str = payload.get("name", "")
        sub: str = payload.get("sub")
        picture: str = payload.get("picture", "")
        
        if email is None or sub is None:
            logger.warning("Token missing required fields (email or sub)")
            return None

        try:
            sub = str(UUID(sub))
        except (TypeError, ValueError, AttributeError):
            logger.info("Token uses a legacy non-UUID subject; re-authentication required")
            return None
            
        return TokenData(email=email, name=name, sub=sub, picture=picture)
    except JWTError as e:
        logger.debug(f"Token verification failed: {str(e)}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials from Authorization header
    
    Returns:
        TokenData with user information
    
    Raises:
        AuthenticationError: If token is invalid or expired
        AuthorizationError: If email domain is not allowed
    """
    token = credentials.credentials
    token_data = verify_token(token)
    
    if token_data is None:
        raise AuthenticationError("Invalid or expired token")
    
    # Additional validation: ensure email domain is still valid
    if not validate_email_domain(token_data.email):
        logger.warning(f"Access denied for email: {token_data.email}")
        raise AuthorizationError(
            f"Access denied: Email domain must be {settings.allowed_email_domain}"
        )
    
    return token_data
