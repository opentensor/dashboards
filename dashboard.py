import time
import pandas as pd
import streamlit as st
from opendashboards.assets import io, inspect, metric, plot

# prompt-based completion score stats
# instrospect specific RUN-UID-COMPLETION
# cache individual file loads
# Hotkey churn

DEFAULT_PROJECT = "alpha-validators"
DEFAULT_FILTERS = {"tags": {"$in": [f'1.1.{i}' for i in range(10)]}}
DEFAULT_SELECTED_HOTKEYS = None
DEFAULT_SRC = 'followup'
DEFAULT_COMPLETION_NTOP = 10
DEFAULT_UID_NTOP = 10

# Set app config
st.set_page_config(
    page_title='Validator Dashboard',
    menu_items={
        'Report a bug': "https://github.com/opentensor/dashboards/issues",
        'About': """
        This dashboard is part of the OpenTensor project. \n
        To see runs in wandb, go to: \n
        https://wandb.ai/opentensor-dev/alpha-validators/table?workspace=default
        """
    },
    layout = "centered"
    )

st.title('Validator :red[Analysis] Dashboard :eyes:')
# add vertical space
st.markdown('#')
st.markdown('#')


with st.spinner(text=f'Checking wandb...'):
    df_runs = io.load_runs(project=DEFAULT_PROJECT, filters=DEFAULT_FILTERS, min_steps=10)

metric.wandb(df_runs)

# add vertical space
st.markdown('#')
st.markdown('#')

tab1, tab2, tab3, tab4 = st.tabs(["Raw Data", "UID Health", "Completions", "Prompt-based scoring"])

### Wandb Runs ###
with tab1:

    st.markdown('#')
    st.subheader(":violet[Run] Data")
    with st.expander(f'Show :violet[raw] wandb data'):

        edited_df = st.data_editor(
            df_runs.assign(Select=False).set_index('Select'),
            column_config={"Select": st.column_config.CheckboxColumn(required=True)},
            disabled=df_runs.columns,
            use_container_width=True,
        )
        df_runs_subset = df_runs[edited_df.index==True]
        n_runs = len(df_runs_subset)

    if n_runs:
        df = io.load_data(df_runs_subset, load=True, save=True)
        df = inspect.clean_data(df)
        print(f'\nNans in columns: {df.isna().sum()}')
        df_long = inspect.explode_data(df)
    else:
        st.info(f'You must select at least one run to load data')
        st.stop()

    metric.runs(df_long)

    st.markdown('#')
    st.subheader(":violet[Event] Data")
    with st.expander(f'Show :violet[raw] event data for **{n_runs} selected runs**'):
        raw_data_col1, raw_data_col2 = st.columns(2)
        use_long_checkbox = raw_data_col1.checkbox('Use long format', value=True)
        num_rows = raw_data_col2.slider('Number of rows:', min_value=1, max_value=100, value=10, key='num_rows')
        st.dataframe(df_long.head(num_rows) if use_long_checkbox else df.head(num_rows),
                     use_container_width=True)

# step_types = ['all']+['augment','followup','answer']#list(df.name.unique())
step_types = ['all']+list(df.task.unique())

