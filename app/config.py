"""
Application configuration.

All settings are read from environment variables (or .env file).
This is the single source of truth for configuration — never import
settings from anywhere else.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://smarthome:changeme@db:5432/smarthome",
        alias="DATABASE_URL",
    )
    alembic_database_url: str = Field(
        default="postgresql+psycopg://smarthome:changeme@db:5432/smarthome",
        alias="ALEMBIC_DATABASE_URL",
    )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # ------------------------------------------------------------------
    # JWT Authentication
    # ------------------------------------------------------------------
    secret_key: str = Field(default="CHANGE_ME", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # ------------------------------------------------------------------
    # FRITZ!Box Provider
    # ------------------------------------------------------------------
    fritz_mock_mode: bool = Field(default=True, alias="FRITZ_MOCK_MODE")
    fritz_host: str = Field(default="192.168.178.1", alias="FRITZ_HOST")
    fritz_username: str = Field(default="admin", alias="FRITZ_USERNAME")
    fritz_password: str = Field(default="", alias="FRITZ_PASSWORD")
    fritz_ssl_verify: bool = Field(default=False, alias="FRITZ_SSL_VERIFY")

    # ------------------------------------------------------------------
    # OpenWeatherMap
    # ------------------------------------------------------------------
    openweathermap_api_key: str = Field(default="", alias="OPENWEATHERMAP_API_KEY")
    weather_location_lat: float = Field(default=48.1351, alias="WEATHER_LOCATION_LAT")
    weather_location_lon: float = Field(default=11.5820, alias="WEATHER_LOCATION_LON")
    weather_timezone: str = Field(default="Europe/Berlin", alias="WEATHER_TIMEZONE")

    # ------------------------------------------------------------------
    # Admin seed user
    # ------------------------------------------------------------------
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="changeme", alias="ADMIN_PASSWORD")


settings = Settings()
