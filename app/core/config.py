from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "WinAudit.MajorERP"
    API_V1_STR: str = "/api/v1"
    APP_PORT: int = 8003
    LOG_LEVEL: str = "INFO"
    DEFAULT_TIMEZONE: str = "America/Guayaquil"
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8080"
    )

    ADMIN_DB_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5444/DbWinAuditAdmin"
    )
    TENANT_DB_PREFIX: str = "DbWinAudit"
    BASE_STORAGE: str = "storage"

    @property
    def base_path(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def storage_path(self) -> Path:
        return self.base_path / self.BASE_STORAGE

    @property
    def logs_path(self) -> Path:
        return self.base_path / "logs"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
