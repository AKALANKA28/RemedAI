from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langsmith import traceable


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    return value


@traceable(name='append_local_audit', run_type='tool')
def append_audit_event(workspace_dir: str, agent: str, stage: str, payload: Any) -> dict[str, Any]:
    """Append a structured audit event to a case-local JSONL file."""
    event = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'agent': agent,
        'stage': stage,
        'payload': _jsonable(payload),
    }
    audit_path = Path(workspace_dir) / 'audit.jsonl'
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + '\n')
    return event
