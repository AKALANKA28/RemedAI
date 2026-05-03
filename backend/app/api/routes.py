from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.models.schemas import AnalyzeSampleRequest, AnalyzeTextRequest
from backend.app.services.workflow_runner import get_runner

router = APIRouter()
logger = get_logger(__name__)


@router.get('/health')
def health() -> dict[str, Any]:
    return {"status": "ok", "agent_models": settings.agent_model_map()}


@router.post('/api/v1/analyze/sample')
def analyze_sample(payload: AnalyzeSampleRequest) -> dict:
    runner = get_runner()
    logger.info('Analyze sample request: sample_id=%s', payload.sample_id)
    return runner.run_sample(payload.sample_id, payload.query)


@router.post('/api/v1/analyze/text')
def analyze_text(payload: AnalyzeTextRequest) -> dict:
    runner = get_runner()
    logger.info('Analyze text request: case_label=%s input_paths=%d', payload.case_label, len(payload.input_paths))
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
        logger.warning('Case not found: case_id=%s', case_id)
        raise HTTPException(status_code=404, detail='Case not found')
    logger.info('Fetch case: case_id=%s', case_id)
    return json.loads(bundle_path.read_text(encoding='utf-8'))


@router.get('/api/v1/cases/{case_id}/audit')
def get_case_audit(case_id: str) -> FileResponse:
    runner = get_runner()
    outputs_dir = (Path(runner.runtime_dir) / 'outputs').resolve()
    audit_path = (outputs_dir / case_id / 'audit.jsonl').resolve()
    if outputs_dir not in audit_path.parents:
        raise HTTPException(status_code=400, detail='Invalid case id')
    if not audit_path.exists() or not audit_path.is_file():
        logger.warning('Audit log not found: case_id=%s', case_id)
        raise HTTPException(status_code=404, detail='Audit log not found')
    logger.info('Fetch audit log: case_id=%s', case_id)
    return FileResponse(
        audit_path,
        media_type='text/plain',
        filename='audit.jsonl',
        content_disposition_type='inline',
    )
