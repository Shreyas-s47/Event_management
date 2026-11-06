from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://event:event_local@localhost:55432/event_management"
    jwt_secret: str = Field(min_length=32)
    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = ["http://localhost:5173"]
    cookie_secure: bool = True
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=7, ge=1, le=30)

    @model_validator(mode="after")
    def secure_production(self):
        if self.environment == "production":
            if not self.cookie_secure or any(
                not x.startswith("https://") for x in self.cors_origins
            ):
                raise ValueError("Production requires secure cookies and HTTPS frontend origins")
        if "*" in self.cors_origins:
            raise ValueError("Credentialed CORS requires explicit origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
