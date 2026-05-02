# Assignment Rubric Mapping

| Rubric area | Evidence in repository |
|---|---|
| Problem Definition & System Architecture | `README.md`, `docs/PROJECT_DESCRIPTION.md`, report architecture section |
| Multi-Agent Architecture & Orchestration | `backend/app/graph/workflow.py`, `backend/app/agents/`, per-agent model routing in `backend/app/services/llm.py` |
| Tool Development & Integration | `backend/app/tools/` |
| State Management & Observability | `backend/app/graph/state.py`, `backend/app/services/observability.py`, LangGraph SQLite checkpointer |
| Testing & Evaluation | `tests/`, `scripts/run_sample_case.py` |
| Individual Agent Design | prompts and agent classes under `backend/app/agents/`, plus agent-specific Ollama models in `.env.example` |
| Individual Custom Tool | one primary custom tool per specialist agent plus orchestrator registry tool |
| Report | `docs/CTSE_Assignment2_Report.docx` and `docs/CTSE_Assignment2_Report.pdf` |
| Demo support | `docs/demo_video_script.md`, Streamlit frontend |

## Contribution plan template for a 4-person team

Replace the placeholders below with real member names before submission.

- Student 1: Orchestrator Agent + Case Registry Tool + orchestrator tests
- Student 2: Intake Agent + Document Ingestion Tool + intake tests
- Student 3: Compliance Agent + Capability Lookup Tool + compliance tests
- Student 4: Risk Agent + Risk Scoring Tool + risk tests
- Group integration: Planner Agent + Plan Export Tool + unified evaluation harness
