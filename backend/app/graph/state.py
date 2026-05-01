from __future__ import annotations

from operator import add
from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class TenderMASState(TypedDict, total=False):
    case_id: str
    workspace_dir: str
    user_query: str
    case_label: str
    input_paths: list[str]
    messages: Annotated[list[AnyMessage], add_messages]
    audit_trail: Annotated[list[dict[str, Any]], add]
    errors: Annotated[list[str], add]
    orchestrator_decision: dict[str, Any]
    parsed_tender: dict[str, Any]
    compliance: dict[str, Any]
    risk: dict[str, Any]
    plan: dict[str, Any]
    artifacts: dict[str, str]
    final_bundle: dict[str, Any]
