import time
import numerize
import pandas as pd
import streamlit as st

def fmt(number):
    units = ['', 'k', 'M', 'B']
    magnitude = 0
    while abs(number) >= 1000 and magnitude < len(units) - 1:
        magnitude += 1
        number /= 1000

    if units[magnitude]:
        return f'{number:.2f}{units[magnitude]}'
    else:
        return f'{number:.0f}{units[magnitude]}'


@st.cache_data
def wandb(df_runs):

    # get rows where start time is older than 24h ago
    df_runs_old = df_runs.loc[df_runs.start_time < pd.to_datetime(time.time()-24*60*60, unit='s')]

    col1, col2, col3, col4 = st.columns(4)

    # Convert to appropriate units e.g. 1.2k instead of 1200.
    col1.metric('Runs', fmt(df_runs.shape[0]), delta=fmt(df_runs.shape[0]-df_runs_old.shape[0])+' (24h)')
    col2.metric('Hotkeys', fmt(df_runs.hotkey.nunique()), delta=fmt(df_runs.hotkey.nunique()-df_runs_old.hotkey.nunique())+' (24h)')
    col3.metric('Events', fmt(df_runs.num_steps.sum()), delta=fmt(df_runs.num_steps.sum()-df_runs_old.num_steps.sum())+' (24h)')
    col4.metric('Completions', fmt(df_runs.num_completions.sum()), delta=fmt(df_runs.num_completions.sum()-df_runs_old.num_completions.sum())+' (24h)')
    
    st.markdown('----')


@st.cache_data
def runs(df_long, n_runs):

    col1, col2, col3 = st.columns(3)
    col1.metric(label="Runs", value=n_runs)
    col1.metric(label="Events", value=df_long.shape[0])
    col2.metric(label="Followup UIDs", value=df_long.followup_uids.nunique())
    col2.metric(label="Answer UIDs", value=df_long.answer_uids.nunique())
    col3.metric(label="Unique Followups", value=df_long.followup_completions.nunique())
    col3.metric(label="Unique Answers", value=df_long.answer_completions.nunique())
    st.markdown('----')



@st.cache_data
def uids(df_long, src, uids=None):

    uid_col = f'{src}_uids'
    completion_col = f'{src}_completions'
    nsfw_col = f'{src}_nsfw_scores'
    reward_col = f'{src}_rewards'

    if uids:
        df_long = df_long.loc[df_long[uid_col].isin(uids)]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        label="Success %",
        value=f'{df_long.loc[df_long[completion_col].str.len() > 0].shape[0]/df_long.shape[0] * 100:.1f}',
        help='Number of successful completions divided by total number of events'
    )
    col2.metric(
        label="Diversity %",
        value=f'{df_long[completion_col].nunique()/df_long.shape[0] * 100:.1f}',
        help='Number of unique completions divided by total number of events'
    )
    # uniqueness can be expressed as the average number of unique completions per uid divided by all unique completions

    col3.metric(
        label="Uniqueness %",
        value=f'{df_long.groupby(uid_col)[completion_col].nunique().mean()/df_long[completion_col].nunique() * 100:.1f}',
        help='Average number of unique completions per uid divided by all unique completions'
    )
    col4.metric(
        label="Toxicity %",
        value=f'{df_long[nsfw_col].mean() * 100:.1f}' if nsfw_col in df_long.columns else '--',
        help='Average toxicity score of all events'
    )
    st.markdown('----')
