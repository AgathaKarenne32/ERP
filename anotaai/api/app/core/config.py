from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ecletica:ecletica@localhost:5432/anotaai"
    secret_key: str = "change-me-anotaai"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ecletica_api_url: str = "http://ecletica-api:8000"

    model_config = SettingsConfigDict(env_prefix="ANOTAAI_")


settings = Settings()
