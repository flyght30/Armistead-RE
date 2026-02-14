from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@db/ttc"
    redis_url: str = "redis://redis"
    minio_endpoint: str = "minio"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    claude_api_key: str = "your_claude_api_key"

    class Config:
        env_file = ".env"
        env_prefix = ""
