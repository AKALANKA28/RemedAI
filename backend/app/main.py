from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.core.config import settings
from backend.app.services.logging_utils import get_app_logger

logger = get_app_logger('main')

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


@app.on_event('startup')
def log_startup() -> None:
    logger.info('Backend startup project=%s runtime_dir=%s models=%s', settings.project_name, settings.runtime_dir, settings.agent_model_map())
