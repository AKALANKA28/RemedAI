from __future__ import annotations

from langsmith import traceable

from backend.app.models.schemas import FinalBundle, SubmissionPlan
from backend.app.prompts import PLANNER_PROMPT
from backend.app.services.llm import StructuredLLM
from backend.app.services.observability import append_audit_event
from backend.app.tools.planning import build_submission_plan, write_case_outputs


class PlannerAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(PLANNER_PROMPT, SubmissionPlan, agent_name='planner')

    @traceable(name='planner_agent', run_type='chain')
    def run(
        self,
        case_id: str,
        workspace_dir: str,
        parsed_tender: dict,
        compliance: dict,
        risk: dict,
        audit_trail: list[dict],
    ) -> dict:
        raw_plan = build_submission_plan(parsed_tender, compliance, risk)
        plan = self.chain.invoke(
            task='Create the final submission plan for the bid team.',
            context={
                'parsed_tender': parsed_tender,
                'compliance': compliance,
                'risk': risk,
                'raw_plan': raw_plan,
            },
        )
        summary = (
            f"Recommendation: {risk['recommendation']}. "
            f"Coverage ratio: {compliance['coverage_ratio']}. "
            f"Mandatory gaps: {len(compliance['mandatory_gaps'])}."
        )
        bundle = FinalBundle(
            case_id=case_id,
            project_title=parsed_tender['project_title'],
            recommendation=risk['recommendation'],
            overall_risk=risk['overall_risk'],
            summary=summary,
            compliance=compliance,
            risk=risk,
            plan=plan,
            artifacts={},
            audit_trail=audit_trail,
        )
        artifacts = write_case_outputs(workspace_dir, bundle.model_dump())
        enriched_bundle = bundle.model_copy(update={'artifacts': artifacts})
        event = append_audit_event(
            workspace_dir,
            'planner',
            'final_bundle',
            {'model': self.chain.model_name, 'output': enriched_bundle.model_dump()},
        )
        final = enriched_bundle.model_dump()
        final['audit_trail'] = audit_trail + [event]
        artifacts = write_case_outputs(workspace_dir, final)
        final['artifacts'] = artifacts
        return {
            'plan': plan.model_dump(),
            'artifacts': artifacts,
            'final_bundle': final,
            'audit_trail': [event],
        }
