# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import os
import re
import tqdm
import wandb
import pandas as pd

from traceback import format_exc
from pandas.api.types import is_list_like

from typing import List, Dict, Any, Union


def pull_wandb_runs(project='openvalidators', filters=None, min_steps=50, ntop=10, summary_filters=None ):
    all_runs = get_runs(project, filters)
    print(f'Using {ntop}/{len(all_runs)} runs with more than {min_steps} events')
    pbar = tqdm.tqdm(all_runs)
    runs = []
    n_events = 0
    successful = 0
    for i, run in enumerate(pbar):

        summary = run.summary
        if summary_filters is not None and not summary_filters(summary):
            continue
        step = summary.get('_step',0)
        if step < min_steps:
            # warnings.warn(f'Skipped run `{run.name}` because it contains {step} events (<{min_steps})')
            continue

        prog_msg = f'Loading data {i/len(all_runs)*100:.0f}% ({successful}/{len(all_runs)} runs, {n_events} events)'
        pbar.set_description(f'{prog_msg}... **fetching** `{run.name}`')

        duration = summary.get('_runtime')
        end_time = summary.get('_timestamp')
        # extract values for selected tags
        rules = {'hotkey': re.compile('^[0-9a-z]{48}$',re.IGNORECASE), 'version': re.compile('^\\d\.\\d+\.\\d+$'), 'spec_version': re.compile('\\d{4}$')}
        tags = {k: tag for k, rule in rules.items() for tag in run.tags if rule.match(tag)}
        # include bool flag for remaining tags
        tags.update({k: True for k in run.tags if k not in tags.keys() and k not in tags.values()})

        runs.append({
            'state': run.state,
            'num_steps': step,
            'num_completions': step*sum(len(v) for k, v in run.summary.items() if k.endswith('completions') and isinstance(v, list)),
            'entity': run.entity,
            'user': run.user.name,
            'username': run.user.username,
            'run_id': run.id,
            'run_name': run.name,
            'project': run.project,
            'run_url': run.url,
            'run_path': os.path.join(run.entity, run.project, run.id),
            'start_time': pd.to_datetime(end_time-duration, unit="s"),
            'end_time': pd.to_datetime(end_time, unit="s"),
            'duration': pd.to_timedelta(duration, unit="s").round('s'),
            **tags
        })
        n_events += step
        successful += 1
        if successful >= ntop:
            break

    cat_cols = ['state', 'hotkey', 'version', 'spec_version']
    return pd.DataFrame(runs).astype({k: 'category' for k in cat_cols if k in runs[0]})



def get_runs(project: str = "openvalidators", filters: Dict[str, Any] = None, return_paths: bool = False, api_key: str = None) -> List:
    """Download runs from wandb.

    Args:
        project (str): Name of the project. Defaults to 'openvalidators' (community project)
        filters (Dict[str, Any], optional): Optional run filters for wandb api. Defaults to None.
        return_paths (bool, optional): Return only run paths. Defaults to False.

    Returns:
        List[wandb.apis.public.Run]: List of runs or run paths (List[str]).
    """
    api = wandb.Api(api_key=api_key)
    wandb.login(anonymous="allow")

    runs = api.runs(project, filters=filters)
    if return_paths:
        return [os.path.join(run.entity, run.project, run.id) for run in runs]
    else:
        return runs


def download_data(run_path: Union[str, List] = None, timeout: float = 600, api_key: str = None) -> pd.DataFrame:
    """Download data from wandb.

    Args:
        run_path (Union[str, List], optional): Path to run or list of paths. Defaults to None.
        timeout (float, optional): Timeout for wandb api. Defaults to 600.

    Returns:
        pd.DataFrame: Dataframe of event log.
    """
    api = wandb.Api(api_key=api_key, timeout=timeout)
    wandb.login(anonymous="allow")

    if isinstance(run_path, str):
        run_path = [run_path]

    frames = []
    total_events = 0
    pbar = tqdm.tqdm(sorted(run_path), desc="Loading history from wandb", total=len(run_path), unit="run")
    for path in pbar:
        run = api.run(path)

        frame = pd.DataFrame(list(run.scan_history()))
        frames.append(frame)
        total_events += len(frame)

        pbar.set_postfix({"total_events": total_events})

    df = pd.concat(frames)

    # Convert timestamp to datetime.
    df._timestamp = pd.to_datetime(df._timestamp, unit="s")
    df.sort_values("_timestamp", inplace=True)

    return df


