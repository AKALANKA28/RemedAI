from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import AnalyzeSampleRequest, AnalyzeTextRequest
from backend.app.services.workflow_runner import get_runner

router = APIRouter()


@router.get('/health')
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post('/api/v1/analyze/sample')
def analyze_sample(payload: AnalyzeSampleRequest) -> dict:
    runner = get_runner()
    return runner.run_sample(payload.sample_id, payload.query)


@router.post('/api/v1/analyze/text')
def analyze_text(payload: AnalyzeTextRequest) -> dict:
    runner = get_runner()
    return runner.run_text_case(
        query=payload.query,
        input_paths=payload.input_paths,
        case_label=payload.case_label,
    )


@router.get('/api/v1/cases/{case_id}')
def get_case(case_id: str) -> dict:
    runner = get_runner()
    bundle_path = Path(runner.runtime_dir) / 'outputs' / case_id / 'final_bundle.json'
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail='Case not found')
    return json.loads(bundle_path.read_text(encoding='utf-8'))
