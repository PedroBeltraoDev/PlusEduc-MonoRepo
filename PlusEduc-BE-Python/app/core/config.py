from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PlusEduc API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "pluseduc"
    mongodb_required: bool = False
    mongodb_server_selection_timeout_ms: int = Field(default=2000, ge=50)
    mongodb_connect_timeout_ms: int = Field(default=2000, ge=50)

    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    cors_allow_credentials: bool = True

    jwt_secret: str = ""
    jwt_expiration_ms: int = Field(default=28_800_000, ge=1_000)
    jwt_refresh_expiration_ms: int = Field(default=604_800_000, ge=1_000)

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_api_version: str = "v1"
    gemini_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    gemini_connect_timeout_seconds: float = Field(default=10.0, gt=0.0)
    gemini_read_timeout_seconds: float = Field(default=45.0, gt=0.0)
    ai_demo_fallback_enabled: bool = True

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
