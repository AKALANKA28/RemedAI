from __future__ import annotations

import json

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = 'http://127.0.0.1:8000'
DEFAULT_TENDER_URL = 'https://www.waterboard.lk/tenders/'
SOURCES = {'National Water Supply and Drainage Board': 'waterboard'}


def summarize_payload(payload: dict) -> dict:
    return {
        key: value
        for key, value in payload.items()
        if key in {'model', 'decision', 'recommendation', 'overall_risk', 'case_id'}
    }


def event_label(index: int, event: dict) -> str:
    return f"{index + 1}. {event.get('agent', 'unknown')} - {event.get('stage', 'event')}"


def response_error_message(exc: requests.RequestException) -> str:
    response = getattr(exc, 'response', None)
    if response is None:
        return str(exc)
    try:
        detail = response.json().get('detail')
    except ValueError:
        detail = response.text
    return f'{response.status_code}: {detail or response.reason}'


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

with st.sidebar:
    st.header('Tender source')
    source_label = st.selectbox('Official source', list(SOURCES))
    tender_url = st.text_input('Tender URL', value=DEFAULT_TENDER_URL)
    query = st.text_area('User objective', value='Should we bid on this tender?')
    run_button = st.button('Analyze Tender', type='primary', width='stretch')
    st.markdown(
        '<p class="small-note">Paste a Water Board tender page or document URL. Backend must be running on port 8000.</p>',
        unsafe_allow_html=True,
    )

if run_button:
    with st.spinner('Running 5-agent workflow...'):
        try:
            response = requests.post(
                f'{BACKEND_URL}/api/v1/analyze/url',
                json={'source': SOURCES[source_label], 'tender_url': tender_url, 'query': query},
                timeout=300,
            )
            response.raise_for_status()
            st.session_state['result'] = response.json()
        except requests.RequestException as exc:
            st.error(f'Unable to analyze tender: {response_error_message(exc)}')

result = st.session_state.get('result')
if result:
    metric_cols = st.columns(4)
    metric_cols[0].metric('Recommendation', result['recommendation'])
    metric_cols[1].metric('Overall risk', result['overall_risk'])
    metric_cols[2].metric('Mandatory gaps', len(result['compliance']['mandatory_gaps']))
    metric_cols[3].metric('Plan tasks', len(result['plan']['tasks']))

    tab1, tab2, tab3, tab4, tab5 = st.tabs(['Executive Summary', 'Compliance', 'Risk', 'Plan', 'Audit Log'])

    with tab1:
        source = result.get('source', {})
        st.subheader(result['project_title'])
        st.write(result['summary'])
        st.write(
            {
                'source': source.get('issuer'),
                'source_url': source.get('source_url'),
                'document_url': source.get('document_url'),
                'saved_document_path': source.get('saved_document_path'),
            }
        )
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
        case_id = result['case_id']
        audit_key = f'audit:{case_id}'
        if st.button('Load audit log', width='content') or audit_key in st.session_state:
            try:
                if audit_key not in st.session_state:
                    audit_response = requests.get(f'{BACKEND_URL}/api/v1/cases/{case_id}/audit', timeout=10)
                    audit_response.raise_for_status()
                    st.session_state[audit_key] = audit_response.json()

                audit = st.session_state[audit_key]
                events = audit.get('events', [])
                raw_audit = audit.get('raw', '')

                st.download_button(
                    'Download audit JSONL',
                    data=raw_audit,
                    file_name=f'{case_id}-audit.jsonl',
                    mime='application/jsonl',
                    width='content',
                )

                for index, event in enumerate(events):
                    with st.expander(event_label(index, event)):
                        st.write(
                            {
                                'timestamp': event.get('timestamp'),
                                'agent': event.get('agent'),
                                'stage': event.get('stage'),
                                'payload_summary': summarize_payload(event.get('payload', {})),
                            }
                        )

                if events:
                    selected_label = st.selectbox(
                        'View full event',
                        [event_label(index, event) for index, event in enumerate(events)],
                    )
                    selected_index = int(selected_label.split('.', 1)[0]) - 1
                    st.code(json.dumps(events[selected_index], indent=2), language='json')
            except requests.RequestException as exc:
                st.warning(f'Audit log is not available yet: {exc}')
else:
    st.info('Paste an official tender URL and click Analyze Tender.')
