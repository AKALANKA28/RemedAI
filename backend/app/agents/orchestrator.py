from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from langsmith import traceable

from backend.app.core.config import settings
from backend.app.models.schemas import OrchestratorDecision
from backend.app.prompts import ORCHESTRATOR_PROMPT
from backend.app.services.llm import StructuredLLM
from backend.app.services.observability import append_audit_event
from backend.app.tools.case_registry import register_case


class OrchestratorAgent:
    def __init__(self) -> None:
        self.chain = StructuredLLM(ORCHESTRATOR_PROMPT, OrchestratorDecision, agent_name='orchestrator')

    @traceable(name='orchestrator_agent', run_type='chain')
    def run(self, user_query: str, input_paths: list[str], case_label: str) -> dict:
        registered = register_case(
            query=user_query,
            input_paths=input_paths,
            runtime_dir=settings.runtime_dir,
            case_label=case_label,
        )
        missing_paths = [path for path in input_paths if not Path(path).exists()]
        if not input_paths or missing_paths:
            rationale: list[str] = []
            required_inputs: list[str] = []
            questions: list[str] = []
            if not input_paths:
                rationale.append('No input documents were provided.')
                required_inputs.extend(
                    [
                        'Project Scope of Work document (scope_of_work.md)',
                        'Tender Notice document (tender_notice.md)',
                    ]
                )
                questions.append('Please provide the tender scope and notice documents.')
            if missing_paths:
                rationale.append(f"Some input paths do not exist: {', '.join(missing_paths)}")
                required_inputs.extend(missing_paths)
                questions.append('Please confirm the correct file paths for the tender documents.')
            decision = OrchestratorDecision(
                objective=f'Assess bid feasibility for: {user_query}',
                route='clarify',
                proceed=False,
                rationale=rationale,
                required_inputs=required_inputs,
                clarification_questions=questions,
            )
            model_name = 'rule-based'
        else:
            decision = OrchestratorDecision(
                objective=f'Assess bid feasibility for: {user_query}',
                route='continue',
                proceed=True,
                rationale=['Input documents were found; proceeding with intake.'],
            )
            model_name = 'rule-based'
        event = append_audit_event(
            registered.workspace_dir,
            'orchestrator',
            'decision',
            {'model': model_name, 'output': decision.model_dump()},
        )
        return {
            'case_id': registered.case_id,
            'workspace_dir': registered.workspace_dir,
            'orchestrator_decision': decision.model_dump(),
            'audit_trail': [event],
        }
