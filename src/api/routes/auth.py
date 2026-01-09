"""Authentication routes for Google OAuth."""
import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import httpx

from src.api.auth import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    create_access_token,
    validate_email_domain,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class VerifyTokenRequest(BaseModel):
    """Request model for token verification."""
    token: str


@router.get("/google")
async def google_auth():
    """Initiate Google OAuth flow by redirecting to Google."""
    if not GOOGLE_CLIENT_ID:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Google OAuth not configured",
                "detail": "Please set GOOGLE_CLIENT_ID environment variable. Create a .env file in the project root with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
            }
        )
    
    # Build OAuth URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(code: str):
    """Handle Google OAuth callback and issue JWT token."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided",
        )
    
    try:
        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to obtain access token from Google",
                )
            
            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()
            
            email = user_info.get("email", "")
            name = user_info.get("name", "")
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email not provided by Google",
                )
            
            # Validate email domain
            if not validate_email_domain(email):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Email must be from {os.getenv('ALLOWED_EMAIL_DOMAIN', '@edupyramids.org')} domain",
                )
            
            # Create JWT token
            jwt_token = create_access_token(email=email, name=name)
            
            # Redirect to frontend with token
            frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
            # Remove trailing slash to avoid double slashes
            frontend_url = frontend_url.rstrip('/')
            redirect_url = f"{frontend_url}/auth/callback?token={jwt_token}"
            
            return RedirectResponse(url=redirect_url)
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )


@router.post("/verify")
async def verify_token_endpoint(request: VerifyTokenRequest):
    """Verify a JWT token and return user info."""
    token_data = verify_token(request.token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    # Validate email domain
    if not validate_email_domain(token_data.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid email domain",
        )
    
    return JSONResponse({
        "valid": True,
        "email": token_data.email,
        "name": token_data.name,
    })


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal)."""
    return JSONResponse({"message": "Logged out successfully"})
