from __future__ import annotations

from dataclasses import asdict

from langsmith import traceable

from backend.app.core.config import settings
from backend.app.models.schemas import OrchestratorDecision
from backend.app.prompts import ORCHESTRATOR_PROMPT
from backend.app.services.llm import ModelInvocationError, StructuredLLM
from backend.app.services.logging_utils import get_app_logger
from backend.app.services.observability import append_audit_event
from backend.app.tools.case_registry import register_case

logger = get_app_logger('agent.orchestrator')


class OrchestratorAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(ORCHESTRATOR_PROMPT, OrchestratorDecision, agent_name='orchestrator')

    @traceable(name='orchestrator_agent', run_type='chain')
    def run(self, user_query: str, input_paths: list[str], case_label: str) -> dict:
        logger.info('Orchestrator start case_label=%s input_files=%s', case_label, len(input_paths))
        registered = register_case(
            query=user_query,
            input_paths=input_paths,
            runtime_dir=settings.runtime_dir,
            case_label=case_label,
        )
        try:
            decision = self.chain.invoke(
                task='Decide whether the tender analysis workflow can proceed.',
                context={
                    'user_query': user_query,
                    'input_paths': input_paths,
                    'registered_case': asdict(registered),
                },
            )
        except ModelInvocationError as exc:
            logger.warning('Orchestrator LLM unavailable; using deterministic fallback: %s', exc)
            decision = OrchestratorDecision(
                objective=user_query,
                route='continue' if input_paths else 'clarify',
                proceed=bool(input_paths),
                rationale=['LLM unavailable; proceeding with fetched local tender files.'],
                required_inputs=[] if input_paths else ['At least one tender document is required.'],
                clarification_questions=[] if input_paths else ['Please provide a tender URL or document.'],
            )
        event = append_audit_event(
            registered.workspace_dir,
            'orchestrator',
            'decision',
            {'model': self.chain.model_name, 'output': decision.model_dump()},
        )
        logger.info('Orchestrator complete case_id=%s proceed=%s', registered.case_id, decision.proceed)
        return {
            'case_id': registered.case_id,
            'workspace_dir': registered.workspace_dir,
            'orchestrator_decision': decision.model_dump(),
            'audit_trail': [event],
        }
