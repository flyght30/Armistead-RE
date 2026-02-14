from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import Settings
from app.api import router as api_router
import logging

logger = logging.getLogger(__name__)
settings = Settings()

app = FastAPI(title="Armistead RE - Transaction Tracker", version="0.1.0")

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
