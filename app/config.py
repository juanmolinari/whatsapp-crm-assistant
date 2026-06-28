from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    strict_zero_cost: bool = True
    database_url: str = "sqlite:///./data/assistant.db"
    storage_path: str = "./data/uploads"
    timezone: str = "America/Argentina/Buenos_Aires"
    daily_summary_time: str = "08:00"
    local_llm_provider: str = "heuristic"
    local_llm_model: str = ""
    local_transcription_provider: str = "simulated"
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    owner_telegram_user_id: str = ""
    whatsapp_enabled: bool = False
    whatsapp_mode: str = "test_only"
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    owner_whatsapp_number: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def storage_dir(self) -> Path:
        return Path(self.storage_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
