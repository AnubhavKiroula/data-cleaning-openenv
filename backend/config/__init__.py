"""Application configuration management."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/data_cleaning",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    jwt_secret: str = Field(default="change-me-in-production", validation_alias="JWT_SECRET")
    max_upload_size: int = Field(
        default=100 * 1024 * 1024,
        ge=1,
        validation_alias="MAX_UPLOAD_SIZE",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    environment: str = Field(default="dev", validation_alias="ENVIRONMENT")
    api_port: int = Field(default=8000, ge=1, le=65535, validation_alias="API_PORT")


settings = Settings()
