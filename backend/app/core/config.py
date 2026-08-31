from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved from this file's location (repo_root/backend/app/core/config.py),
# not the process's working directory — env_file="../.env" used to break
# depending on where the app/tests were launched from.
REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

# Where admin-uploaded images (map covers, strategy screenshots) land —
# bind-mounted into the backend container by docker-compose, so files
# written here persist on the host too.
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        # .env carries a couple of infra-only keys (e.g. NGROK_*) that
        # docker-compose needs but the app itself never reads — don't
        # crash Settings() over those.
        extra="ignore",
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

    # AI support assistant (OpenAI-compatible chat completions)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    # Model id sent to the API verbatim. Kept as a setting rather than a
    # constant so it can be repointed without a redeploy — including at a
    # self-hosted or proxied OpenAI-compatible endpoint via openai_base_url.
    ai_agent_model: str = "gpt-4o-mini"
    ai_agent_timeout_seconds: float = 20.0
    # Hard stop on how many times the assistant will speak in one ticket, so
    # a confused exchange can't turn into an endless back-and-forth that
    # buries the actual question from whoever picks the ticket up.
    ai_agent_max_replies_per_thread: int = 3

    # App
    debug: bool = False
    secret_key: str = "change-me"
    environment: str = "development"


settings = Settings()