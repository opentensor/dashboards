import os
import re
import argparse
import tqdm
import wandb
import traceback
import plotly.express as px
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

import opendashboards.utils.utils as utils
import opendashboards.utils.aggregate as aggregate

from IPython.display import display

api= wandb.Api(timeout=60)
wandb.login(anonymous="allow")

def pull_wandb_runs(project='openvalidators', filters=None, min_steps=50, max_steps=100_000, ntop=10, netuid=None, summary_filters=None ):
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
        if netuid is not None and run.config.get('netuid') != netuid:
            continue
        step = summary.get('_step',0)
        if step < min_steps or step > max_steps:
            # warnings.warn(f'Skipped run `{run.name}` because it contains {step} events (<{min_steps})')
            continue

        prog_msg = f'Loading data {successful/ntop*100:.0f}% ({successful}/{ntop} runs, {n_events} events)'
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
            'netuid': run.config.get('netuid'),
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


def clean_data(df):
    return df.dropna(subset=df.filter(regex='completions|rewards').columns, how='any').dropna(axis=1, how='all')

def explode_data(df):
    list_cols = utils.get_list_col_lengths(df)
    return utils.explode_data(df, list(list_cols.keys())).apply(pd.to_numeric, errors='ignore')


def load_data(run_id, run_path=None, load=True, save=False, explode=True):

    file_path = os.path.join('data/runs/',f'history-{run_id}.parquet')

    if load and os.path.exists(file_path):
        df = pd.read_parquet(file_path)
        # filter out events with missing step length
        df = df.loc[df.step_length.notna()]

        # detect list columns which as stored as strings
        ignore_cols = ('moving_averaged_scores')
        list_cols = [c for c in df.columns if c not in ignore_cols and df[c].dtype == "object" and df[c].str.startswith("[").all()]
        # convert string representation of list to list
        # df[list_cols] = df[list_cols].apply(lambda x: eval(x, {'__builtins__': None}) if pd.notna(x) else x)
        try:
            df[list_cols] = df[list_cols].fillna('').applymap(eval, na_action='ignore')
        except ValueError as e:
            print(f'Error loading {file_path!r} when converting columns {list_cols} to list: {e}', flush=True)

    else:
        # Download the history from wandb and add metadata
        run = api.run(run_path)
        df = pd.DataFrame(list(run.scan_history()))

        # Remove rows with missing completions or rewards, which will be stuff related to weights
        df.dropna(subset=df.filter(regex='completions|rewards').columns, how='any', inplace=True)

        print(f'Downloaded {df.shape[0]} events from {run_path!r} with id {run_id!r}')

        # Clean and explode dataframe
        # overwrite object to free memory
        float_cols = df.filter(regex='reward').columns
        df = explode_data(clean_data(df)).astype({c: float for c in float_cols}).fillna({c: 0 for c in float_cols})

        if save:
            df.to_parquet(file_path, index=False)

    # Convert timestamp to datetime.
    df._timestamp = pd.to_datetime(df._timestamp, unit="s")
    return df.sort_values("_timestamp")