### UID Health ###
# TODO: Live time - time elapsed since moving_averaged_score for selected UID was 0 (lower bound so use >Time)
# TODO: Weight - Most recent weight for selected UID (Add warning if weight is 0 or most recent timestamp is not current)
with tab2:

    st.markdown('#')
    st.subheader("UID :violet[Health]")
    st.info(f"Showing UID health metrics for **{n_runs} selected runs**")

    uid_src = st.radio('Select task type:', step_types, horizontal=True, key='uid_src')
    df_uid = df_long[df_long.task.str.contains(uid_src)] if uid_src != 'all' else df_long
        
    metric.uids(df_uid, uid_src)
    uids = st.multiselect('UID:', sorted(df_uid['uids'].unique()), key='uid')
    with st.expander(f'Show UID health data for **{n_runs} selected runs** and **{len(uids)} selected UIDs**'):
        st.markdown('#')
        st.subheader(f"UID {uid_src.title()} :violet[Health]")
        agg_uid_checkbox = st.checkbox('Aggregate UIDs', value=True)
        if agg_uid_checkbox:
            metric.uids(df_uid, uid_src, uids)
        else:
            for uid in uids:
                st.caption(f'UID: {uid}')
                metric.uids(df_uid, uid_src, [uid])

        st.subheader(f'Cumulative completion frequency')

        freq_col1, freq_col2 = st.columns(2)
        freq_ntop = freq_col1.slider('Number of Completions:', min_value=10, max_value=1000, value=100, key='freq_ntop')
        freq_rm_empty = freq_col2.checkbox('Remove empty (failed)', value=True, key='freq_rm_empty')
        freq_cumulative = freq_col2.checkbox('Cumulative', value=False, key='freq_cumulative')
        freq_normalize = freq_col2.checkbox('Normalize', value=True, key='freq_normalize')

        plot.uid_completion_counts(df_uid, uids=uids, src=uid_src, ntop=freq_ntop, rm_empty=freq_rm_empty, cumulative=freq_cumulative, normalize=freq_normalize)


    with st.expander(f'Show UID **{uid_src}** leaderboard data for **{n_runs} selected runs**'):

        st.markdown('#')
        st.subheader(f"UID {uid_src.title()} :violet[Leaderboard]")
        uid_col1, uid_col2 = st.columns(2)
        uid_ntop = uid_col1.slider('Number of UIDs:', min_value=1, max_value=50, value=DEFAULT_UID_NTOP, key='uid_ntop')
        uid_agg = uid_col2.selectbox('Aggregation:', ('mean','min','max','size','nunique'), key='uid_agg')

        plot.leaderboard(
                df_uid,
                ntop=uid_ntop,
                group_on='uids',
                agg_col='rewards',
                agg=uid_agg
            )


    with st.expander(f'Show UID **{uid_src}** diversity data for **{n_runs} selected runs**'):

        st.markdown('#')
        st.subheader(f"UID {uid_src.title()} :violet[Diversity]")
        rm_failed = st.checkbox(f'Remove failed **{uid_src}** completions', value=True)
        plot.uid_diversty(df, rm_failed)


### Completions ###
with tab3:

    st.markdown('#')
    st.subheader('Completion :violet[Leaderboard]')
    completion_info = st.empty()

    msg_col1, msg_col2 = st.columns(2)
    # completion_src = msg_col1.radio('Select one:', ['followup', 'answer'], horizontal=True, key='completion_src')
    completion_src = st.radio('Select task type:', step_types, horizontal=True, key='completion_src')
    df_comp = df_long[df_long.task.str.contains(completion_src)] if completion_src != 'all' else df_long
    
    completion_info.info(f"Showing **{completion_src}** completions for **{n_runs} selected runs**")

    completion_ntop = msg_col2.slider('Top k:', min_value=1, max_value=50, value=DEFAULT_COMPLETION_NTOP, key='completion_ntop')

    completions = inspect.completions(df_long, 'completions')

    # Get completions with highest average rewards
    plot.leaderboard(
        df_comp,
        ntop=completion_ntop,
        group_on='completions',
        agg_col='rewards',
        agg='mean',
        alias=True
    )

    with st.expander(f'Show **{completion_src}** completion rewards data for **{n_runs} selected runs**'):

        st.markdown('#')
        st.subheader('Completion :violet[Rewards]')

        completion_select = st.multiselect('Completions:', completions.index, default=completions.index[:3].tolist())
        # completion_regex = st.text_input('Completion regex:', value='', key='completion_regex')

        plot.completion_rewards(
            df_comp,
            completion_col='completions',
            reward_col='rewards',
            uid_col='uids',
            ntop=completion_ntop,
            completions=completion_select,
        )
        # TODO: show the UIDs which have used the selected completions


    with st.expander(f'Show **{completion_src}** completion length data for **{n_runs} selected runs**'):

        st.markdown('#')
        st.subheader('Completion :violet[Length]')

        completion_length_radio = st.radio('Use: ', ['characters','words','sentences'], key='completion_length_radio')

        # Todo: use color to identify selected completions/ step names/ uids
        plot.completion_length_time(
            df_comp,
            completion_col='completions',
            uid_col='uids',
            time_col='timings',
            length_opt=completion_length_radio,
        )

### Prompt-based scoring ###
with tab4:
    # coming soon
    st.info('Prompt-based scoring coming soon')
    st.snow()

    # st.dataframe(df_long_long.filter(regex=prompt_src).head())

