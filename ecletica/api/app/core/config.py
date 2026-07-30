from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ecletica:ecletica@localhost:5432/ecletica"
    secret_key: str = "change-me-ecletica"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    internal_api_token: str = Field(default="change-me-internal-token", alias="INTERNAL_API_TOKEN")
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(env_prefix="ECLETICA_")

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origem.strip() for origem in self.cors_allowed_origins.split(",") if origem.strip()]


settings = Settings()
