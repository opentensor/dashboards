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

import tqdm

import pandas as pd
import numpy as np
import networkx as nx

import plotly.express as px
import plotly.graph_objects as go

from typing import List, Union

plotly_config = {"width": 800, "height": 600, "template": "plotly_white"}

def plot_gantt(df_runs: pd.DataFrame, y='username'):
    fig = px.timeline(df_runs,
                x_start="start_time", x_end="end_time", y=y, color="state",
                title="Timeline of WandB Runs",
                category_orders={'run_name': df_runs.run_name.unique()},
                hover_name="run_name",
                hover_data=[col for col in ['hotkey','user','username','run_id','num_steps','num_completions'] if col in df_runs],
                color_discrete_map={'running': 'green', 'finished': 'grey', 'killed':'blue', 'crashed':'orange', 'failed': 'red'},
                opacity=0.3,
                width=1200,
                height=800,
                template="plotly_white",
    )
    # remove y axis ticks
    fig.update_yaxes(tickfont_size=8, title='')
    return fig

def plot_throughput(df: pd.DataFrame, n_minutes: int = 10) -> go.Figure:
    """Plot throughput of event log.

    Args:
        df (pd.DataFrame): Dataframe of event log.
        n_minutes (int, optional): Number of minutes to aggregate. Defaults to 10.
    """

    rate = df.resample(rule=f"{n_minutes}T", on="_timestamp").size()
    return px.line(
        x=rate.index, y=rate, title="Event Log Throughput", labels={"x": "", "y": f"Logs / {n_minutes} min"}, **plotly_config
    )


def plot_weights(scores: pd.DataFrame, ntop: int = 20, uids: List[Union[str, int]] = None) -> go.Figure:
    """Plot weights of uids.

    Args:
        scores (pd.DataFrame): Dataframe of scores. Should be indexed by timestamp and have one column per uid.
        ntop (int, optional): Number of uids to plot. Defaults to 20.
        uids (List[Union[str, int]], optional): List of uids to plot, should match column names. Defaults to None.
    """

    # Select subset of columns for plotting
    if not uids:
        uids = scores.columns[:ntop]
        print(f"Using first {ntop} uids for plotting: {uids}")

    return px.line(
        scores, y=uids, title="Moving Averaged Scores", labels={"_timestamp": "", "value": "Score"}, **plotly_config
    ).update_traces(opacity=0.7)


def plot_uid_diversty(df: pd.DataFrame, x: str = 'followup', y: str = 'answer', remove_unsuccessful: bool = False) -> go.Figure:
    """Plot uid diversity as measured by ratio of unique to total completions.

    Args:
        df (pd.DataFrame): Dataframe of event log.
    """
    return px.scatter(x=[1,2,3],y=[1,2,3])
    xrows = df.loc[df.name.str.contains(x)]
    yrows = df.loc[df.name.str.contains(y)]
    df = pd.merge(xrows, yrows, on='uid', suffixes=('_followup', '_answer'))

    df = df[list_cols].explode(column=list_cols)
    if remove_unsuccessful:
        # remove unsuccessful completions, as indicated by empty completions
        for col in completion_cols:
            df = df[df[col].str.len() > 0]

    frames = []
    for uid_col, completion_col, reward_col in zip(uid_cols, completion_cols, reward_cols):
        frame = df.groupby(uid_col).agg({completion_col: ["nunique", "size"], reward_col: "mean"})
        # flatten multiindex columns
        frame.columns = ["_".join(col) for col in frame.columns]
        frame["diversity"] = frame[f"{completion_col}_nunique"] / frame[f"{completion_col}_size"]
        frames.append(frame)

    merged = pd.merge(*frames, left_index=True, right_index=True, suffixes=("_followup", "_answer"))
    merged["reward_mean"] = merged.filter(regex="rewards_mean").mean(axis=1).astype(float)

    merged.index.name = "UID"
    merged.reset_index(inplace=True)

    return px.scatter(
        merged,
        x="diversity_followup",
        y="diversity_answer",
        opacity=0.35,
        # size="completions_size",
        color="reward_mean",
        hover_data=["UID"] + merged.columns.tolist(),
        marginal_x="histogram",
        marginal_y="histogram",
        color_continuous_scale=px.colors.sequential.Bluered,
        labels={"x": "Followup diversity", "y": "Answer diversity"},
        title="Diversity of completions by UID",
        **plotly_config,
    )


