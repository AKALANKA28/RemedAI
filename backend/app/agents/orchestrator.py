from __future__ import annotations

from dataclasses import asdict

from langsmith import traceable

from backend.app.core.config import settings
from backend.app.models.schemas import OrchestratorDecision
from backend.app.prompts import ORCHESTRATOR_PROMPT
from backend.app.services.llm import StructuredLLM
from backend.app.services.observability import append_audit_event
from backend.app.tools.case_registry import register_case


class OrchestratorAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(ORCHESTRATOR_PROMPT, OrchestratorDecision)

    @traceable(name='orchestrator_agent', run_type='chain')
    def run(self, user_query: str, input_paths: list[str], case_label: str) -> dict:
        registered = register_case(
            query=user_query,
            input_paths=input_paths,
            runtime_dir=settings.runtime_dir,
            case_label=case_label,
        )
        decision = self.chain.invoke(
            task='Decide whether the tender analysis workflow can proceed.',
            context={
                'user_query': user_query,
                'input_paths': input_paths,
                'registered_case': asdict(registered),
            },
        )
        event = append_audit_event(registered.workspace_dir, 'orchestrator', 'decision', decision.model_dump())
        return {
            'case_id': registered.case_id,
            'workspace_dir': registered.workspace_dir,
            'orchestrator_decision': decision.model_dump(),
            'audit_trail': [event],
        }
