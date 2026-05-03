from __future__ import annotations

import json

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = 'http://127.0.0.1:8000'

st.set_page_config(page_title='RemedAI Demo', page_icon='🧪', layout='wide')

st.markdown(
    """
    <style>
    .metric-card {
        padding: 1rem;
        border-radius: 1rem;
        background: linear-gradient(180deg, #f7fbff 0%, #eef6f2 100%);
        border: 1px solid rgba(0,0,0,0.08);
    }
    .small-note {
        color: #5b6570;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title('RemedAI')
st.caption('Local multi-agent tender qualification for environmental remediation bids')


def _parse_audit_jsonl(raw_text: str) -> list[dict]:
    events: list[dict] = []
    for line_no, line in enumerate(raw_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            events.append(json.loads(stripped))
        except json.JSONDecodeError:
            events.append({'_parse_error': True, 'line_number': line_no, 'raw': stripped})
    return events


def _summarize_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {'payload_type': type(payload).__name__}
    summary: dict[str, object] = {}
    model = payload.get('model')
    if model:
        summary['model'] = model
    output = payload.get('output')
    if isinstance(output, dict):
        for key in ('case_id', 'recommendation', 'overall_risk', 'coverage_ratio'):
            if key in output:
                summary[key] = output[key]
    decision = payload.get('decision')
    if decision:
        summary['decision'] = decision
    return summary

with st.sidebar:
    st.header('Run settings')
    sample_id = st.selectbox(
        'Sample tender',
        ['remediation_tender', 'riverbank_spill', 'asbestos_abatement', 'tailings_stabilization'],
    )
    query = st.text_area('User objective', value='Should we bid on this tender?')
    run_button = st.button('Run analysis', type='primary', width='stretch')
    st.markdown('<p class="small-note">Backend must be running on port 8000.</p>', unsafe_allow_html=True)

if run_button:
    with st.spinner('Running 5-agent workflow...'):
        response = requests.post(
            f'{BACKEND_URL}/api/v1/analyze/sample',
            json={'sample_id': sample_id, 'query': query},
            timeout=300,
        )
        response.raise_for_status()
        st.session_state['result'] = response.json()

result = st.session_state.get('result')
if result:
    case_id = result.get('case_id')
    if case_id and st.session_state.get('audit_case_id') != case_id:
        st.session_state.pop('audit_log_raw', None)
        st.session_state.pop('audit_events', None)
        st.session_state['audit_case_id'] = case_id
    if not result or 'recommendation' not in result:
        st.error('Workflow did not complete successfully.')
        st.write(result)
    else:
        metric_cols = st.columns(4)
        metric_cols[0].metric('Recommendation', result.get('recommendation', 'N/A'))
        metric_cols[1].metric('Overall risk', result.get('overall_risk', 'N/A'))
        metric_cols[2].metric(
            'Mandatory gaps',
            len(result.get('compliance', {}).get('mandatory_gaps', []))
        )
        metric_cols[3].metric(
            'Plan tasks',
            len(result.get('plan', {}).get('tasks', []))
        )

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ['Executive Summary', 'Compliance', 'Risk', 'Plan', 'Audit Log']
        )

        with tab1:
            st.subheader(result['project_title'])
            st.write(result['summary'])
            st.write(result['artifacts'])

        with tab2:
            df = pd.DataFrame(result['compliance']['rows'])
            st.dataframe(df, width='stretch')

        with tab3:
            risk_df = pd.DataFrame(result['risk']['risks'])
            st.dataframe(risk_df, width='stretch')
            st.write('Rationale:')
            for reason in result['risk']['rationale']:
                st.markdown(f'- {reason}')

        with tab4:
            plan_df = pd.DataFrame(result['plan']['tasks'])
            st.dataframe(plan_df, width='stretch')

        with tab5:
            st.subheader('Audit log')
            if not case_id:
                st.info('Run an analysis to view the audit log.')
            else:
                audit_url = f'{BACKEND_URL}/api/v1/cases/{case_id}/audit'
                load_clicked = st.button('Load audit log', type='secondary')
                if load_clicked:
                    with st.spinner('Fetching audit log...'):
                        try:
                            response = requests.get(audit_url, timeout=60)
                            if response.status_code == 404:
                                st.warning('Audit log not found yet for this case.')
                            else:
                                response.raise_for_status()
                                raw_text = response.text
                                st.session_state['audit_log_raw'] = raw_text
                                st.session_state['audit_events'] = _parse_audit_jsonl(raw_text)
                        except requests.RequestException as exc:
                            st.error(f'Unable to fetch audit log: {exc}')

                raw_text = st.session_state.get('audit_log_raw')
                events = st.session_state.get('audit_events', [])
                if raw_text:
                    st.download_button(
                        'Download audit JSONL',
                        data=raw_text,
                        file_name=f'{case_id}-audit.jsonl',
                        mime='text/plain',
                    )
                    st.caption(f'Loaded {len(events)} events from the audit log.')
                else:
                    st.caption('Load the audit log to enable event summaries and downloads.')
                    st.markdown(f'[Open raw audit log]({audit_url})')

                if events:
                    st.subheader('Event summaries')
                    for index, event in enumerate(events, start=1):
                        agent = event.get('agent', 'unknown')
                        stage = event.get('stage', 'event')
                        timestamp = event.get('timestamp')
                        title = f'{index}. {agent} - {stage}'
                        if timestamp:
                            title = f'{title} ({timestamp})'
                        with st.expander(title):
                            if event.get('_parse_error'):
                                st.warning(f"Parse error on line {event.get('line_number')}")
                                st.code(event.get('raw', ''), language='json')
                                continue
                            payload = event.get('payload', {})
                            summary = {
                                'timestamp': timestamp,
                                'agent': agent,
                                'stage': stage,
                            }
                            summary.update(_summarize_payload(payload))
                            st.write(summary)
                            if isinstance(payload, dict):
                                payload_keys = sorted(payload.keys())
                                if payload_keys:
                                    st.caption(f"Payload keys: {', '.join(payload_keys)}")

                    selector_key = f'audit_event_select_{case_id}'
                    options = [
                        f"{idx}. {event.get('agent', 'unknown')} - {event.get('stage', 'event')}"
                        for idx, event in enumerate(events, start=1)
                    ]
                    selected = st.selectbox('Full event viewer', options, key=selector_key)
                    selected_index = options.index(selected)
                    selected_event = events[selected_index]
                    st.subheader('Selected event')
                    if selected_event.get('_parse_error'):
                        st.code(selected_event.get('raw', ''), language='json')
                    else:
                        st.json(selected_event)
else:
    st.info('Select the sample tender and click Run analysis.')
