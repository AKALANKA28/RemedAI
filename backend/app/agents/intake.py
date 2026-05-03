from __future__ import annotations

from langsmith import traceable

from backend.app.models.schemas import TenderSummary
from backend.app.prompts import INTAKE_PROMPT
from backend.app.services.llm import ModelInvocationError, StructuredLLM
from backend.app.services.logging_utils import get_app_logger
from backend.app.services.observability import append_audit_event
from backend.app.tools.document_ingestion import parse_tender_package

logger = get_app_logger('agent.intake')


class IntakeAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(INTAKE_PROMPT, TenderSummary, agent_name='intake')

    @traceable(name='intake_agent', run_type='chain')
    def run(self, workspace_dir: str, input_paths: list[str]) -> dict:
        logger.info('Intake start input_files=%s', len(input_paths))
        parsed = parse_tender_package(input_paths)
        try:
            summary = self.chain.invoke(
                task='Create a normalized tender summary from the extracted local tender package.',
                context=parsed,
            )
        except ModelInvocationError as exc:
            logger.warning('Intake LLM unavailable; using deterministic parser output: %s', exc)
            summary = TenderSummary.model_validate(parsed)
        event = append_audit_event(
            workspace_dir,
            'intake',
            'parsed_tender',
            {'model': self.chain.model_name, 'output': summary.model_dump()},
        )
        logger.info('Intake complete title=%s requirements=%s', summary.project_title, len(summary.requirements))
        return {
            'parsed_tender': summary.model_dump(),
            'audit_trail': [event],
        }
