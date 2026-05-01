from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    project_name: str = 'RemedAI'
    ollama_base_url: str = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    ollama_model: str = os.getenv('OLLAMA_MODEL', 'qwen3:8b')
    ollama_temperature: float = float(os.getenv('OLLAMA_TEMPERATURE', '0.1'))
    langsmith_tracing: bool = os.getenv('LANGSMITH_TRACING', 'false').lower() == 'true'
    langsmith_project: str = os.getenv('LANGSMITH_PROJECT', 'ctse-remedai')
    runtime_dir: str = os.getenv('APP_RUNTIME_DIR', 'runtime')
    case_db_path: str = os.getenv('CASE_DB_PATH', 'data/seed/company_knowledge.db')
    checkpoint_db_path: str = os.getenv('CHECKPOINT_DB_PATH', 'runtime/checkpoints/langgraph_state.db')
    allow_langsmith_fallback: bool = os.getenv('ALLOW_LANGSMITH_FALLBACK', 'true').lower() == 'true'

    def ensure_directories(self) -> None:
        Path(self.runtime_dir).mkdir(parents=True, exist_ok=True)
        Path(self.runtime_dir, 'outputs').mkdir(parents=True, exist_ok=True)
        Path(self.runtime_dir, 'checkpoints').mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
