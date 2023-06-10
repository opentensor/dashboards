import os
import re
import pandas as pd
import streamlit as st

import  opendashboards.utils.utils as utils

BASE_DIR = '.'#os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f'BASE_DIR = {BASE_DIR}')

@st.cache_data
def load_runs(project, filters, min_steps=10):
    runs = []
    msg = st.empty()
    for run in utils.get_runs(project, filters):
        step = run.summary.get('_step',0)
        if step < min_steps:
            msg.warning(f'Skipped run `{run.name}` because it contains {step} events (<{min_steps})')
            continue

        duration = run.summary.get('_runtime')
        end_time = run.summary.get('_timestamp')
        # extract values for selected tags
        rules = {'hotkey': re.compile('^[0-9a-z]{48}$',re.IGNORECASE), 'version': re.compile('^\\d\.\\d+\.\\d+$'), 'spec_version': re.compile('\\d{4}$')}
        tags = {k: tag for k, rule in rules.items() for tag in run.tags if rule.match(tag)}
        # include bool flag for remaining tags
        tags.update({k: k in run.tags for k in ('mock','custom_gating_model','nsfw_filter','outsource_scoring','disable_set_weights')})

        runs.append({
            'state': run.state,
            'num_steps': step,
            'entity': run.entity,
            'id': run.id,
            'name': run.name,
            'project': run.project,
            'url': run.url,
            'path': os.path.join(run.entity, run.project, run.id),
            'start_time': pd.to_datetime(end_time-duration, unit="s"),
            'end_time': pd.to_datetime(end_time, unit="s"),
            'duration': pd.to_datetime(duration, unit="s"),
            **tags
        })
    msg.empty()
    return pd.DataFrame(runs).astype({'state': 'category', 'hotkey': 'category', 'version': 'category', 'spec_version': 'category'})


@st.cache_data
def load_data(selected_runs, load=True, save=False):

    frames = []
    n_events = 0
    progress = st.progress(0, 'Loading data')
    info = st.empty()
    for i, idx in enumerate(selected_runs.index):
        run = selected_runs.loc[idx]
        prog_msg = f'Loading data {i/len(selected_runs)*100:.0f}% ({i}/{len(selected_runs)} runs, {n_events} events)'

        rel_path = os.path.join('data',f'history-{run.id}.csv')
        file_path = os.path.join(BASE_DIR,rel_path)

        if load and os.path.exists(file_path):
            progress.progress(i/len(selected_runs),f'{prog_msg}... **reading** `{rel_path}`')
            try:
                df = utils.load_data(file_path)
            except Exception as e:
                info.warning(f'Failed to load history from `{file_path}`')
                st.exception(e)
                continue
        else:
            progress.progress(i/len(selected_runs),f'{prog_msg}... **downloading** `{run.path}`')
            try:
                # Download the history from wandb
                df = utils.download_data(run.path)
                df.assign(**run.to_dict())
                if not os.path.exists('data/'):
                    os.makedirs(file_path)

                if save and run.state != 'running':
                    df.to_csv(file_path, index=False)
                    # st.info(f'Saved history to {file_path}')
            except Exception as e:
                info.warning(f'Failed to download history for `{run.path}`')
                st.exception(e)
                continue

        frames.append(df)
        n_events += df.shape[0]

    progress.empty()
    if not frames:
        info.error('No data loaded')
        st.stop()
    # Remove rows which contain chain weights as it messes up schema
    return pd.concat(frames)


