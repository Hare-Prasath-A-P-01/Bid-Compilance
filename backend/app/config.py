import os
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./bidcompliance.db"
    SECRET_KEY: str = "byte-busters-local-development-only-change-in-production-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "./uploads"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # Production security parameters
    SECURE_COOKIES: bool = False
    HSTS_SECONDS: int = 31536000
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # In production, secret must be long and distinct from development defaults
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Enforce strict secret key validation in production
if settings.APP_ENV.lower() == "production":
    if len(settings.SECRET_KEY) < 32 or "development" in settings.SECRET_KEY.lower() or "byte-busters" in settings.SECRET_KEY.lower():
        raise RuntimeError(
            "FATAL: In production (APP_ENV=production), SECRET_KEY must be a cryptographically random "
            "secret of at least 32 characters and cannot use default/development strings."
        )

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def cors_origins() -> List[str]:
    return [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