def plot_completion_rates(
    df: pd.DataFrame,
    msg_col: str = "completions",
    time_interval: str = "H",
    time_col: str = "_timestamp",
    ntop: int = 20,
    completions: List[str] = None,
    completion_regex: str = None,
) -> go.Figure:
    """Plot completion rates. Useful for identifying common completions and attacks.

    Args:
        df (pd.DataFrame): Dataframe of event log.
        msg_col (str, optional): List-like column containing completions. Defaults to 'completions'.
        time_interval (str, optional): Pandas time interval. Defaults to 'H'. See https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases
        time_col (str, optional): Column containing timestamps as pd.Datetime. Defaults to '_timestamp'.
        ntop (int, optional): Number of completions to plot. Defaults to 20.
        completions (List[str], optional): List of completions to plot. Defaults to None.
        completion_regex (str, optional): Regex to match completions. Defaults to None.

    """

    df = df[[time_col, msg_col]].explode(column=msg_col)

    if completions is None:
        completion_counts = df[msg_col].value_counts()
        if completion_regex is not None:
            completions = completion_counts[completion_counts.index.str.contains(completion_regex)].index[:ntop]
            print(f"Using {len(completions)} completions which match {completion_regex!r}: \n{completions}")
        else:
            completions = completion_counts.index[:ntop]
            print(f"Using top {len(completions)} completions: \n{completions}")

    period = df[time_col].dt.to_period(time_interval)

    counts = df.groupby([msg_col, period]).size()
    top_counts = counts.loc[completions].reset_index().rename(columns={0: "Size"})
    top_counts["Completion ID"] = top_counts[msg_col].map({k: f"{i}" for i, k in enumerate(completions, start=1)})

    return px.line(
        top_counts.astype({time_col: str}),
        x=time_col,
        y="Size",
        color="Completion ID",
        hover_data=[top_counts[msg_col].str.replace("\n", "<br>")],
        labels={time_col: f"Time, {time_interval}", "Size": f"Occurrences / {time_interval}"},
        title=f"Completion Rates for {len(completions)} Messages",
        **plotly_config,
    ).update_traces(opacity=0.7)


def plot_completion_rewards(
    df: pd.DataFrame,
    msg_col: str = "completions",
    reward_col: str = "rewards",
    time_col: str = "_timestamp",
    uid_col: str = "uids",
    ntop: int = 3,
    completions: List[str] = None,
    completion_regex: str = None,
) -> go.Figure:
    """Plot completion rewards. Useful for tracking common completions and their rewards.

    Args:
        df (pd.DataFrame): Dataframe of event log.
        msg_col (str, optional): List-like column containing completions. Defaults to 'completions'.
        reward_col (str, optional): List-like column containing rewards. Defaults to 'rewards'.
        time_col (str, optional): Column containing timestamps as pd.Datetime. Defaults to '_timestamp'.
        uid_col (str, optional): Column containing UIDs. Defaults to 'uids'.
        ntop (int, optional): Number of completions to plot. Defaults to 20.
        completions (List[str], optional): List of completions to plot. Defaults to None.
        completion_regex (str, optional): Regex to match completions. Defaults to None.

    """

    df = (
        df[[time_col, uid_col, msg_col, reward_col]]
        .explode(column=[msg_col, uid_col, reward_col])
        .rename(columns={uid_col: "UID"})
    )
    completion_counts = df[msg_col].value_counts()

    if completions is None:
        if completion_regex is not None:
            completions = completion_counts[completion_counts.index.str.contains(completion_regex)].index[:ntop]
            print(f"Using {len(completions)} completions which match {completion_regex!r}: \n{completions}")
        else:
            completions = completion_counts.index[:ntop]
            print(f"Using top {len(completions)} completions: \n{completions}")
    else:
        found_completions = [c for c in completions if c in completion_counts.index]
        print(f"Using {len(found_completions)}/{len(completions)} completions: \n{found_completions}")
        completions = found_completions
        
    # Get ranks of completions in terms of number of occurrences
    ranks = completion_counts.rank(method="dense", ascending=False).loc[completions].astype(int)

    # Filter to only the selected completions
    df = df.loc[df[msg_col].isin(completions)]
    df["rank"] = df[msg_col].map(ranks).astype(str)
    df["Total"] = df[msg_col].map(completion_counts)

    return px.scatter(
        df,
        x=time_col,
        y=reward_col,
        color="rank",
        hover_data=[msg_col, "UID", "Total"],
        category_orders={"rank": sorted(df["rank"].unique())},
        marginal_x="histogram",
        marginal_y="violin",
        labels={"rank": "Rank", reward_col: "Reward", time_col: ""},
        title=f"Rewards for {len(completions)} Messages",
        **plotly_config,
        opacity=0.35,
    )