def calculate_stats(df_long, freq='H', save_path=None, ntop=3 ):

    df_long._timestamp = pd.to_datetime(df_long._timestamp)

    # if dataframe has columns such as followup_completions and answer_completions, convert to multiple rows
    if 'completions' not in df_long.columns:
        df_long.set_index(['_timestamp','run_id'], inplace=True)
        df_schema = pd.concat([
            df_long[['followup_completions','followup_rewards']].rename(columns={'followup_completions':'completions', 'followup_rewards':'rewards'}),
            df_long[['answer_completions','answer_rewards']].rename(columns={'answer_completions':'completions', 'answer_rewards':'rewards'})
        ])
        df_long = df_schema.reset_index()

    run_id = df_long['run_id'].iloc[0]
    # print(f'Calculating stats for run {run_id!r} dataframe with shape {df_long.shape}')

    # Approximate number of tokens in each completion
    df_long['completion_num_tokens'] = (df_long['completions'].astype(str).str.split().str.len() / 0.75).round()

    # TODO: use named aggregations
    reward_aggs = ['sum','mean','std','median','max',aggregate.nonzero_rate, aggregate.nonzero_mean, aggregate.nonzero_std, aggregate.nonzero_median]
    aggs = {
        'completions': ['nunique','count', aggregate.diversity, aggregate.successful_diversity, aggregate.success_rate],
        'completion_num_tokens': ['mean', 'std', 'median', 'max'],
        **{k: reward_aggs for k in df_long.filter(regex='reward') if df_long[k].nunique() > 1}
    }

    # Calculate tokens per second
    if 'completion_times' in df_long.columns:
        df_long['tokens_per_sec'] = df_long['completion_num_tokens']/(df_long['completion_times']+1e-6)
        aggs.update({
            'completion_times': ['mean','std','median','min','max'],
            'tokens_per_sec': ['mean','std','median','max'],
        })

    grouper = df_long.groupby(pd.Grouper(key='_timestamp', axis=0, freq=freq))
    # carry out main aggregations
    stats = grouper.agg(aggs)
    # carry out multi-column aggregations using apply
    diversity = grouper.apply(aggregate.successful_nonzero_diversity)
    # carry out top completions aggregations using apply
    top_completions = grouper.apply(aggregate.completion_top_stats, exclude='', ntop=ntop).unstack()
    
    # combine all aggregations, which have the same index
    stats = pd.concat([stats, diversity, top_completions], axis=1)
    
    # flatten multiindex columns
    stats.columns = ['_'.join([str(cc) for cc in c]) if isinstance(c, tuple) else str(c) for c in stats.columns]
    stats = stats.reset_index().assign(run_id=run_id)
    
    if save_path:
        stats.to_csv(save_path, index=False)

    return stats



def process(run, load=True, save=False, load_stats=True, freq='H', ntop=3):

    try:

        stats_path = f'data/aggs/stats-{run["run_id"]}.csv'
        if load_stats and os.path.exists(stats_path):
            print(f'Loaded stats file {stats_path!r}')
            return pd.read_csv(stats_path)

        # Load data and add extra columns from wandb run
        df_long = load_data(run_id=run['run_id'],
                    run_path=run['run_path'],
                    load=load,
                    save=save,
                    # save = (run['state'] != 'running') & run['end_time']
                    ).assign(**run.to_dict())
        assert isinstance(df_long, pd.DataFrame), f'Expected dataframe, but got {type(df_long)}'

        # Get and save stats
        return calculate_stats(df_long, freq=freq, save_path=stats_path, ntop=ntop)

    except Exception as e:
        print(f'Error processing run {run["run_id"]!r}:\t{e.__class__.__name__}: {e}',flush=True)
        print(traceback.format_exc())

def line_chart(df, col, title=None):
    title = title or col.replace('_',' ').title()
    fig = px.line(df.astype({'_timestamp':str}),
            x='_timestamp', y=col,
            line_group='run_id',
            title=f'{title} over Time',
            labels={'_timestamp':'', col: title, 'uids':'UID','value':'counts', 'variable':'Completions'},
            width=800, height=600,
            template='plotly_white',
        ).update_traces(opacity=0.2)

    fig.write_image(f'data/figures/{col}.png')
    fig.write_html(f'data/figures/{col}.html')
    return col


