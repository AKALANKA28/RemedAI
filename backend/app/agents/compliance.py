from __future__ import annotations

from langsmith import traceable

from backend.app.core.config import settings
from backend.app.models.schemas import ComplianceAssessment
from backend.app.prompts import COMPLIANCE_PROMPT
from backend.app.services.llm import ModelInvocationError, StructuredLLM
from backend.app.services.logging_utils import get_app_logger
from backend.app.services.observability import append_audit_event
from backend.app.tools.capability_lookup import query_capability_catalog

logger = get_app_logger('agent.compliance')


class ComplianceAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(COMPLIANCE_PROMPT, ComplianceAssessment, agent_name='compliance')

    @traceable(name='compliance_agent', run_type='chain')
    def run(self, workspace_dir: str, parsed_tender: dict) -> dict:
        logger.info('Compliance start requirements=%s', len(parsed_tender.get('requirements', [])))
        rows = query_capability_catalog(parsed_tender['requirements'], settings.case_db_path)
        mandatory_gaps = [row['requirement_id'] for row in rows if row['status'] == 'missing']
        coverage_ratio = 0.0
        if rows:
            fully_met = sum(1 for row in rows if row['status'] == 'fully_met')
            partially_met = sum(1 for row in rows if row['status'] == 'partially_met')
            coverage_ratio = round((fully_met + 0.5 * partially_met) / len(rows), 2)
        confidence_notes = [
            'The matching step is lexical and evidence-based; ambiguous domain synonyms may require reviewer confirmation.'
        ]
        try:
            assessment = self.chain.invoke(
                task='Produce the final compliance assessment using the evidence-backed match rows.',
                context={
                    'tender': parsed_tender,
                    'coverage_ratio': coverage_ratio,
                    'mandatory_gaps': mandatory_gaps,
                    'rows': rows,
                    'confidence_notes': confidence_notes,
                },
            )
        except ModelInvocationError as exc:
            logger.warning('Compliance LLM unavailable; using deterministic match rows: %s', exc)
            assessment = ComplianceAssessment(
                coverage_ratio=coverage_ratio,
                mandatory_gaps=mandatory_gaps,
                rows=rows,
                confidence_notes=confidence_notes + ['LLM unavailable; deterministic fallback used.'],
            )
        event = append_audit_event(
            workspace_dir,
            'compliance',
            'assessment',
            {'model': self.chain.model_name, 'output': assessment.model_dump()},
        )
        logger.info('Compliance complete coverage=%s mandatory_gaps=%s', assessment.coverage_ratio, len(assessment.mandatory_gaps))
        return {
            'compliance': assessment.model_dump(),
            'audit_trail': [event],
        }
