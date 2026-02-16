from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@db/ttc"
    redis_url: str = "redis://redis"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    claude_api_key: str = "your_claude_api_key"

    # Phase 2: Email delivery (Resend)
    resend_api_key: str = ""
    resend_webhook_secret: str = ""
    resend_from_email: str = "noreply@armistead.re"

    # Celery
    celery_broker_url: str = ""  # Falls back to redis_url if empty

    # Auth (Clerk)
    clerk_secret_key: str = ""
    clerk_frontend_api: str = ""  # e.g. "clerk.your-app.com" or "your-app.clerk.accounts.dev"

    # Portal (Phase 3)
    portal_base_url: str = "http://localhost:3000"

    @property
    def effective_celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    class Config:
        env_file = ".env"
        env_prefix = ""
