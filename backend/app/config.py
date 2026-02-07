"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL: Database connection string. Falls back to SQLite for local dev.
        FITBIT_CLIENT_ID: OAuth2 client ID for the Fitbit Web API.
        FITBIT_CLIENT_SECRET: OAuth2 client secret for the Fitbit Web API.
        FITBIT_REDIRECT_URI: OAuth2 redirect URI registered with Fitbit.
        SECRET_KEY: Secret key used for signing tokens and sessions.
    """

    DATABASE_URL: str = "sqlite:///./health_coach.db"
    FITBIT_CLIENT_ID: str = ""
    FITBIT_CLIENT_SECRET: str = ""
    FITBIT_REDIRECT_URI: str = "http://localhost:8000/api/sync/fitbit/callback"
    SECRET_KEY: str = "change-me-in-production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
