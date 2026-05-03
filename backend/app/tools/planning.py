from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from langsmith import traceable


def _deadline(date_str: str | None) -> datetime:
    if not date_str:
        return datetime.now(UTC).replace(tzinfo=None) + timedelta(days=21)
    return datetime.strptime(date_str, '%Y-%m-%d')


@traceable(name='build_submission_plan', run_type='tool')
def build_submission_plan(
    parsed_tender: dict[str, Any],
    compliance: dict[str, Any],
    risk: dict[str, Any],
) -> dict[str, Any]:
    """Create a backward-planned submission checklist from the tender deadline and identified gaps."""
    deadline = _deadline(parsed_tender.get('submission_deadline'))
    missing_artifacts = compliance.get('mandatory_gaps', [])
    rows = compliance.get('rows', [])
    partner_actions = [row['recommended_action'] for row in rows if row['status'] == 'partially_met']
    tasks = [
        {
            'task_id': 'PLAN-01',
            'title': 'Freeze bid strategy and executive sponsor approval',
            'owner': 'Proposal Director',
            'due_date': (deadline - timedelta(days=14)).date().isoformat(),
            'deliverable': 'Signed bid/no-bid checkpoint',
            'depends_on': [],
        },
        {
            'task_id': 'PLAN-02',
            'title': 'Assemble compliance evidence pack',
            'owner': 'Proposal Lead',
            'due_date': (deadline - timedelta(days=10)).date().isoformat(),
            'deliverable': 'Evidence annex and certificates',
            'depends_on': ['PLAN-01'],
        },
        {
            'task_id': 'PLAN-03',
            'title': 'Obtain partner commitment letters for partial gaps',
            'owner': 'Technical Lead',
            'due_date': (deadline - timedelta(days=8)).date().isoformat(),
            'deliverable': 'Signed commitment letters',
            'depends_on': ['PLAN-01'],
        },
        {
            'task_id': 'PLAN-04',
            'title': 'Draft technical methodology and incident coverage narrative',
            'owner': 'Technical Lead',
            'due_date': (deadline - timedelta(days=5)).date().isoformat(),
            'deliverable': 'Technical response section',
            'depends_on': ['PLAN-02', 'PLAN-03'],
        },
        {
            'task_id': 'PLAN-05',
            'title': 'Final QA and submission rehearsal',
            'owner': 'QA Lead',
            'due_date': (deadline - timedelta(days=2)).date().isoformat(),
            'deliverable': 'Signed quality checklist',
            'depends_on': ['PLAN-04'],
        },
    ]
    summary = (
        f"Recommended mode: {risk.get('recommendation', 'conditional_bid')}. "
        f"Focus first on {len(partner_actions)} recoverable gap(s) and lock the evidence pack before final drafting."
    )
    return {
        'executive_summary': summary,
        'missing_artifacts': missing_artifacts,
        'partner_actions': sorted(set(partner_actions)),
        'tasks': tasks,
    }


@traceable(name='write_case_outputs', run_type='tool')
def write_case_outputs(workspace_dir: str, final_bundle: dict[str, Any]) -> dict[str, str]:
    """Persist the final machine-readable bundle and human-friendly output files for a tender case."""
    workspace = Path(workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    final_bundle_path = workspace / 'final_bundle.json'
    final_bundle_path.write_text(json.dumps(final_bundle, indent=2), encoding='utf-8')

    summary_path = workspace / 'summary.md'
    summary_path.write_text(
        f"# {final_bundle['project_title']}\n\n"
        f"- Recommendation: **{final_bundle['recommendation']}**\n"
        f"- Overall risk: **{final_bundle['overall_risk']}**\n\n"
        f"{final_bundle['summary']}\n",
        encoding='utf-8',
    )

    compliance_path = workspace / 'compliance_matrix.csv'
    with compliance_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=['requirement_id', 'requirement_text', 'status', 'justification', 'recommended_action'],
        )
        writer.writeheader()
        for row in final_bundle['compliance']['rows']:
            writer.writerow(
                {
                    'requirement_id': row['requirement_id'],
                    'requirement_text': row['requirement_text'],
                    'status': row['status'],
                    'justification': row['justification'],
                    'recommended_action': row['recommended_action'],
                }
            )

    risk_path = workspace / 'risk_register.csv'
    with risk_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=['risk_id', 'title', 'severity', 'driver', 'mitigation', 'owner'],
        )
        writer.writeheader()
        for row in final_bundle['risk']['risks']:
            writer.writerow(row)

    plan_path = workspace / 'submission_plan.json'
    plan_path.write_text(json.dumps(final_bundle['plan'], indent=2), encoding='utf-8')

    return {
        'final_bundle': str(final_bundle_path),
        'summary': str(summary_path),
        'compliance_matrix': str(compliance_path),
        'risk_register': str(risk_path),
        'submission_plan': str(plan_path),
        'audit_log': str(workspace / 'audit.jsonl'),
    }
