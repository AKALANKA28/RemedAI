from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from langsmith import traceable


@dataclass(slots=True)
class RegisteredCase:
    case_id: str
    workspace_dir: str
    created_at: str
    manifest_path: str


@traceable(name='register_case', run_type='tool')
def register_case(query: str, input_paths: list[str], runtime_dir: str, case_label: str) -> RegisteredCase:
    """Create a case workspace and persist a manifest for a new tender assessment run."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    safe_label = ''.join(ch if ch.isalnum() or ch in {'_', '-'} else '_' for ch in case_label.lower())[:30]
    case_id = f'{safe_label}-{timestamp}'
    workspace = Path(runtime_dir) / 'outputs' / case_id
    workspace.mkdir(parents=True, exist_ok=True)
    manifest = {
        'case_id': case_id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'query': query,
        'input_paths': input_paths,
    }
    manifest_path = workspace / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    registered = RegisteredCase(
        case_id=case_id,
        workspace_dir=str(workspace),
        created_at=manifest['created_at'],
        manifest_path=str(manifest_path),
    )
    return registered
