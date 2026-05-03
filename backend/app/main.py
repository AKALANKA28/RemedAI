from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Local multi-agent tender qualification backend powered by LangGraph and Ollama.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
