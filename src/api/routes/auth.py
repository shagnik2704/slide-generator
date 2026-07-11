"""Authentication routes for Google OAuth."""
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import httpx

from src.api.config import settings
from src.api.auth import create_access_token, validate_email_domain, verify_token
from src.api.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    InternalServerError,
)
from src.users.persistence import upsert_user

logger = logging.getLogger(__name__)

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
    if not settings.google_client_id:
        raise InternalServerError(
            "Google OAuth not configured",
            "Please set GOOGLE_CLIENT_ID environment variable",
        )
    
    # Build OAuth URL
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
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
        raise ValidationError("Authorization code not provided")
    
    try:
        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise ValidationError("Failed to obtain access token from Google")
            
            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()
            
            email = user_info.get("email", "")
            name = user_info.get("name", "")
            picture = user_info.get("picture", "")
            provider_subject = user_info.get("id", "")
            
            if not email:
                raise ValidationError("Email not provided by Google")
            if not provider_subject:
                raise ValidationError("Stable account identifier not provided by Google")
            
            # Validate email domain
            if not validate_email_domain(email):
                logger.warning(f"OAuth access denied for email: {email}")
                raise AuthorizationError(
                    f"Email domain must be {settings.allowed_email_domain}"
                )
            
            user = await upsert_user(
                provider="google",
                provider_subject=provider_subject,
                email=email,
                name=name,
                picture=picture,
            )

            # The JWT subject is our stable user UUID. Google identity details
            # remain in the users table and can be refreshed on each login.
            jwt_token = create_access_token(
                subject=str(user["id"]),
                email=user["email"],
                name=user["name"] or "",
                picture=user["picture"] or "",
            )
            
            # Redirect to frontend with token
            redirect_url = f"{settings.frontend_url}/auth/callback?token={jwt_token}"
            
            return RedirectResponse(url=redirect_url)
            
    except (ValidationError, AuthorizationError):
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"OAuth HTTP error: {e.response.text}")
        raise ValidationError("OAuth authentication failed")
    except Exception as e:
        logger.error(f"OAuth error: {str(e)}", exc_info=True)
        raise InternalServerError("Authentication failed")


@router.post("/verify")
async def verify_token_endpoint(request: VerifyTokenRequest):
    """Verify a JWT token and return user info."""
    token_data = verify_token(request.token)
    
    if token_data is None:
        raise AuthenticationError("Invalid or expired token")
    
    # Validate email domain
    if not validate_email_domain(token_data.email):
        raise AuthorizationError("Invalid email domain")
    
    return JSONResponse({
        "valid": True,
        "email": token_data.email,
        "name": token_data.name,
        "picture": token_data.picture,
    })


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal)."""
    return JSONResponse({"message": "Logged out successfully"})