def read_data(path: str, nrows: int = None):
    """Load data from csv."""
    df = pd.read_csv(path, nrows=nrows)
    # filter out events with missing step length
    df = df.loc[df.step_length.notna()]

    # detect list columns which as stored as strings
    list_cols = [c for c in df.columns if df[c].dtype == "object" and df[c].str.startswith("[").all()]
    # convert string representation of list to list
    df[list_cols] = df[list_cols].applymap(eval, na_action='ignore')

    return df

def load_data(selected_runs, load=True, save=False, explode=True, datadir='data/'):

    frames = []
    n_events = 0
    successful = 0
    if not os.path.exists(datadir):
        os.makedirs(datadir)

    pbar = tqdm.tqdm(selected_runs.index, desc="Loading runs", total=len(selected_runs), unit="run")
    for i, idx in enumerate(pbar):
        run = selected_runs.loc[idx]
        prog_msg = f'Loading data {i/len(selected_runs)*100:.0f}% ({successful}/{len(selected_runs)} runs, {n_events} events)'

        file_path = os.path.join(datadir,f'history-{run.run_id}.csv')

        if (load is True and os.path.exists(file_path)) or (callable(load) and load(run.to_dict())):
            pbar.set_description(f'{prog_msg}... **reading** `{file_path}`')
            try:
                df = read_data(file_path)
            except Exception as e:
                print(f'Failed to load history from `{file_path}`: {format_exc(e)}')
                continue
        else:
            pbar.set_description(f'{prog_msg}... **downloading** `{run.run_path}`')
            try:
                # Download the history from wandb and add metadata
                df = download_data(run.run_path).assign(**run.to_dict())
                if explode:
                    df = explode_data(df)

                print(f'Downloaded {df.shape[0]} events from `{run.run_path}`. Columns: {df.columns}')

                if save is True or (callable(save) and save(run.to_dict())):
                    df.to_csv(file_path, index=False)
                    print(f'Saved {df.shape[0]} events to `{file_path}`')

            except Exception as e:
                print(f'Failed to download history for `{run.run_path}`: {e}')
                continue

        frames.append(df)
        n_events += df.shape[0]
        successful += 1

    # Remove rows which contain chain weights as it messes up schema
    return pd.concat(frames)


def explode_data(df: pd.DataFrame, list_cols: List[str] = None, list_len: int = None) -> pd.DataFrame:
    """Explode list columns in dataframe so that each element in the list is a separate row.

    Args:
        df (pd.DataFrame): Dataframe of event log.
        list_cols (List[str], optional): List of columns to explode. Defaults to None.
        list_len (int, optional): Length of list. Defaults to None.

    Returns:
        pd.DataFrame: Dataframe with exploded list columns.
    """
    if list_cols is None:
        list_cols = [c for c in df.columns if df[c].apply(is_list_like).all()]
        print(f"Exploding {len(list_cols)}) list columns with {list_len} elements: {list_cols}")
    if list_len:
        list_cols = [c for c in list_cols if df[c].apply(len).unique()[0] == list_len]
        print(f"Exploding {len(list_cols)}) list columns with {list_len} elements: {list_cols}")

    return df.explode(column=list_cols)


def get_list_col_lengths(df: pd.DataFrame) -> Dict[str, int]:
    """Helper function to get the length of list columns."""
    list_col_lengths = {c: sorted(df[c].apply(len).unique()) for c in df.columns if df[c].apply(is_list_like).all()}
    varying_lengths = {c: v for c, v in list_col_lengths.items() if len(v) > 1}

    if len(varying_lengths) > 0:
        print(f"The following columns have varying lengths: {varying_lengths}")

    return {c: v[0] for c, v in list_col_lengths.items() if v}
