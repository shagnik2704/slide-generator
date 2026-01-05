"""Google OAuth 2.0 authentication handlers."""
import os
from pathlib import Path
from urllib.parse import urlencode
from fastapi import HTTPException
from dotenv import load_dotenv

# Load .env from project root (3 levels up from src/api/auth/oauth.py)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
ALLOWED_EMAIL_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "@edupyramids.org")

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_google_auth_url(state: str = None) -> str:
    """
    Generate Google OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
    
    Returns:
        Authorization URL string
    """
    if not GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth client ID not configured"
        )
    
    params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    if state:
        params["state"] = state
    
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange authorization code for access token and user info.
    
    Args:
        code: Authorization code from Google OAuth callback
    
    Returns:
        Dictionary with user information (email, name, picture)
    
    Raises:
        HTTPException: If token exchange or user info fetch fails
    """
    import httpx
    
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured"
        )
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        
        if token_response.status_code != 200:
            error_detail = token_response.text
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange code for tokens: {error_detail}"
            )
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="No access token received from Google"
            )
        
        # Get user info
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Failed to fetch user information from Google"
            )
        
        user_info = userinfo_response.json()
        
        # Validate email domain
        email = user_info.get("email")
        if not email:
            raise HTTPException(
                status_code=400,
                detail="No email found in user information"
            )
        
        validate_email_domain(email)
        
        return {
            "email": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }


def validate_email_domain(email: str) -> None:
    """
    Validate that the email belongs to the allowed domain.
    
    Args:
        email: User's email address
    
    Raises:
        HTTPException: If email domain is not allowed
    """
    if not email.endswith(ALLOWED_EMAIL_DOMAIN):
        raise HTTPException(
            status_code=403,
            detail=f"Access restricted to {ALLOWED_EMAIL_DOMAIN} email addresses"
        )
