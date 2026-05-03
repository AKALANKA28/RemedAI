from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _split_env_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(',') if item.strip()]


@dataclass(slots=True)
class Settings:
    project_name: str = 'RemedAI'
    ollama_base_url: str = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    ollama_temperature: float = float(os.getenv('OLLAMA_TEMPERATURE', '0.1'))
    ollama_context_length: int = int(os.getenv('OLLAMA_CONTEXT_LENGTH', '2048'))
    ollama_keep_alive: str | int = os.getenv('OLLAMA_KEEP_ALIVE', '0')

    # Default model used by every agent unless an agent-specific override is set.
    ollama_model: str = os.getenv('OLLAMA_MODEL', 'phi3:mini')

    # Optional per-agent local Ollama model overrides.
    orchestrator_model: str = os.getenv('OLLAMA_ORCHESTRATOR_MODEL', ollama_model)
    intake_model: str = os.getenv('OLLAMA_INTAKE_MODEL', ollama_model)
    compliance_model: str = os.getenv('OLLAMA_COMPLIANCE_MODEL', ollama_model)
    risk_model: str = os.getenv('OLLAMA_RISK_MODEL', ollama_model)
    planner_model: str = os.getenv('OLLAMA_PLANNER_MODEL', ollama_model)
    ollama_fallback_models: list[str] = field(
        default_factory=lambda: _split_env_list(os.getenv('OLLAMA_FALLBACK_MODELS', ''))
    )

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

    def agent_model_map(self) -> dict[str, str]:
        """Return the local Ollama model assigned to each RemedAI agent."""
        return {
            'orchestrator': self.orchestrator_model,
            'intake': self.intake_model,
            'compliance': self.compliance_model,
            'risk': self.risk_model,
            'planner': self.planner_model,
        }

    def model_for_agent(self, agent_name: str) -> str:
        """Resolve the configured Ollama model for an agent name."""
        return self.agent_model_map().get(agent_name, self.ollama_model)


settings = Settings()
settings.ensure_directories()
