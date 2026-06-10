from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # PostgreSQL
    database_url: str

    # Kafka
    kafka_bootstrap_servers: str
    kafka_transfer_topic: str = "transfers"
    kafka_dlq_topic: str = "transfers.dlq"
    kafka_consumer_group: str = "transfer-consumer-group"

    # Redis
    redis_url: str

    # Worker settings
    outbox_poll_interval_seconds: int = 2
    recovery_job_interval_seconds: int = 60
    reconciliation_job_interval_seconds: int = 300
    stuck_transfer_threshold_minutes: int = 10
    max_transfer_retry_count: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
