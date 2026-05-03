from __future__ import annotations

from langsmith import traceable

from backend.app.core.config import settings
from backend.app.models.schemas import RiskAssessment
from backend.app.prompts import RISK_PROMPT
from backend.app.services.llm import ModelInvocationError, StructuredLLM
from backend.app.services.logging_utils import get_app_logger
from backend.app.services.observability import append_audit_event
from backend.app.tools.capability_lookup import get_capacity_snapshot
from backend.app.tools.risk_scoring import score_procurement_risk

logger = get_app_logger('agent.risk')


class RiskAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(RISK_PROMPT, RiskAssessment, agent_name='risk')

    @traceable(name='risk_agent', run_type='chain')
    def run(self, workspace_dir: str, parsed_tender: dict, compliance: dict) -> dict:
        logger.info('Risk start rows=%s', len(compliance.get('rows', [])))
        capacity = get_capacity_snapshot(settings.case_db_path)
        scored = score_procurement_risk(parsed_tender, compliance['rows'], capacity)
        try:
            assessment = self.chain.invoke(
                task='Convert the deterministic risk signals into a concise bid recommendation and risk register.',
                context={
                    'parsed_tender': parsed_tender,
                    'compliance': compliance,
                    'capacity_snapshot': capacity,
                    'scored_signals': scored,
                },
            )
        except ModelInvocationError as exc:
            logger.warning('Risk LLM unavailable; using deterministic risk score: %s', exc)
            assessment = RiskAssessment.model_validate(scored)
        event = append_audit_event(
            workspace_dir,
            'risk',
            'assessment',
            {'model': self.chain.model_name, 'output': assessment.model_dump()},
        )
        logger.info('Risk complete recommendation=%s overall=%s', assessment.recommendation, assessment.overall_risk)
        return {
            'risk': assessment.model_dump(),
            'audit_trail': [event],
        }
