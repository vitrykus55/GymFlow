from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "GymFlow API"
    version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://gymflow:gymflow@localhost:5432/gymflow"

    # Comma-separated list, e.g. "http://localhost:3000,https://gymflow.app"
    backend_cors_origins: str = "http://localhost:3000"

    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        return value

    @model_validator(mode="after")
    def require_jwt_secret_key_in_production(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret_key is None:
            raise ValueError("JWT_SECRET_KEY must be configured in production.")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
