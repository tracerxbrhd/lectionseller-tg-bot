from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "local"
    app_debug: bool = False
    app_log_level: str = "INFO"
    app_secret_key: SecretStr = Field(default=SecretStr("change-me-only-for-local"))
    base_url: str = "http://localhost:8000"
    allowed_hosts: str = "localhost,127.0.0.1"
    miniapp_url: str | None = None
    miniapp_init_data_max_age_seconds: int = 60 * 60 * 24

    bot_token: SecretStr | None = None
    admin_telegram_ids: str = ""

    database_host: str = "postgres"
    database_port: int = 5432
    database_name: str = "lectionseller"
    database_user: str = "lectionseller"
    database_password: SecretStr = Field(default=SecretStr("lectionseller"))
    database_echo: bool = False

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr | None = None

    web_host: str = "0.0.0.0"
    web_port: int = 8000

    yookassa_shop_id: str | None = None
    yookassa_secret_key: SecretStr | None = None
    yookassa_return_url: str = "http://localhost:8000/payments/return"
    yookassa_webhook_allowed_ips: str = ""

    upload_dir: str = "uploads"

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def normalize_admin_telegram_ids(cls, value: object) -> object:
        if value is None:
            return ""
        return value

    @property
    def admin_telegram_id_list(self) -> list[int]:
        if not self.admin_telegram_ids:
            return []
        return [int(item.strip()) for item in self.admin_telegram_ids.split(",") if item.strip()]

    @field_validator("bot_token", "redis_password", "yookassa_secret_key", mode="before")
    @classmethod
    def empty_secret_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("miniapp_url", "yookassa_shop_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @property
    def database_url(self) -> str:
        user = quote_plus(self.database_user)
        password = quote_plus(self.database_password.get_secret_value())
        host = self.database_host
        port = self.database_port
        database = quote_plus(self.database_name)
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    @property
    def redis_url(self) -> str:
        auth = ""
        if self.redis_password is not None:
            password = quote_plus(self.redis_password.get_secret_value())
            auth = f":{password}@"
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def yookassa_enabled(self) -> bool:
        return bool(self.yookassa_shop_id and self.yookassa_secret_key)

    @property
    def yookassa_webhook_allowed_ip_list(self) -> list[str]:
        if not self.yookassa_webhook_allowed_ips:
            return []
        return [
            item.strip()
            for item in self.yookassa_webhook_allowed_ips.split(",")
            if item.strip()
        ]

    @property
    def allowed_host_list(self) -> list[str]:
        if not self.allowed_hosts:
            return []
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

    @property
    def effective_miniapp_url(self) -> str:
        if self.miniapp_url:
            return self.miniapp_url
        return f"{self.base_url.rstrip('/')}/app"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
