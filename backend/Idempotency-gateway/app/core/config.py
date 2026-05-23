from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "FinSafe Idempotency API"
    version: str = "1.0.0"
    debug: bool = False

    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    redis_url: str = "redis://localhost:6379/0"

    payment_delay_seconds: int = 2
    idempotency_ttl_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def build_redis_url(self) -> "Settings":
        if self.upstash_redis_rest_url and self.upstash_redis_rest_token:
            host = (
                self.upstash_redis_rest_url
                .replace("https://", "")
                .replace("http://", "")
                .rstrip("/")
            )
            self.redis_url = f"rediss://default:{self.upstash_redis_rest_token}@{host}:6379"
        return self


settings = Settings()
