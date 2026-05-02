from __future__ import annotations

from langsmith import traceable

from backend.app.core.config import settings
from backend.app.models.schemas import RiskAssessment
from backend.app.prompts import RISK_PROMPT
from backend.app.services.llm import StructuredLLM
from backend.app.services.observability import append_audit_event
from backend.app.tools.capability_lookup import get_capacity_snapshot
from backend.app.tools.risk_scoring import score_procurement_risk


class RiskAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(RISK_PROMPT, RiskAssessment, agent_name='risk')

    @traceable(name='risk_agent', run_type='chain')
    def run(self, workspace_dir: str, parsed_tender: dict, compliance: dict) -> dict:
        capacity = get_capacity_snapshot(settings.case_db_path)
        scored = score_procurement_risk(parsed_tender, compliance['rows'], capacity)
        assessment = self.chain.invoke(
            task='Convert the deterministic risk signals into a concise bid recommendation and risk register.',
            context={
                'parsed_tender': parsed_tender,
                'compliance': compliance,
                'capacity_snapshot': capacity,
                'scored_signals': scored,
            },
        )
        event = append_audit_event(
            workspace_dir,
            'risk',
            'assessment',
            {'model': self.chain.model_name, 'output': assessment.model_dump()},
        )
        return {
            'risk': assessment.model_dump(),
            'audit_trail': [event],
        }
