from __future__ import annotations

from langsmith import traceable

from backend.app.core.config import settings
from backend.app.models.schemas import ComplianceAssessment
from backend.app.prompts import COMPLIANCE_PROMPT
from backend.app.services.llm import StructuredLLM
from backend.app.services.observability import append_audit_event
from backend.app.tools.capability_lookup import query_capability_catalog


class ComplianceAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(COMPLIANCE_PROMPT, ComplianceAssessment)

    @traceable(name='compliance_agent', run_type='chain')
    def run(self, workspace_dir: str, parsed_tender: dict) -> dict:
        rows = query_capability_catalog(parsed_tender['requirements'], settings.case_db_path)
        mandatory_gaps = [row['requirement_id'] for row in rows if row['status'] == 'missing']
        coverage_ratio = 0.0
        if rows:
            fully_met = sum(1 for row in rows if row['status'] == 'fully_met')
            partially_met = sum(1 for row in rows if row['status'] == 'partially_met')
            coverage_ratio = round((fully_met + 0.5 * partially_met) / len(rows), 2)
        assessment = self.chain.invoke(
            task='Produce the final compliance assessment using the evidence-backed match rows.',
            context={
                'tender': parsed_tender,
                'coverage_ratio': coverage_ratio,
                'mandatory_gaps': mandatory_gaps,
                'rows': rows,
                'confidence_notes': [
                    'The matching step is lexical and evidence-based; ambiguous domain synonyms may require reviewer confirmation.'
                ],
            },
        )
        event = append_audit_event(workspace_dir, 'compliance', 'assessment', assessment.model_dump())
        return {
            'compliance': assessment.model_dump(),
            'audit_trail': [event],
        }
