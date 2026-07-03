from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://dataproof:dataproof@localhost:5432/dataproof"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "dataproof"
    minio_secure: bool = False
    deepseek_api_key: str = ""
    log_level: str = "INFO"
    environment: str = "development"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_access_expire_hours: int = 1
    jwt_refresh_expire_days: int = 30

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_lab: str = ""
    app_url: str = "http://localhost:5173"

    # Sentry
    sentry_dsn: str = ""


settings = Settings()
