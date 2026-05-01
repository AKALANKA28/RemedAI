from __future__ import annotations

from pathlib import Path

from backend.app.tools.document_ingestion import parse_tender_package
from backend.app.tools.risk_scoring import score_procurement_risk


def test_parse_tender_package_extracts_seeded_requirements() -> None:
    sample_dir = Path('data/sample_inputs/remediation_tender')
    payload = parse_tender_package([str(path) for path in sorted(sample_dir.iterdir())])
    assert payload['project_title'].startswith('Emergency remediation')
    assert len(payload['requirements']) >= 7
    assert payload['submission_deadline'] == '2026-05-14'


def test_score_procurement_risk_escalates_missing_mandatory_requirements() -> None:
    parsed_tender = {'submission_deadline': '2026-05-14'}
    compliance_rows = [
        {
            'requirement_id': 'REQ-03',
            'requirement_text': 'Provide 24x7 response coverage',
            'status': 'missing',
            'recommended_action': 'Find an approved partner',
        }
    ]
    capacity = [{'role': 'Proposal Lead', 'availability_pct': 80, 'notes': 'Available'}]
    result = score_procurement_risk(parsed_tender, compliance_rows, capacity)
    assert result['recommendation'] == 'no_bid'
    assert result['overall_risk'] == 'critical'
