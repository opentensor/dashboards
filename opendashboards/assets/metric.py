import time
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
def runs(df_long):
    
    col1, col2, col3, col4 = st.columns(4)
    print(df_long.columns)

    # Convert to appropriate units e.g. 1.2k instead of 1200.c
    col1.metric('Runs', fmt(df_long.run_id.nunique()))
    col2.metric('Hotkeys', fmt(df_long.hotkey.nunique()))
    col3.metric('Events', fmt(df_long.groupby(['run_id','_step']).ngroups))
    col4.metric('Completions', fmt(df_long.shape[0]))
    
    name_type = df_long.name.apply(lambda x: x if not x[-1].isdigit() else x[:-1])
    aggs = df_long.groupby(name_type).agg({'uids': 'nunique', 'completions': 'nunique'})
    print(aggs)
    for i,c in enumerate(st.columns(len(aggs))):
        name = aggs.index[i].title()
        uid_unique, comp_unique = aggs.iloc[i]
        c.metric(label=f'{name} UIDs', value=uid_unique) 
        c.metric(label=f'{name} Completions', value=comp_unique)

    st.markdown('----')



@st.cache_data
def uids(df_long, src, uids=None):

    nsfw_col = f'{src}_nsfw_scores'

    if uids:
        df_long = df_long.loc[df_long['uids'].isin(uids)]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        label="Success %",
        value=f'{df_long.loc[df_long["completions"].str.len() > 0].shape[0]/df_long.shape[0] * 100:.1f}',
        help='Number of successful completions divided by total number of events'
    )
    col2.metric(
        label="Diversity %",
        value=f'{df_long["completions"].nunique()/df_long.shape[0] * 100:.1f}',
        help='Number of unique completions divided by total number of events'
    )
    # uniqueness can be expressed as the average number of unique completions per uid divided by all unique completions
    # uniqueness is the shared completions between selected uids 

    col3.metric(
        label="Uniqueness %",
        value=f'{df_long.groupby("uids")["completions"].nunique().mean()/df_long["completions"].nunique() * 100:.1f}',
        help='Average number of unique completions per uid divided by all unique completions'
    )
    col4.metric(
        label="Toxicity %",
        value=f'{df_long[nsfw_col].mean() * 100:.1f}' if nsfw_col in df_long.columns else '--',
        help='Average toxicity score of all events'
    )
    st.markdown('----')
