"""Application configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MediStock Intelligence"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    data_provider: str = "synthetic"
    synthetic_seed: int = 42
    forecast_horizon_days: int = 14
    cache_dir: str = ".cache"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Stockout risk thresholds (days until predicted stockout)
    stockout_critical_days: int = 3
    stockout_high_days: int = 7
    stockout_medium_days: int = 14

    # Expiry risk windows
    expiry_critical_days: int = 0  # already expired
    expiry_high_days: int = 7
    expiry_medium_days: int = 30
    expiry_low_days: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()