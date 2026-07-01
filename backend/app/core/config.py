from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://stratmaster:changeme@db:5432/stratmaster_db"
    postgres_user: str = "stratmaster"
    postgres_password: str = "changeme"
    postgres_db: str = "stratmaster_db"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_host: str = "redis"
    redis_port: int = 6379

    # Telegram Bot
    bot_token: str = ""
    webhook_secret: str = ""
    webapp_url: str = ""

    # CryptoPay
    cryptopay_token: str = ""
    cryptopay_webhook_secret: str = ""

    # App
    debug: bool = False
    secret_key: str = "change-me"
    environment: str = "development"


settings = Settings()