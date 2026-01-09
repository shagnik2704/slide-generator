"""Authentication utilities for Google OAuth and JWT token handling."""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

# Load environment variables from .env file
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Email Domain Restriction
ALLOWED_EMAIL_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "@edupyramids.org")

# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data."""
    email: str
    name: str
    sub: str


def validate_email_domain(email: str) -> bool:
    """Validate that email ends with the allowed domain."""
    if not email:
        return False
    email_lower = email.lower()
    domain_lower = ALLOWED_EMAIL_DOMAIN.lower()
    return email_lower.endswith(domain_lower)


def create_access_token(email: str, name: str) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": email,
        "email": email,
        "name": name,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("email")
        name: str = payload.get("name", "")
        sub: str = payload.get("sub")
        
        if email is None or sub is None:
            return None
            
        return TokenData(email=email, name=name, sub=sub)
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Dependency to get current authenticated user from JWT token."""
    token = credentials.credentials
    token_data = verify_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Additional validation: ensure email domain is still valid
    if not validate_email_domain(token_data.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid email domain",
        )
    
    return token_data
