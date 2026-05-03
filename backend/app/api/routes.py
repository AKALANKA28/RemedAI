from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException

from backend.app.core.config import settings
from backend.app.models.schemas import AnalyzeSampleRequest, AnalyzeTenderUrlRequest, AnalyzeTextRequest
from backend.app.services.llm import ModelInvocationError
from backend.app.services.logging_utils import get_app_logger
from backend.app.services.workflow_runner import get_runner

router = APIRouter()
logger = get_app_logger('api')


@router.get('/health')
def health() -> dict[str, Any]:
    return {"status": "ok", "agent_models": settings.agent_model_map()}


@router.post('/api/v1/analyze/sample')
def analyze_sample(payload: AnalyzeSampleRequest) -> dict:
    logger.info('API analyze_sample sample_id=%s', payload.sample_id)
    runner = get_runner()
    return runner.run_sample(payload.sample_id, payload.query)


@router.post('/api/v1/analyze/text')
def analyze_text(payload: AnalyzeTextRequest) -> dict:
    logger.info('API analyze_text case_label=%s input_files=%s', payload.case_label, len(payload.input_paths))
    runner = get_runner()
    return runner.run_text_case(
        query=payload.query,
        input_paths=payload.input_paths,
        case_label=payload.case_label,
    )


@router.post('/api/v1/analyze/url')
def analyze_tender_url(payload: AnalyzeTenderUrlRequest) -> dict:
    logger.info('API analyze_url source=%s url=%s', payload.source, payload.tender_url)
    runner = get_runner()
    try:
        return runner.run_tender_url(
            source=payload.source,
            tender_url=payload.tender_url,
            query=payload.query,
        )
    except ValueError as exc:
        logger.warning('API analyze_url rejected: %s', exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except requests.RequestException as exc:
        logger.warning('API analyze_url fetch failed: %s', exc)
        raise HTTPException(status_code=502, detail=f'Unable to fetch tender URL: {exc}') from exc
    except ModelInvocationError as exc:
        logger.warning('API analyze_url model failed: %s', exc)
        raise HTTPException(
            status_code=503,
            detail=f'Ollama model failed for agent {exc.agent_name} using {exc.model_name}: {exc}',
        ) from exc


@router.get('/api/v1/cases/{case_id}')
def get_case(case_id: str) -> dict:
    runner = get_runner()
    bundle_path = Path(runner.runtime_dir) / 'outputs' / case_id / 'final_bundle.json'
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail='Case not found')
    return json.loads(bundle_path.read_text(encoding='utf-8'))


@router.get('/api/v1/cases/{case_id}/audit')
def get_case_audit(case_id: str) -> dict:
    runner = get_runner()
    audit_path = Path(runner.runtime_dir) / 'outputs' / case_id / 'audit.jsonl'
    if not audit_path.exists():
        raise HTTPException(status_code=404, detail='Audit log not found')

    raw_lines = [line for line in audit_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    events = [json.loads(line) for line in raw_lines]
    return {
        'case_id': case_id,
        'event_count': len(events),
        'events': events,
        'raw': '\n'.join(raw_lines),
    }
