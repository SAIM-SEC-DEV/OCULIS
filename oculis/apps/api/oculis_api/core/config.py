"""
Central application settings.

Everything configurable lives here and is sourced from environment
variables (see .env.example at the repo root). Nothing in the app should
read os.environ directly outside of this module.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "oculis-api"

    database_url: str = "postgresql+psycopg://oculis:oculis@localhost:5432/oculis"
    redis_url: str = "redis://localhost:6379/0"
    sandbox_url: str = "http://sandbox:9000"

    # Analysis limits (Phase 4+ will actually enforce these; defined now so
    # nothing downstream has to guess at reasonable defaults)
    analysis_timeout_seconds: int = 60
    max_redirects: int = 10
    max_requests_per_analysis: int = 200
    max_response_bytes: int = 1_000_000

    cors_allow_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
