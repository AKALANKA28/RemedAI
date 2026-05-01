from __future__ import annotations

import sqlite3
from functools import lru_cache

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from backend.app.agents.compliance import ComplianceAgent
from backend.app.agents.intake import IntakeAgent
from backend.app.agents.orchestrator import OrchestratorAgent
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.risk import RiskAgent
from backend.app.core.config import settings
from backend.app.graph.state import TenderMASState


orchestrator = OrchestratorAgent()
intake = IntakeAgent()
compliance = ComplianceAgent()
risk = RiskAgent()
planner = PlannerAgent()


def orchestrator_node(state: TenderMASState) -> dict:
    return orchestrator.run(
        user_query=state['user_query'],
        input_paths=state['input_paths'],
        case_label=state.get('case_label', 'manual_case'),
    )


def intake_node(state: TenderMASState) -> dict:
    return intake.run(workspace_dir=state['workspace_dir'], input_paths=state['input_paths'])


def compliance_node(state: TenderMASState) -> dict:
    return compliance.run(workspace_dir=state['workspace_dir'], parsed_tender=state['parsed_tender'])


def risk_node(state: TenderMASState) -> dict:
    return risk.run(
        workspace_dir=state['workspace_dir'],
        parsed_tender=state['parsed_tender'],
        compliance=state['compliance'],
    )


def planner_node(state: TenderMASState) -> dict:
    return planner.run(
        case_id=state['case_id'],
        workspace_dir=state['workspace_dir'],
        parsed_tender=state['parsed_tender'],
        compliance=state['compliance'],
        risk=state['risk'],
        audit_trail=state.get('audit_trail', []),
    )


def route_after_orchestrator(state: TenderMASState) -> str:
    decision = state.get('orchestrator_decision', {})
    if decision.get('route') == 'clarify' or not decision.get('proceed', True):
        return 'end'
    return 'intake'


@lru_cache(maxsize=1)
def build_workflow():
    builder = StateGraph(TenderMASState)
    builder.add_node('orchestrator', orchestrator_node)
    builder.add_node('intake', intake_node)
    builder.add_node('compliance', compliance_node)
    builder.add_node('risk', risk_node)
    builder.add_node('planner', planner_node)

    builder.add_edge(START, 'orchestrator')
    builder.add_conditional_edges(
        'orchestrator',
        route_after_orchestrator,
        {
            'intake': 'intake',
            'end': END,
        },
    )
    builder.add_edge('intake', 'compliance')
    builder.add_edge('compliance', 'risk')
    builder.add_edge('risk', 'planner')
    builder.add_edge('planner', END)

    connection = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    return builder.compile(checkpointer=checkpointer)
