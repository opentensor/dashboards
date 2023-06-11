import time
import pandas as pd
import streamlit as st
from opendashboards.assets import io, inspect, metric, plot

# prompt-based completion score stats
# instrospect specific RUN-UID-COMPLETION
# cache individual file loads

DEFAULT_PROJECT = "openvalidators"
DEFAULT_FILTERS = {"tags": {"$in": ["1.0.0", "1.0.1", "1.0.2", "1.0.3", "1.0.4"]}}
DEFAULT_SELECTED_RUNS = ['kt9bzxii']
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
        https://wandb.ai/opentensor-dev/openvalidators/table?workspace=default
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


### Wandb Runs ###
with st.sidebar:

    st.markdown('#')
    st.sidebar.header(":violet[Select] Runs")

    df_runs_subset = io.filter_dataframe(df_runs, demo_selection=df_runs.id.isin(DEFAULT_SELECTED_RUNS))
    n_runs = len(df_runs_subset)

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

        filter_selected_checkbox = st.checkbox('Filter to selected runs', value=True)
        df_to_show = df_runs_subset if filter_selected_checkbox else df_runs

        # TODO: make this editable so that runs can be selected directly from the table
        st.dataframe(
            df_to_show.assign(
                Selected=df_to_show.index.isin(df_runs_subset.index)
            ).set_index('Selected').sort_index(ascending=False),#.style.highlight_max(subset=df_runs_subset.index, color='lightgreen', axis=1),
            use_container_width=True,
        )

    if n_runs:
        df = io.load_data(df_runs_subset, load=True, save=True)
        df_long = inspect.explode_data(df)
        df_weights = inspect.weights(df)
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
        


### UID Health ###
with tab2:

    st.markdown('#')
    st.subheader("UID :violet[Health]")
    st.info(f"Showing UID health metrics for **{n_runs} selected runs**")

    uid_src = st.radio('Select one:', ['followup', 'answer'], horizontal=True, key='uid_src')

    metric.uids(df_long, uid_src)

    with st.expander(f'Show UID **{uid_src}** weights data for **{n_runs} selected runs**'):

        uids = st.multiselect('UID:', sorted(df_long[f'{uid_src}_uids'].unique()), key='uid')
        st.markdown('#')
        st.subheader(f"UID {uid_src.title()} :violet[Weights]")

        plot.weights(
                df_weights,
                uids=uids,
        )

    with st.expander(f'Show UID **{uid_src}** leaderboard data for **{n_runs} selected runs**'):

        st.markdown('#')
        st.subheader(f"UID {uid_src.title()} :violet[Leaderboard]")
        uid_col1, uid_col2 = st.columns(2)
        uid_ntop = uid_col1.slider('Number of UIDs:', min_value=1, max_value=50, value=DEFAULT_UID_NTOP, key='uid_ntop')
        uid_agg = uid_col2.selectbox('Aggregation:', ('mean','min','max','size','nunique'), key='uid_agg')

        plot.leaderboard(
                df,
                ntop=uid_ntop,
                group_on=f'{uid_src}_uids',
                agg_col=f'{uid_src}_rewards',
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
    completion_src = msg_col1.radio('Select one:', ['followup', 'answer'], horizontal=True, key='completion_src')
    completion_info.info(f"Showing **{completion_src}** completions for **{n_runs} selected runs**")

    completion_ntop = msg_col2.slider('Top k:', min_value=1, max_value=50, value=DEFAULT_COMPLETION_NTOP, key='completion_ntop')

    completion_col = f'{completion_src}_completions'
    reward_col = f'{completion_src}_rewards'
    uid_col = f'{completion_src}_uids'
    time_col = f'{completion_src}_times'

    completions = inspect.completions(df_long, completion_col)

    # Get completions with highest average rewards
    plot.leaderboard(
        df,
        ntop=completion_ntop,
        group_on=completion_col,
        agg_col=reward_col,
        agg='mean',
        alias=True
    )

    with st.expander(f'Show **{completion_src}** completion rewards data for **{n_runs} selected runs**'):

        st.markdown('#')
        st.subheader('Completion :violet[Rewards]')

        completion_select = st.multiselect('Completions:', completions.index, default=completions.index[:3].tolist())
        # completion_regex = st.text_input('Completion regex:', value='', key='completion_regex')

        plot.completion_rewards(
            df,
            completion_col=completion_col,
            reward_col=reward_col,
            uid_col=uid_col,
            ntop=completion_ntop,
            completions=completion_select,
        )


    with st.expander(f'Show **{completion_src}** completion length data for **{n_runs} selected runs**'):

        st.markdown('#')
        st.subheader('Completion :violet[Length]')

        words_checkbox = st.checkbox('Use words', value=True, key='words_checkbox')

        plot.completion_length_time(
            df,
            completion_col=completion_col,
            uid_col=uid_col,
            time_col=time_col,
            words=words_checkbox,
        )

### Prompt-based scoring ###
with tab4:
    # coming soon
    st.info('Prompt-based scoring coming soon')
    st.snow()

    # st.dataframe(df_long_long.filter(regex=prompt_src).head())

