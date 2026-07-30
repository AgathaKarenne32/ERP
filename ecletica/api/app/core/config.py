from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ecletica:ecletica@localhost:5432/ecletica"
    secret_key: str = "change-me-ecletica"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    internal_api_token: str = Field(default="change-me-internal-token", alias="INTERNAL_API_TOKEN")

    model_config = SettingsConfigDict(env_prefix="ECLETICA_")


settings = Settings()
