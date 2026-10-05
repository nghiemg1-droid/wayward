from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./wayward.db"
    secret_key: str
    access_token_expire_minutes: int = 60
    alert_webhook_url: str | None = None
    allow_registration: bool = True

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
