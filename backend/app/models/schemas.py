from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeSampleRequest(BaseModel):
    sample_id: str = Field(default='remediation_tender')
    query: str = Field(default='Should we bid on this tender?')


class AnalyzeTextRequest(BaseModel):
    query: str
    input_paths: list[str] = Field(default_factory=list)
    case_label: str = Field(default='manual_case')


class OrchestratorDecision(BaseModel):
    objective: str
    route: Literal['continue', 'clarify'] = 'continue'
    proceed: bool = True
    rationale: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)


class TenderRequirement(BaseModel):
    requirement_id: str
    text: str
    mandatory: bool = True
    category: str = 'general'
    evidence_needed: str = ''


class TenderSummary(BaseModel):
    project_title: str
    issuer: str
    submission_deadline: str | None = None
    estimated_budget_lkr: int | None = None
    contract_duration_months: int | None = None
    requirements: list[TenderRequirement] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    scope_summary: list[str] = Field(default_factory=list)


class ComplianceRow(BaseModel):
    requirement_id: str
    requirement_text: str
    status: Literal['fully_met', 'partially_met', 'missing']
    justification: str
    supporting_evidence: list[str] = Field(default_factory=list)
    recommended_action: str


class ComplianceAssessment(BaseModel):
    coverage_ratio: float = 0.0
    mandatory_gaps: list[str] = Field(default_factory=list)
    rows: list[ComplianceRow] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    risk_id: str
    title: str
    severity: Literal['low', 'medium', 'high', 'critical']
    driver: str
    mitigation: str
    owner: str


class RiskAssessment(BaseModel):
    overall_risk: Literal['low', 'medium', 'high', 'critical']
    recommendation: Literal['bid', 'conditional_bid', 'no_bid']
    rationale: list[str] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)


class PlanTask(BaseModel):
    task_id: str
    title: str
    owner: str
    due_date: str
    deliverable: str
    depends_on: list[str] = Field(default_factory=list)


class SubmissionPlan(BaseModel):
    executive_summary: str
    missing_artifacts: list[str] = Field(default_factory=list)
    partner_actions: list[str] = Field(default_factory=list)
    tasks: list[PlanTask] = Field(default_factory=list)


class FinalBundle(BaseModel):
    case_id: str
    project_title: str
    recommendation: str
    overall_risk: str
    summary: str
    compliance: ComplianceAssessment
    risk: RiskAssessment
    plan: SubmissionPlan
    artifacts: dict[str, str] = Field(default_factory=dict)
    audit_trail: list[dict] = Field(default_factory=list)
