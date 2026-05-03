from __future__ import annotations

from langchain_core.exceptions import OutputParserException
from langsmith import traceable

from backend.app.models.schemas import TenderSummary
from backend.app.prompts import INTAKE_PROMPT
from backend.app.services.llm import StructuredLLM
from backend.app.services.observability import append_audit_event
from backend.app.tools.document_ingestion import parse_tender_package


class IntakeAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(INTAKE_PROMPT, TenderSummary, agent_name='intake')

    @traceable(name='intake_agent', run_type='chain')
    def run(self, workspace_dir: str, input_paths: list[str]) -> dict:
        parsed = parse_tender_package(input_paths)
        try:
            summary = self.chain.invoke(
                task='Create a normalized tender summary from the extracted local tender package.',
                context=parsed,
            )
            model_name = self.chain.model_name
        except OutputParserException:
            summary = TenderSummary(
                project_title=parsed.get('project_title', 'Unknown project'),
                issuer=parsed.get('issuer', 'Unknown issuer'),
                submission_deadline=parsed.get('submission_deadline'),
                estimated_budget_lkr=parsed.get('estimated_budget_lkr'),
                contract_duration_months=parsed.get('contract_duration_months'),
                requirements=parsed.get('requirements', []),
                evaluation_criteria=parsed.get('evaluation_criteria', []),
                ambiguities=parsed.get('ambiguities', []),
                scope_summary=parsed.get('scope_summary', []),
            )
            model_name = 'fallback-extractor'
        event = append_audit_event(
            workspace_dir,
            'intake',
            'parsed_tender',
            {'model': model_name, 'output': summary.model_dump()},
        )
        return {
            'parsed_tender': summary.model_dump(),
            'audit_trail': [event],
        }
