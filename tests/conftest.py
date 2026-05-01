from __future__ import annotations

from typing import Any

import pytest

from backend.app.models.schemas import (
    ComplianceAssessment,
    ComplianceRow,
    OrchestratorDecision,
    PlanTask,
    RiskAssessment,
    RiskItem,
    SubmissionPlan,
    TenderRequirement,
    TenderSummary,
)
from backend.app.services.llm import StructuredLLM


def _fake_invoke(self: StructuredLLM, task: str, context: dict[str, Any]):
    model_name = self.output_model.__name__
    if model_name == 'OrchestratorDecision':
        return OrchestratorDecision(
            objective=context.get('user_query', 'Assess the tender'),
            route='continue',
            proceed=True,
            rationale=['Required tender files are present and the workflow can proceed.'],
            required_inputs=context.get('input_paths', []),
            clarification_questions=[],
        )
    if model_name == 'TenderSummary':
        requirements = [TenderRequirement(**item) for item in context.get('requirements', [])]
        return TenderSummary(
            project_title=context.get('project_title', 'Unknown project'),
            issuer=context.get('issuer', 'Unknown issuer'),
            submission_deadline=context.get('submission_deadline'),
            estimated_budget_lkr=context.get('estimated_budget_lkr'),
            contract_duration_months=context.get('contract_duration_months'),
            requirements=requirements,
            evaluation_criteria=context.get('evaluation_criteria', []),
            ambiguities=context.get('ambiguities', []),
            scope_summary=context.get('scope_summary', []),
        )
    if model_name == 'ComplianceAssessment':
        rows = [ComplianceRow(**item) for item in context.get('rows', [])]
        return ComplianceAssessment(
            coverage_ratio=context.get('coverage_ratio', 0.0),
            mandatory_gaps=context.get('mandatory_gaps', []),
            rows=rows,
            confidence_notes=context.get('confidence_notes', []),
        )
    if model_name == 'RiskAssessment':
        scored = context.get('scored_signals', {})
        risks = [RiskItem(**item) for item in scored.get('risks', [])]
        return RiskAssessment(
            overall_risk=scored.get('overall_risk', 'medium'),
            recommendation=scored.get('recommendation', 'conditional_bid'),
            rationale=scored.get('rationale', []),
            risks=risks,
        )
    if model_name == 'SubmissionPlan':
        raw_plan = context.get('raw_plan', {})
        tasks = [PlanTask(**item) for item in raw_plan.get('tasks', [])]
        return SubmissionPlan(
            executive_summary=raw_plan.get('executive_summary', 'Prepare the bid package.'),
            missing_artifacts=raw_plan.get('missing_artifacts', []),
            partner_actions=raw_plan.get('partner_actions', []),
            tasks=tasks,
        )
    raise AssertionError(f'No fake LLM handler for {model_name}')


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(StructuredLLM, 'invoke', _fake_invoke)
