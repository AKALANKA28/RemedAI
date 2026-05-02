from __future__ import annotations

from pathlib import Path

from hypothesis import given, strategies as st

from backend.app.tools.document_ingestion import parse_tender_package
from backend.app.tools.risk_scoring import score_procurement_risk


def test_intake_does_not_drop_all_requirements() -> None:
    sample_dir = Path('data/sample_inputs/remediation_tender')
    payload = parse_tender_package([str(path) for path in sorted(sample_dir.iterdir())])
    assert any(item['requirement_id'] == 'REQ-03' for item in payload['requirements'])


def test_compliance_sensitive_requirement_exists_in_seeded_case() -> None:
    sample_dir = Path('data/sample_inputs/remediation_tender')
    payload = parse_tender_package([str(path) for path in sorted(sample_dir.iterdir())])
    texts = ' '.join(item['text'].lower() for item in payload['requirements'])
    assert '24x7' in texts or 'response coverage' in texts


@given(st.integers(min_value=0, max_value=100))
def test_risk_rule_preserves_capacity_signal(availability_pct: int) -> None:
    parsed_tender = {'submission_deadline': '2026-05-14'}
    compliance_rows = [
        {
            'requirement_id': 'REQ-01',
            'requirement_text': 'Valid ISO certification',
            'status': 'fully_met',
            'recommended_action': 'Attach certificate',
        }
    ]
    result = score_procurement_risk(
        parsed_tender,
        compliance_rows,
        [{'role': 'Technical Lead', 'availability_pct': availability_pct, 'notes': 'synthetic'}],
    )
    assert result['recommendation'] in {'bid', 'conditional_bid', 'no_bid'}
    if availability_pct < 50:
        assert any(risk['title'].startswith('Limited capacity') for risk in result['risks'])


def test_planner_outputs_are_expected_after_full_run() -> None:
    from backend.app.services.workflow_runner import get_runner

    result = get_runner().run_sample('remediation_tender', 'Should we bid on this tender?')
    assert len(result['plan']['tasks']) >= 4
    assert result['artifacts']['summary'].endswith('summary.md')
    assert result['artifacts']['submission_plan'].endswith('submission_plan.json')


def test_env_example_uses_single_default_model_with_optional_agent_overrides() -> None:
    env_text = Path('.env.example').read_text(encoding='utf-8')
    assert 'OLLAMA_MODEL=phi3:mini' in env_text

    optional_keys = [
        'OLLAMA_ORCHESTRATOR_MODEL',
        'OLLAMA_INTAKE_MODEL',
        'OLLAMA_COMPLIANCE_MODEL',
        'OLLAMA_RISK_MODEL',
        'OLLAMA_PLANNER_MODEL',
    ]
    for key in optional_keys:
        assert f'# {key}=' in env_text
