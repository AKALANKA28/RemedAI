from __future__ import annotations

from backend.app.services.workflow_runner import get_runner


def test_sample_workflow_runs_to_completion() -> None:
    result = get_runner().run_sample('remediation_tender', 'Should we bid on this tender?')
    assert result['case_id']
    assert result['project_title']
    assert result['recommendation'] in {'bid', 'conditional_bid', 'no_bid'}
    assert 'compliance' in result
    assert 'risk' in result
    assert 'plan' in result