def plot_leaderboard(
    df: pd.DataFrame,
    group_on: str = "uids",
    agg_col: str = "rewards",
    agg: str = "mean",
    ntop: int = 10,
    alias: bool = False,
) -> go.Figure:
    """Plot leaderboard for a given column. By default plots the top 10 UIDs by mean reward.

    Args:
        df (pd.DataFrame): Dataframe of event log.
        group_on (str, optional): Entities to use for grouping. Defaults to 'uids'.
        agg_col (str, optional): Column to aggregate. Defaults to 'rewards'.
        agg (str, optional): Aggregation function. Defaults to 'mean'.
        ntop (int, optional): Number of entities to plot. Defaults to 10.
        alias (bool, optional): Whether to use aliases for indices. Defaults to False.
    """
    df = df[[group_on, agg_col]].explode(column=[group_on, agg_col])

    rankings = df.groupby(group_on)[agg_col].agg(agg).sort_values(ascending=False).head(ntop).astype(float)
    if alias:
        index = rankings.index.map({name: str(i) for i, name in enumerate(rankings.index)})
    else:
        index = rankings.index.astype(str)

    return px.bar(
        x=rankings,
        y=index,
        color=rankings,
        orientation="h",
        labels={"x": f"{agg_col.title()}", "y": group_on, "color": ""},
        title=f"Leaderboard for {agg_col}, top {ntop} {group_on}",
        color_continuous_scale="BlueRed",
        opacity=0.35,
        hover_data=[rankings.index.astype(str)],
        **plotly_config,
    )



def plot_dendrite_rates(
    df: pd.DataFrame, uid_col: str = "uids", reward_col: str = "rewards", ntop: int = 20, uids: List[int] = None
) -> go.Figure:
    """Makes a bar chart of the success rate of dendrite calls for a given set of uids.

    Args:
        df (pd.DataFrame): Dataframe of event log.
        uid_col (str, optional): Column containing uids. Defaults to 'uids'.
        reward_col (str, optional): Column containing rewards. Defaults to 'rewards'.
        ntop (int, optional): Number of uids to plot. Defaults to 20.
        uids (List[int], optional): List of uids to plot. Defaults to None.

    """

    df = df[[uid_col, reward_col]].explode(column=[uid_col, reward_col]).rename(columns={uid_col: "UID"})
    df["success"] = df[reward_col] != 0

    if uids is None:
        uids = df["UID"].value_counts().head(ntop).index
    df = df.loc[df["UID"].isin(uids)]

    # get total and successful dendrite calls
    rates = df.groupby("UID").success.agg(["sum", "count"]).rename(columns={"sum": "Success", "count": "Total"})
    rates = rates.melt(ignore_index=False).reset_index()
    return px.bar(
        rates.astype({"UID": str}),
        x="value",
        y="UID",
        color="variable",
        labels={"value": "Number of Calls", "variable": ""},
        barmode="group",
        title="Dendrite Calls by UID",
        color_continuous_scale="Blues",
        opacity=0.35,
        **plotly_config,
    )

def plot_completion_length_time(
    df: pd.DataFrame,
    uid_col: str = "uids",
    completion_col: str = "completions",
    time_col: str = "timings",
    uids: List[int] = None,
    length_opt: str = 'characters',
) -> go.Figure:


    df = df[[uid_col, completion_col, time_col]].explode(column=[uid_col, completion_col, time_col])
    df["time"] = df[time_col].astype(float)
    if uids is not None:
        df = df.loc[df[uid_col].isin(uids)]
        
        
    if length_opt == 'characters':
        df["completion_length"] = df[completion_col].str.len()
    elif length_opt == 'words':
        df["completion_length"] = df[completion_col].str.split().str.len()
    elif length_opt == 'sentences':
        df["completion_length"] = df[completion_col].str.split('.').str.len()
    else:
        raise ValueError(f"length_opt must be one of 'words', 'characters', or 'sentences', got {length_opt}")

    return px.scatter(
        df,
        x='completion_length',
        y='time',
        color=uid_col if uids is not None else None,
        labels={"completion_length": f"Completion Length, {length_opt.title()}", "time": "Time (s)"},
        title=f"Completion Length vs Time, {length_opt.title()}",
        marginal_x="histogram",
        marginal_y="histogram",
        hover_data=[uid_col, completion_col],
        opacity=0.35,
        **plotly_config,
    )

