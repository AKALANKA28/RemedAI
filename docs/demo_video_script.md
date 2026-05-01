# Demo Video Script (4-5 minutes)

## 0:00-0:30 - Problem framing
- Introduce RemedAI.
- Explain that it is a local multi-agent system for environmental remediation tender qualification.
- Mention Ollama, LangGraph, LangChain, and local tooling.

## 0:30-1:10 - Show architecture
- Open the README architecture section.
- Explain the 5-agent flow: orchestrator -> intake -> compliance -> risk -> planner.
- Mention one tool per agent and the SQLite state/tracing components.

## 1:10-2:00 - Show backend only
- Run `python scripts/run_sample_case.py --sample remediation_tender`.
- Point out the generated recommendation, risks, and artifacts.
- Open `runtime/outputs/<case_id>/summary.md` and `audit.jsonl`.

## 2:00-3:20 - Show frontend
- Start the Streamlit UI.
- Select the seeded sample tender.
- Click **Run analysis**.
- Walk through recommendation metrics, compliance matrix, risk register, and submission plan.

## 3:20-4:20 - Show observability and testing
- Show local audit logs.
- If LangSmith is configured, show the trace tree.
- Run `pytest -q` or show the evaluation files.

## 4:20-4:50 - Close
- Summarize why the chosen problem is useful and non-generic.
- Highlight local privacy, structured state handoffs, and team contribution mapping.
