import os
import re
import time
import pandas as pd
import streamlit as st


@st.cache_data
def wandb(df_runs):

    # get rows where start time is older than 24h ago
    df_runs_old = df_runs.loc[df_runs.start_time < pd.to_datetime(time.time()-24*60*60, unit='s')]

    col1, col2, col3 = st.columns(3)

    col1.metric('Runs', df_runs.shape[0], delta=f'{df_runs.shape[0]-df_runs_old.shape[0]} (24h)')
    col2.metric('Hotkeys', df_runs.hotkey.nunique(), delta=f'{df_runs.hotkey.nunique()-df_runs_old.hotkey.nunique()} (24h)')
    col3.metric('Events', df_runs.num_steps.sum(), delta=f'{df_runs.num_steps.sum()-df_runs_old.num_steps.sum()} (24h)')
    st.markdown('----')


@st.cache_data
def runs(df, df_long, selected_runs):

    col1, col2, col3 = st.columns(3)
    col1.metric(label="Runs", value=len(selected_runs))
    col1.metric(label="Events", value=df.shape[0]) #
    col2.metric(label="Followup UIDs", value=df_long.followup_uids.nunique())
    col2.metric(label="Answer UIDs", value=df_long.answer_uids.nunique())
    col3.metric(label="Followup Completions", value=df_long.followup_completions.nunique())
    col3.metric(label="Answer Completions", value=df_long.answer_completions.nunique())
    st.markdown('----')


    
@st.cache_data
def uids(df_long, src, uid=None):

    uid_col = f'{src}_uids'
    completion_col = f'{src}_completions'
    nsfw_col = f'{src}_nsfw_scores'
    reward_col = f'{src}_rewards'

    if uid is not None:
        df_long = df_long.loc[df_long[uid_col] == uid]

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="Success %",
        value=f'{df_long.loc[df_long[completion_col].str.len() > 0].shape[0]/df_long.shape[0] * 100:.1f}'
    )
    col2.metric(
        label="Diversity %",
        value=f'{df_long[completion_col].nunique()/df_long.shape[0] * 100:.1f}'
    )
    col3.metric(
        label="Toxicity %",
        value=f'{df_long[nsfw_col].mean() * 100:.1f}' if nsfw_col in df_long.columns else 'N/A'
    )
    st.markdown('----')
