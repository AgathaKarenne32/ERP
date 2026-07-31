from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ecletica:ecletica@localhost:5432/anotaai"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    ecletica_api_url: str = "http://ecletica-api:8000"
    internal_api_token: str = Field(alias="INTERNAL_API_TOKEN")
    celery_broker_url: str = "redis://redis:6379/0"
    rate_limit_storage_uri: str = "redis://redis:6379/2"
    ifood_webhook_secret: str
    meta_app_secret: str
    meta_verify_token: str
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(env_prefix="ANOTAAI_")

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origem.strip() for origem in self.cors_allowed_origins.split(",") if origem.strip()]


settings = Settings()
