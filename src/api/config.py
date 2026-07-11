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

    # Persistence
    #
    # Script Chat uses this same PostgreSQL instance for its application metadata
    # and LangGraph checkpoints. Keep credentials out of source control by
    # setting DATABASE_URL in the deployment environment.
    database_url: str = Field(
        default="postgresql://spoken_tutorial:spoken_tutorial@localhost:5432/spoken_tutorial",
        alias="DATABASE_URL",
    )
    database_pool_min_size: int = Field(default=1, ge=1, alias="DATABASE_POOL_MIN_SIZE")
    database_pool_max_size: int = Field(default=5, ge=1, alias="DATABASE_POOL_MAX_SIZE")
    database_pool_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        alias="DATABASE_POOL_TIMEOUT_SECONDS",
    )
    
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
    "DATABASE_URL": os.getenv(
        "DATABASE_URL",
        "postgresql://spoken_tutorial:spoken_tutorial@localhost:5432/spoken_tutorial",
    ),
    "DATABASE_POOL_MIN_SIZE": int(os.getenv("DATABASE_POOL_MIN_SIZE", "1")),
    "DATABASE_POOL_MAX_SIZE": int(os.getenv("DATABASE_POOL_MAX_SIZE", "5")),
    "DATABASE_POOL_TIMEOUT_SECONDS": float(os.getenv("DATABASE_POOL_TIMEOUT_SECONDS", "10")),
}

settings = Settings(**_settings_dict)

if settings.database_pool_max_size < settings.database_pool_min_size:
    raise ValueError("DATABASE_POOL_MAX_SIZE must be greater than or equal to DATABASE_POOL_MIN_SIZE")
