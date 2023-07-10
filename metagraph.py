import streamlit as st
from meta_utils import run_subprocess, load_metagraphs
# from opendashboards.assets import io, inspect, metric, plot
from meta_plotting import plot_trace, plot_cabals

DEFAULT_SRC = 'miner'
DEFAULT_NTOP = 10
DEFAULT_UID_NTOP = 10

# Set app config
st.set_page_config(
    page_title='Validator Dashboard',
    menu_items={
        'Report a bug': "https://github.com/opentensor/dashboards/issues",
        'About': """
        This dashboard is part of the OpenTensor project. \n
        """
    },
    layout = "centered"
    )

st.title('Metagraph :red[Analysis] Dashboard :eyes:')
# add vertical space
st.markdown('#')
st.markdown('#')


with st.spinner(text=f'Loading data...'):
    df = load_metagraphs()

blocks = df.block.unique()

# metric.wandb(df_runs)

# add vertical space
st.markdown('#')
st.markdown('#')

tab1, tab2, tab3, tab4 = st.tabs(["Health", "Miners", "Validators", "Block"])


### Wandb Runs ###
with tab1:

    st.markdown('#')
    st.header(":violet[Wandb] Runs")

    run_msg = st.info("Select a single run or compare multiple runs")
    selected_runs = st.multiselect(f'Runs ({len(df_runs)})', df_runs.id, default=DEFAULT_SELECTED_RUNS, key='runs')

    # Load data if new runs selected
    if not selected_runs:
        # open a dialog to select runs
        run_msg.error("Please select at least one run")
        st.snow()
        st.stop()

    df = io.load_data(df_runs.loc[df_runs.id.isin(selected_runs)], load=True, save=True)
    df_long = inspect.explode_data(df)
    df_weights = inspect.weights(df)

    metric.runs(df, df_long, selected_runs)

    with st.expander(f'Show :violet[raw] data for {len(selected_runs)} selected runs'):
        inspect.run_event_data(df_runs,df, selected_runs)


### UID Health ###
with tab2:

    st.markdown('#')
    st.header("UID :violet[Health]")
    st.info(f"Showing UID health metrics for **{len(selected_runs)} selected runs**")

    uid_src = st.radio('Select one:', ['followup', 'answer'], horizontal=True, key='uid_src')

    metric.uids(df_long, uid_src)

    with st.expander(f'Show UID **{uid_src}** weights data for **{len(selected_runs)} selected runs**'):

        uids = st.multiselect('UID:', sorted(df_long[f'{uid_src}_uids'].unique()), key='uid')
        st.markdown('#')
        st.subheader(f"UID {uid_src.title()} :violet[Weights]")

        plot.weights(
                df_weights,
                uids=uids,
        )
        
    with st.expander(f'Show UID **{uid_src}** leaderboard data for **{len(selected_runs)} selected runs**'):

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


    with st.expander(f'Show UID **{uid_src}** diversity data for **{len(selected_runs)} selected runs**'):

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
    completion_info.info(f"Showing **{completion_src}** completions for **{len(selected_runs)} selected runs**")
    
    completion_ntop = msg_col2.slider('Top k:', min_value=1, max_value=50, value=DEFAULT_COMPLETION_NTOP, key='completion_ntop')

    completion_col = f'{completion_src}_completions'
    reward_col = f'{completion_src}_rewards'
    uid_col = f'{completion_src}_uids'

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

    with st.expander(f'Show **{completion_src}** completion rewards data for **{len(selected_runs)} selected runs**'):

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


### Prompt-based scoring ###
with tab4:
    # coming soon
    st.info('Prompt-based scoring coming soon')

    # st.dataframe(df_long_long.filter(regex=prompt_src).head())

 