from __future__ import annotations

from datetime import date, datetime
from typing import Any

from langsmith import traceable


def _days_to_deadline(deadline: str | None) -> int | None:
    if not deadline:
        return None
    parsed = datetime.strptime(deadline, '%Y-%m-%d').date()
    return (parsed - date.today()).days


@traceable(name='score_procurement_risk', run_type='tool')
def score_procurement_risk(
    parsed_tender: dict[str, Any],
    compliance_rows: list[dict[str, Any]],
    capacity_snapshot: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate deterministic bid-risk signals from tender facts, capability gaps, and resource availability."""
    risks: list[dict[str, str]] = []
    recommendation = 'bid'
    overall_risk = 'low'
    rationale: list[str] = []

    missing = [row for row in compliance_rows if row['status'] == 'missing']
    partial = [row for row in compliance_rows if row['status'] == 'partially_met']

    if missing:
        recommendation = 'no_bid'
        overall_risk = 'critical'
        for index, row in enumerate(missing, start=1):
            risks.append(
                {
                    'risk_id': f'RISK-MISS-{index}',
                    'title': f"Mandatory gap: {row['requirement_id']}",
                    'severity': 'critical',
                    'driver': row['requirement_text'],
                    'mitigation': row['recommended_action'],
                    'owner': 'Proposal Director',
                }
            )
        rationale.append('One or more mandatory requirements are currently unsupported.')
    elif partial:
        recommendation = 'conditional_bid'
        overall_risk = 'high'
        rationale.append('Mandatory delivery is possible only if partial gaps are closed before submission.')
        for index, row in enumerate(partial, start=1):
            risks.append(
                {
                    'risk_id': f'RISK-PART-{index}',
                    'title': f"Recoverable compliance gap: {row['requirement_id']}",
                    'severity': 'high',
                    'driver': row['requirement_text'],
                    'mitigation': row['recommended_action'],
                    'owner': 'Proposal Lead',
                }
            )

    days_remaining = _days_to_deadline(parsed_tender.get('submission_deadline'))
    if days_remaining is not None and days_remaining < 21:
        overall_risk = 'high' if overall_risk in {'low', 'medium'} else overall_risk
        recommendation = 'conditional_bid' if recommendation == 'bid' else recommendation
        rationale.append(f'Only {days_remaining} days remain before submission.')
        risks.append(
            {
                'risk_id': 'RISK-SCHED-1',
                'title': 'Compressed bid schedule',
                'severity': 'high' if days_remaining < 14 else 'medium',
                'driver': f'Submission deadline in {days_remaining} days',
                'mitigation': 'Freeze the bid go/no-go decision immediately and parallelize evidence collection.',
                'owner': 'Proposal Lead',
            }
        )

    overloaded = [item for item in capacity_snapshot if int(item['availability_pct']) < 50]
    if overloaded:
        if recommendation == 'bid':
            recommendation = 'conditional_bid'
        if overall_risk == 'low':
            overall_risk = 'medium'
        rationale.append('One or more key owners have limited near-term availability.')
        for index, item in enumerate(overloaded, start=1):
            risks.append(
                {
                    'risk_id': f'RISK-CAP-{index}',
                    'title': f"Limited capacity: {item['role']}",
                    'severity': 'medium',
                    'driver': item['notes'],
                    'mitigation': 'Reassign internal support or pre-book partner assistance.',
                    'owner': item['role'],
                }
            )

    if recommendation == 'bid' and not rationale:
        rationale.append('Current evidence indicates the tender is serviceable with internal capability and manageable delivery risk.')

    return {
        'overall_risk': overall_risk,
        'recommendation': recommendation,
        'rationale': rationale,
        'risks': risks,
    }
