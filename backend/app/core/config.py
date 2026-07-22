from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration read from the environment (Pydantic Settings).

    Everything that varies between environments lives here so nothing is
    hardcoded across the codebase. See `.env.example` for the full list.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "E-commerce MVP"
    api_prefix: str = "/api"
    debug: bool = False

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/ecommerce"

    # Auth / JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS — comma-separated list of allowed origins for the local frontend
    cors_origins: str = "http://localhost:4200,http://localhost:80,http://localhost"

    # AI (Anthropic) — the key stays server-side only, never exposed to Angular.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # Seed — run demo-data seeding on first startup
    run_seed: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
