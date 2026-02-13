# Phase 1 — Step 1.1: Project scaffolding & Docker Compose
**Generated:** 2026-02-13T13:01:20.240476

===FILE: docker-compose.yml===
version: '3.9'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db/ttc
      - REDIS_URL=redis://redis
      - MINIO_ENDPOINT=minio
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - CLAUDE_API_KEY=your_claude_api_key
    depends_on:
      - db
      - redis
      - minio

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_BACKEND_URL=http://backend:8000
    depends_on:
      - backend

  db:
    image: postgres:16
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=ttc

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"

volumes:
  db_data:
  redis_data:

===END FILE===

===FILE: backend/requirements.txt===
fastapi[all]
uvicorn
sqlalchemy[asyncpg]
alembic
pydantic-settings
python-multipart
aiofiles
celery
redis
psycopg2-binary
minio
claudia-api-client
tailwindcss
react-email
clerk
===END FILE===

===FILE: backend/app/__init__.py===
# Empty file for now
===END FILE===

===FILE: backend/app/config.py===
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@db/ttc"
    redis_url: str = "redis://redis"
    minio_endpoint: str = "minio"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    clauude_api_key: str = "your_claude_api_key"

    class Config:
        env_file = ".env"
===END FILE===

===FILE: backend/app/main.py===
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import Settings
import logging

settings = Settings()

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include other routes and dependencies here
===END FILE===

===FILE: backend/Dockerfile===
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
===END FILE===

===FILE: .env.example===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ttc
REDIS_URL=redis://redis
MINIO_ENDPOINT=minio
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
CLAUDE_API_KEY=your_claude_api_key
===END FILE===

===FILE: .gitignore===
__pycache__/
*.pyc
node_modules/
dist/
.env
.DS_Store
===END FILE===
