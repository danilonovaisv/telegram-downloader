import logging

from dotenv import load_dotenv
from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    BOT_TOKEN: str
    TELEGRAM_LOCAL: bool = False
    LOCAL_BOT_API_URL: str | None = None
    BOT_API_DIR: str | None = None
    DOWNLOAD_TO_DIR: str
    USER_ID: str
    CHAT_ID: str

    @model_validator(mode="after")
    def validate_local_bot_api_settings(self) -> "Settings":
        if self.TELEGRAM_LOCAL:
            if not self.LOCAL_BOT_API_URL:
                raise ValueError(
                    "LOCAL_BOT_API_URL must be set when TELEGRAM_LOCAL is True"
                )
            if not self.BOT_API_DIR:
                raise ValueError(
                    "BOT_API_DIR must be set when TELEGRAM_LOCAL is True"
                )
        return self


logger.info("Loading environment variables")

try:
    env = Settings()
except ValidationError as e:
    logger.error("Environment variables validation error: %s", e)
    exit(1)