def plot_uid_completion_counts(
    df: pd.DataFrame,
    uids: List[int],
    src: str = 'answer',
    rm_empty: bool = True,
    ntop: int = 100,
    cumulative: bool = False,
    normalize: bool = True,
) -> go.Figure:

    completion_col = f'completions'
    uid_col = f'uids'
    if rm_empty:
        df = df.loc[df[completion_col].str.len()>0]

    df = df.loc[df[uid_col].isin(uids)]

    g = df.groupby(uid_col)[completion_col].value_counts(normalize=normalize).reset_index(level=1)
    y_col = g.columns[-1]

    # rescale each group to have a max of 1 if normalize is True
    if cumulative:
        g[y_col] = g.groupby(level=0)[y_col].cumsum().transform(lambda x: x/x.max() if normalize else x)

    # get top n completions
    g = g.groupby(level=0).head(ntop)

    # # create a rank column which increments by one and resets when the uid changes
    g['rank'] = g.groupby(level=0).cumcount()+1

    return px.line(g.sort_index().reset_index(),
            x='rank',y=y_col,color=uid_col,
            labels={'rank':'Top Completions',uid_col:'UID',y_col:y_col.replace('_',' ').title()},
            title=f'{src.title()} Completion {y_col.replace("_"," ").title()}s by Rank',
            **plotly_config,
            ).update_traces(opacity=0.7)


def plot_network_embedding(
    df: pd.DataFrame,
    uid_col: str = "uids",
    completion_col: str = "completions",
    ntop: int = 1,
    uids: List[int] = None,
) -> go.Figure:
    """Plots a network embedding of the most common completions for a given set of uids.

    Args:
        df (pd.DataFrame): Dataframe of event log.

        uid_col (str, optional): Column containing uids. Defaults to 'uids'.
        completion_col (str, optional): Column containing completions. Defaults to 'completions'.
        ntop (int, optional): Number of uids to plot. Defaults to 20.
        hover_data (List[str], optional): Columns to include in hover data. Defaults to None.
        uids (List[int], optional): List of uids to plot. Defaults to None.

    # TODO: use value counts to use weighted similarity instead of a simple set intersection
    """
    top_completions = {}
    df = df[[uid_col, completion_col]].explode(column=[uid_col, completion_col])

    if uids is None:
        uids = df[uid_col].unique()
    # loop over UIDs and compute ntop most common completions
    for uid in tqdm.tqdm(uids, unit="UID"):
        c = df.loc[df[uid_col] == uid, completion_col].value_counts()
        top_completions[uid] = set(c.index[:ntop])

    a = np.zeros((len(uids), len(uids)))
    # now compute similarity matrix as a set intersection
    for i, uid in enumerate(uids):
        for j, uid2 in enumerate(uids[i + 1 :], start=i + 1):
            a[i, j] = a[j, i] = len(top_completions[uid].intersection(top_completions[uid2])) / ntop

    # make a graph from the similarity matrix
    g = nx.from_numpy_array(a)
    z = pd.DataFrame(nx.spring_layout(g)).T.rename(columns={0: "x", 1: "y"})
    z["UID"] = uids
    z["top_completions"] = pd.Series(top_completions).apply(list)

    # assign groups based on cliques (fully connected subgraphs)
    cliques = {
        uids[cc]: f"Group-{i}" if len(c) > 1 else "Other" for i, c in enumerate(nx.find_cliques(g), start=1) for cc in c
    }
    z["Group"] = z["UID"].map(cliques)

    return px.scatter(
        z.reset_index(),
        x="x",
        y="y",
        color="Group",
        title=f"Graph for Top {ntop} Completion Similarities",
        color_continuous_scale="BlueRed",
        hover_data=["UID", "top_completions"],
        opacity=0.35,
        **plotly_config,
    )
