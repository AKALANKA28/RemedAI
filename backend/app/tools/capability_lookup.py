from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from langsmith import traceable


def _normalize_tokens(text: str) -> set[str]:
    cleaned = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in text)
    return {token for token in cleaned.split() if len(token) > 2}


def _load_json_db(db_path: str) -> dict[str, Any]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    payload: dict[str, Any] = defaultdict(list)
    for table in ('capabilities', 'certifications', 'past_projects', 'staff_capacity'):
        rows = connection.execute(f'SELECT * FROM {table}').fetchall()
        payload[table] = [dict(row) for row in rows]
    connection.close()
    return payload


@traceable(name='query_capability_catalog', run_type='tool')
def query_capability_catalog(requirements: list[dict[str, Any]], db_path: str) -> list[dict[str, Any]]:
    """Match tender requirements against a local SQLite capability catalog and return evidence-backed coverage rows."""
    db = _load_json_db(db_path)
    capabilities = db['capabilities']
    certifications = db['certifications']
    projects = db['past_projects']
    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        text = requirement['text']
        tokens = _normalize_tokens(text)
        evidence: list[str] = []
        status = 'missing'
        recommended_action = 'Find external partner or decline the requirement.'
        if requirement['category'] == 'certification':
            for cert in certifications:
                if tokens & _normalize_tokens(' '.join(cert['tags'])):
                    status = 'fully_met'
                    evidence.append(f"Certification {cert['name']} valid until {cert['valid_until']}")
                    recommended_action = 'Attach current certificate in the compliance pack.'
        elif requirement['category'] == 'experience':
            matches = [p for p in projects if tokens & _normalize_tokens(' '.join(p['tags']))]
            if len(matches) >= 2:
                status = 'partially_met' if len(matches) < 3 else 'fully_met'
                evidence.extend([f"Past project: {project['name']} ({project['year']})" for project in matches[:3]])
                recommended_action = 'Prepare project datasheets and emphasise closest public-sector analogues.'
        else:
            scored: list[tuple[int, dict[str, Any]]] = []
            for capability in capabilities:
                score = len(tokens & _normalize_tokens(capability['name'] + ' ' + ' '.join(capability['tags'])))
                if score:
                    scored.append((score, capability))
            scored.sort(key=lambda item: item[0], reverse=True)
            if scored:
                top_score, top = scored[0]
                evidence.append(top['evidence'])
                if 'expired' in top['evidence'].lower() or 'no active roster' in top['evidence'].lower() or 'expired' in top['name'].lower():
                    status = 'partially_met'
                    recommended_action = 'Renew or formalize the external arrangement before bidding.'
                else:
                    status = 'fully_met' if top_score >= 2 else 'partially_met'
                    recommended_action = 'Attach proof and name the delivery owner in the proposal.'
        if status == 'missing' and not evidence:
            evidence.append('No direct evidence found in the local capability database.')
        if status == 'partially_met' and requirement['category'] in {'operations', 'technical'}:
            recommended_action = 'Obtain a written partner commitment and include it in the bid submission.'
        rows.append(
            {
                'requirement_id': requirement['requirement_id'],
                'requirement_text': text,
                'status': status,
                'justification': evidence[0],
                'supporting_evidence': evidence,
                'recommended_action': recommended_action,
            }
        )
    return rows


@traceable(name='get_capacity_snapshot', run_type='tool')
def get_capacity_snapshot(db_path: str) -> list[dict[str, Any]]:
    """Return local staff availability data for operational risk scoring."""
    return _load_json_db(db_path)['staff_capacity']
