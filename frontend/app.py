from __future__ import annotations

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

with st.sidebar:
    st.header('Run settings')
    sample_id = st.selectbox('Sample tender', ['remediation_tender'])
    query = st.text_area('User objective', value='Should we bid on this tender?')
    run_button = st.button('Run analysis', type='primary', use_container_width=True)
    st.markdown('<p class="small-note">Backend must be running on port 8000.</p>', unsafe_allow_html=True)
    try:
        health = requests.get(f'{BACKEND_URL}/health', timeout=3).json()
        st.caption('Active local models')
        st.json(health.get('agent_models', {}))
    except requests.RequestException:
        st.caption('Model map appears after the backend starts.')

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
    metric_cols = st.columns(4)
    metric_cols[0].metric('Recommendation', result['recommendation'])
    metric_cols[1].metric('Overall risk', result['overall_risk'])
    metric_cols[2].metric('Mandatory gaps', len(result['compliance']['mandatory_gaps']))
    metric_cols[3].metric('Plan tasks', len(result['plan']['tasks']))

    tab1, tab2, tab3, tab4 = st.tabs(['Executive Summary', 'Compliance', 'Risk', 'Plan & Trace'])

    with tab1:
        st.subheader(result['project_title'])
        st.write(result['summary'])
        st.json(result['artifacts'])

    with tab2:
        df = pd.DataFrame(result['compliance']['rows'])
        st.dataframe(df, use_container_width=True)

    with tab3:
        risk_df = pd.DataFrame(result['risk']['risks'])
        st.dataframe(risk_df, use_container_width=True)
        st.write('Rationale:')
        for reason in result['risk']['rationale']:
            st.markdown(f'- {reason}')

    with tab4:
        plan_df = pd.DataFrame(result['plan']['tasks'])
        st.dataframe(plan_df, use_container_width=True)
        st.subheader('Agent audit trail')
        for event in result['audit_trail']:
            with st.expander(f"{event['agent']} - {event['stage']}"):
                st.json(event['payload'])
else:
    st.info('Select the sample tender and click Run analysis.')
