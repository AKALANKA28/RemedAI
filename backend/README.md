# Backend

The backend exposes the multi-agent workflow as a FastAPI service and can be run independently of the frontend.

## Endpoints

- `GET /health` - health check plus active per-agent Ollama model map
- `POST /api/v1/analyze/sample` - run a seeded sample tender
- `POST /api/v1/analyze/text` - run a case from a plain-text brief and optional file paths
- `GET /api/v1/cases/{case_id}` - inspect a stored final bundle if it exists

## Design notes

- All agents share a LangGraph state object.
- Every agent writes structured audit events, including the local model used for that agent run.
- A SQLite LangGraph checkpointer preserves graph state between nodes.
- The API is intentionally thin: orchestration logic lives in `backend/app/graph/workflow.py`.
- Agent-specific Ollama models are configured in `.env` through the `OLLAMA_<AGENT>_MODEL` variables.