def parse_arguments():
    parser = argparse.ArgumentParser(description='Process wandb validator runs for a given netuid.')
    parser.add_argument('--load_runs',action='store_true', help='Load runs from file.')
    parser.add_argument('--repull_unfinished',action='store_true', help='Re-pull runs that were running when downloaded and saved.')
    parser.add_argument('--netuid', type=int, default=None, help='Network UID to use.')
    parser.add_argument('--ntop', type=int, default=1000, help='Number of runs to process.')
    parser.add_argument('--min_steps', type=int, default=100, help='Minimum number of steps to include.')
    parser.add_argument('--max_workers', type=int, default=32, help='Max workers to use.')
    parser.add_argument('--no_plot',action='store_true', help='Prevent plotting.')    
    parser.add_argument('--no_save',action='store_true', help='Prevent saving data to file.')
    parser.add_argument('--no_load',action='store_true', help='Prevent loading downloaded data from file.')
    parser.add_argument('--no_load_stats',action='store_true', help='Prevent loading stats data from file.')
    parser.add_argument('--freq', type=str, default='H', help='Frequency to aggregate data.')
    parser.add_argument('--completions_ntop', type=int, default=3, help='Number of top completions to include in stats.')

    return parser.parse_args()


if __name__ == '__main__':

    # TODO: flag to overwrite runs that were running when downloaded and saved: check if file date is older than run end time.

    args = parse_arguments()
    print(args)

    filters = None# {"tags": {"$in": [f'1.1.{i}' for i in range(10)]}}
    # filters={'tags': {'$in': ['5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3']}} # Is foundation validator
    if args.load_runs and os.path.exists('data/wandb.csv'):
        df_runs = pd.read_csv('data/wandb.csv')
        assert len(df_runs) >= args.ntop, f'Loaded {len(df_runs)} runs, but expected at least {args.ntop}'
        df_runs = df_runs.iloc[:args.ntop]
    else:
        df_runs = pull_wandb_runs(ntop=args.ntop,
                                min_steps=args.min_steps,
                                netuid=args.netuid,
                                filters=filters
                                )#summary_filters=lambda s: s.get('augment_prompt'))
        df_runs.to_csv('data/wandb.csv', index=False)


    os.makedirs('data/runs/', exist_ok=True)
    os.makedirs('data/aggs/', exist_ok=True)
    os.makedirs('data/figures/', exist_ok=True)

    display(df_runs)
    if not args.no_plot:
        plot_gantt(df_runs)

    with ProcessPoolExecutor(max_workers=min(args.max_workers, df_runs.shape[0])) as executor:
        futures = [executor.submit(
                            process,
                            run,
                            load=not args.no_load,
                            save=not args.no_save,
                            load_stats=not args.no_load_stats,
                            freq=args.freq,
                            ntop=args.completions_ntop
                    )
                   for _, run in df_runs.iterrows()
                   ]

        # Use tqdm to add a progress bar
        results = []
        with tqdm.tqdm(total=len(futures)) as pbar:
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f'-----------------------------\nWorker generated an exception in "process" function:\n{e.__class__.__name__}: {e}\n-----------------------------\n',flush=True)
                pbar.update(1)

    if not results:
        raise ValueError('No runs were successfully processed.')
    print(f'Processed {len(results)} runs.',flush=True)

   # Concatenate the results into a single dataframe
    df = pd.concat(results, ignore_index=True).sort_values(['_timestamp','run_id'], ignore_index=True)

    df.to_csv('data/processed.csv', index=False)
    print(f'Saved {df.shape[0]} rows to data/processed.csv')

    display(df)
    print(f'Unique values in columns:')
    display(df.nunique().sort_values())
    if not args.no_plot:
        
        plots = []

        cols = df.set_index(['run_id','_timestamp']).columns
        with ProcessPoolExecutor(max_workers=min(args.max_workers, len(cols))) as executor:
            futures = [executor.submit(line_chart, df, c) for c in cols]

            # Use tqdm to add a progress bar
            results = []
            with tqdm.tqdm(total=len(futures)) as pbar:
                for future in futures:
                    try:
                        result = future.result()
                        plots.append(result)
                    except Exception as e:
                        print(f'-----------------------------\nWorker generated an exception in "line_chart" function:\n{e.__class__.__name__}: {e}\n-----------------------------\n',flush=True)
                        # traceback.print_exc()                    
                    pbar.update(1)
        
        print(f'Saved {len(plots)} plots to data/figures/')


