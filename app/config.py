from __future__ import annotations
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    webhook_url: str = Field(default="", alias="WEBHOOK_URL")
    webhook_path: str = Field(default="/telegram/webhook", alias="WEBHOOK_PATH")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")
    port: int = Field(default=10000, alias="PORT")
    bot_username: str = Field(default="", alias="BOT_USERNAME")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-5-mini", alias="OPENAI_CHAT_MODEL")
    openai_transcribe_model: str = Field(default="gpt-4o-mini-transcribe", alias="OPENAI_TRANSCRIBE_MODEL")
    openai_image_model: str = Field(default="gpt-image-1", alias="OPENAI_IMAGE_MODEL")
    default_free_daily_ai: int = Field(default=20, alias="DEFAULT_FREE_DAILY_AI")
    default_pro_daily_ai: int = Field(default=100, alias="DEFAULT_PRO_DAILY_AI")
    default_comfort_daily_ai: int = Field(default=300, alias="DEFAULT_COMFORT_DAILY_AI")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def admin_id_set(self) -> set[int]:
        result: set[int] = set()
        for value in self.admin_ids.split(","):
            value = value.strip()
            if value.isdigit(): result.add(int(value))
        return result

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://"):]
        if url.startswith("postgresql+psycopg2://"):
            return "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]
        return url

@lru_cache
def get_settings() -> Settings:
    return Settings()
