import os
import re
import pandas as pd
import streamlit as st

import  opendashboards.utils.utils as utils

from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)


@st.cache_data
def load_runs(project, filters, min_steps=10):
    runs = []
    n_events = 0
    successful = 0
    progress = st.progress(0, 'Fetching runs from wandb')
    msg = st.empty()

    all_runs = utils.get_runs(project, filters, api_key=st.secrets['WANDB_API_KEY'])
    for i, run in enumerate(all_runs):
        
        summary = run.summary
        step = summary.get('_step',-1) + 1
        if step < min_steps:
            msg.warning(f'Skipped run `{run.name}` because it contains {step} events (<{min_steps})')
            continue
        
        prog_msg = f'Loading data {i/len(all_runs)*100:.0f}% ({successful}/{len(all_runs)} runs, {n_events} events)'
        progress.progress(i/len(all_runs),f'{prog_msg}... **fetching** `{run.name}`')
        
        duration = summary.get('_runtime')
        end_time = summary.get('_timestamp')
        # extract values for selected tags
        rules = {'hotkey': re.compile('^[0-9a-z]{48}$',re.IGNORECASE), 'version': re.compile('^\\d\.\\d+\.\\d+$'), 'spec_version': re.compile('\\d{4}$')}
        tags = {k: tag for k, rule in rules.items() for tag in run.tags if rule.match(tag)}
        # include bool flag for remaining tags
        tags.update({k: k in run.tags for k in ('mock','custom_gating_model','nsfw_filter','outsource_scoring','disable_set_weights')})

        runs.append({
            'state': run.state,
            'num_steps': step,
            'num_completions': step*sum(len(v) for k, v in run.summary.items() if k.endswith('completions') and isinstance(v, list)),
            'entity': run.entity,
            'run_id': run.id,
            'run_name': run.name,
            'project': run.project,
            'url': run.url,
            'run_path': os.path.join(run.entity, run.project, run.id),
            'start_time': pd.to_datetime(end_time-duration, unit="s"),
            'end_time': pd.to_datetime(end_time, unit="s"),
            'duration': pd.to_timedelta(duration, unit="s").round('s'),
            **tags
        })
        n_events += step
        successful += 1

    progress.empty()
    msg.empty()
    return pd.DataFrame(runs).astype({'state': 'category', 'hotkey': 'category', 'version': 'category', 'spec_version': 'category'})


@st.cache_data
def load_data(selected_runs, load=True, save=False):

    frames = []
    n_events = 0
    successful = 0
    progress = st.progress(0, 'Loading data')
    info = st.empty()
    if not os.path.exists('data/'):
        os.makedirs('data/')
    for i, idx in enumerate(selected_runs.index):
        run = selected_runs.loc[idx]
        prog_msg = f'Loading data {i/len(selected_runs)*100:.0f}% ({successful}/{len(selected_runs)} runs, {n_events} events)'

        file_path = os.path.join('data',f'history-{run.run_id}.csv')

        if load and os.path.exists(file_path):
            progress.progress(i/len(selected_runs),f'{prog_msg}... **reading** `{file_path}`')
            try:
                df = utils.load_data(file_path)
            except Exception as e:
                info.warning(f'Failed to load history from `{file_path}`')
                st.exception(e)
                continue
        else:
            progress.progress(i/len(selected_runs),f'{prog_msg}... **downloading** `{run.run_path}`')
            try:
                # Download the history from wandb and add metadata
                df = utils.download_data(run.run_path).assign(**run.to_dict())

                print(f'Downloaded {df.shape[0]} events from `{run.run_path}`. Columns: {df.columns}')
                df.info()
                
                if save and run.state != 'running':
                    df.to_csv(file_path, index=False)
                    # st.info(f'Saved history to {file_path}')
            except Exception as e:
                info.warning(f'Failed to download history for `{run.run_path}`')
                st.exception(e)
                continue

        frames.append(df)
        n_events += df.shape[0]
        successful += 1

    progress.empty()
    if not frames:
        info.error('No data loaded')
        st.stop()
    # Remove rows which contain chain weights as it messes up schema
    return pd.concat(frames)


def filter_dataframe(df: pd.DataFrame, demo_selection=None) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe
        demo_selection (pd.Index): Index of runs to select (if demo)

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    filter_mode = st.sidebar.radio("Filter mode", ("Use demo", "Add filters"), index=0)

    run_msg = st.info("Select a single wandb run or compare multiple runs")

    if filter_mode == "Use demo":
        df = df.loc[demo_selection]
        run_msg.info(f"Selected {len(df)} runs")
        return df
    
    df = df.copy()

    # Try to convert datetimes into a standarrd format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]


    # Load data if new runs selected
    if len(df):
        run_msg.info(f"Selected {len(df)} runs")
    else:
        # open a dialog to select runs
        run_msg.error("Please select at least one run")
        # st.snow()
        # st.stop()

    return df