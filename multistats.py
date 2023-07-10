import os
import warnings
import re
import tqdm
import wandb
from traceback import print_exc
import plotly.express as px
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

import opendashboards.utils.utils as utils

from IPython.display import display

api= wandb.Api(timeout=60)
wandb.login(anonymous="allow")

def pull_wandb_runs(project='openvalidators', filters=None, min_steps=50, max_steps=100_000, ntop=10, summary_filters=None ):
    # TODO: speed this up by storing older runs
    
    all_runs = api.runs(project, filters=filters)
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
        if step < min_steps or step > max_steps:
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

    return pd.DataFrame(runs).astype({'state': 'category', 'hotkey': 'category', 'version': 'category', 'spec_version': 'category'})

def plot_gantt(df_runs):
    fig = px.timeline(df_runs,
                x_start="start_time", x_end="end_time", y="username", color="state",
                title="Timeline of Runs",
                category_orders={'run_name': df_runs.run_name.unique()},#,'username': sorted(df_runs.username.unique())},
                hover_name="run_name",
                hover_data=['hotkey','user','username','run_id','num_steps','num_completions'],
                color_discrete_map={'running': 'green', 'finished': 'grey', 'killed':'blue', 'crashed':'orange', 'failed': 'red'},
                opacity=0.3,
                width=1200,
                height=800,
                template="plotly_white",
    )
    fig.update_yaxes(tickfont_size=8, title='')
    fig.show()

def load_data(run_id, run_path=None, load=True, save=False, timeout=30):

    file_path = os.path.join('data/runs/',f'history-{run_id}.csv')

    if load and os.path.exists(file_path):
        df = pd.read_csv(file_path, nrows=None)
        # filter out events with missing step length
        df = df.loc[df.step_length.notna()]

        # detect list columns which as stored as strings
        list_cols = [c for c in df.columns if df[c].dtype == "object" and df[c].str.startswith("[").all()]
        # convert string representation of list to list
        df[list_cols] = df[list_cols].applymap(eval, na_action='ignore')

    else:
        # Download the history from wandb and add metadata
        run = api.run(run_path)
        df = pd.DataFrame(list(run.scan_history()))

        print(f'Downloaded {df.shape[0]} events from {run_path!r} with id {run_id!r}')

        if save:
            df.to_csv(file_path, index=False)

    # Convert timestamp to datetime.
    df._timestamp = pd.to_datetime(df._timestamp, unit="s")
    return df.sort_values("_timestamp")


def calculate_stats(df_long, rm_failed=True, rm_zero_reward=True, freq='H', save_path=None ):

    df_long._timestamp = pd.to_datetime(df_long._timestamp)
    # if dataframe has columns such as followup_completions and answer_completions, convert to multiple rows
    if 'completions' not in df_long.columns:
        df_long.set_index(['_timestamp','run_id'], inplace=True)
        df_schema = pd.concat([
            df_long[['followup_completions','followup_rewards']].rename(columns={'followup_completions':'completions', 'followup_rewards':'rewards'}),
            df_long[['answer_completions','answer_rewards']].rename(columns={'answer_completions':'completions', 'answer_rewards':'rewards'})
        ])
        df_long = df_schema.reset_index()

    if rm_failed:
        df_long = df_long.loc[ df_long.completions.str.len()>0 ]

    if rm_zero_reward:
        df_long = df_long.loc[ df_long.rewards>0 ]

    print(f'Calculating stats for dataframe with shape {df_long.shape}')

    g = df_long.groupby([pd.Grouper(key='_timestamp', axis=0, freq=freq), 'run_id'])

    stats = g.agg({'completions':['nunique','count'], 'rewards':['sum','mean','std']})

    stats.columns = ['_'.join(c) for c in stats.columns]
    stats['completions_diversity'] = stats['completions_nunique'] / stats['completions_count']
    stats = stats.reset_index()

    if save_path:        
        stats.to_csv(save_path, index=False)

    return stats


def clean_data(df):
    return df.dropna(subset=df.filter(regex='completions|rewards').columns, how='any').dropna(axis=1, how='all')

def explode_data(df):
    list_cols = utils.get_list_col_lengths(df)
    return utils.explode_data(df, list(list_cols.keys())).apply(pd.to_numeric, errors='ignore')


def process(run, load=True, save=False, freq='H'):

    try:
      
        stats_path = f'data/aggs/stats-{run["run_id"]}.csv'
        if os.path.exists(stats_path):
            print(f'Loaded stats file {stats_path}')
            return pd.read_csv(stats_path)

        # Load data and add extra columns from wandb run
        df = load_data(run_id=run['run_id'],
                    run_path=run['run_path'],
                    load=load,
                    save=save, 
                    save = (run['state'] != 'running') & run['end_time']
                    ).assign(**run.to_dict())
        # Clean and explode dataframe
        df_long = explode_data(clean_data(df))
        # Remove original dataframe from memory
        del df
        # Get and save stats
        return calculate_stats(df_long, freq=freq, save_path=stats_path)
    
    except Exception as e:
        print(f'Error processing run {run["run_id"]}: {e}')

if __name__ == '__main__':

    # TODO: flag to overwrite runs that were running when downloaded and saved: check if file date is older than run end time.
    
    filters = None# {"tags": {"$in": [f'1.1.{i}' for i in range(10)]}}
    # filters={'tags': {'$in': ['5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3']}} # Is foundation validator
    df_runs = pull_wandb_runs(ntop=500, filters=filters)#summary_filters=lambda s: s.get('augment_prompt'))

    os.makedirs('data/runs/', exist_ok=True)
    os.makedirs('data/aggs/', exist_ok=True)
    df_runs.to_csv('data/wandb.csv', index=False)
    
    display(df_runs)
    plot_gantt(df_runs)

    with ProcessPoolExecutor(max_workers=min(32, df_runs.shape[0])) as executor:
        futures = [executor.submit(process, run, load=True, save=True) for _, run in df_runs.iterrows()]

        # Use tqdm to add a progress bar
        results = []
        with tqdm.tqdm(total=len(futures)) as pbar:
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f'generated an exception: {print_exc(e)}')
                pbar.update(1)

    if not results:
        raise ValueError('No runs were successfully processed.')

   # Concatenate the results into a single dataframe
    df = pd.concat(results, ignore_index=True)

    df.to_csv('data/processed.csv', index=False)

    display(df)

    fig = px.line(df.astype({'_timestamp':str}),
              x='_timestamp',
              y='completions_diversity',
            #   y=['Unique','Total'],
        line_group='run_id',
        # color='hotkey',
        # color_discrete_sequence=px.colors.sequential.YlGnBu,
        title='Completion Diversity over Time',
        labels={'_timestamp':'', 'completions_diversity':'Diversity', 'uids':'UID','value':'counts', 'variable':'Completions'},
        width=800, height=600,
        template='plotly_white',
        ).update_traces(opacity=0.3)
    fig.show()

