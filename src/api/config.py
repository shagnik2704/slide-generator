"""Configuration management with environment variable validation."""
import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")


class Settings(BaseModel):
    """Application settings with validation."""
    
    # OAuth Configuration
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://127.0.0.1:8000/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI"
    )
    
    # JWT Configuration
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")
    
    # Email Domain Restriction
    allowed_email_domain: str = Field(
        default="@edupyramids.org",
        alias="ALLOWED_EMAIL_DOMAIN"
    )
    
    # CORS Configuration
    cors_origins: List[str] = Field(default_factory=lambda: ["*"], alias="CORS_ORIGINS")
    frontend_url: str = Field(default="http://127.0.0.1:5173", alias="FRONTEND_URL")
    
    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    
    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key is set and secure."""
        if not v:
            v = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        
        env = os.getenv("ENVIRONMENT", "development")
        if not v or v == "your-secret-key-change-in-production":
            if env == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a secure value in production"
                )
        if v and len(v) < 32 and env == "production":
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        return v
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or '*'."""
        if not v:
            v = os.getenv("CORS_ORIGINS", "*")
        if v == "*":
            return ["*"]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["*"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
    
    class Config:
        """Pydantic config."""
        populate_by_name = True
        case_sensitive = False


# Create settings instance from environment variables
# Note: cors_origins will be parsed by the validator
_settings_dict = {
    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
    "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    "GOOGLE_REDIRECT_URI": os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback"),
    "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
    "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
    "JWT_EXPIRATION_HOURS": int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
    "ALLOWED_EMAIL_DOMAIN": os.getenv("ALLOWED_EMAIL_DOMAIN", "@edupyramids.org"),
    "CORS_ORIGINS": os.getenv("CORS_ORIGINS", "*"),  # Will be parsed to list by validator
    "FRONTEND_URL": os.getenv("FRONTEND_URL", "http://127.0.0.1:5173"),
    "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
    "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
}

settings = Settings(**_settings_dict)
