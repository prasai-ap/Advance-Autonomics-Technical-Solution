from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://expense:expense@localhost:5432/expense_claims"
    jwt_secret_key: str = Field(default="local-development-only-change-me", min_length=24)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0, le=15)
    login_max_failures: int = Field(default=5, gt=0)
    login_window_seconds: int = Field(default=60, gt=0)
    database_startup_retries: int = Field(default=10, gt=0)
    database_retry_delay_seconds: float = Field(default=2, ge=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("jwt_algorithm")
    @classmethod
    def only_hs256(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
