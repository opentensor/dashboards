import numpy as np
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots

plotly_config = dict(width=800, height=600, template='plotly_white')

def plot_trace(df, col='emission', agg='mean', time_col='timestamp', ntop=10, hotkeys=None, hotkey_regex=None, abbrev=8, type='Miners', smooth=1, smooth_agg='mean', opacity=0.):
    
    if hotkeys is not None:
        df = df.loc[df.hotkey.isin(hotkeys)]
    if hotkey_regex is not None:
        df = df.loc[df.hotkey.str.contains(hotkey_regex)]
    
    # select hotkeys with highest average value of col (e.g. emission) over time
    top_miners = df.groupby('hotkey')[col].agg(agg).sort_values(ascending=False)
    print(f'Top miners by {col!r}:\n{top_miners}')
    stats = df.loc[df.hotkey.isin(top_miners.index[:ntop])].sort_values(by=time_col)

    # smooth values of col (e.g. emission) over time
    # stats[col] = stats.groupby('hotkey')[col].rolling(smooth).agg(smooth_agg).values
    
    stats['hotkey_abbrev'] = stats.hotkey.str[:abbrev]
    stats['coldkey_abbrev'] = stats.coldkey.str[:abbrev]
    stats['rank'] = stats.hotkey.map({k:i for i,k in enumerate(top_miners.index, start=1)})
    print(stats)
    
    y_label = col.title().replace('_',' ') + f' ({agg})'
    return px.line(stats.sort_values(by=[time_col,'rank']),
                x=time_col, y=col, color='coldkey_abbrev', line_group='hotkey_abbrev',
                hover_data=['hotkey','rank'],
                labels={col:y_label,'timestamp':'','coldkey_abbrev':f'Coldkey (first {abbrev} chars)','hotkey_abbrev':f'Hotkey (first {abbrev} chars)'},
                title=f'Top {ntop} {type}, by {y_label}',
                **plotly_config
            ).update_traces(opacity=opacity)
    
    
def plot_cabals(df, sel_col='coldkey', count_col='hotkey', time_col='timestamp', values=None, ntop=10, abbr=8, smooth=1, smooth_agg='mean', opacity=0.):
    
    if values is None:
        values = df[sel_col].value_counts().sort_values(ascending=False).index[:ntop].tolist()
        print(f'Automatically selected {sel_col!r} = {values!r}')
        
    df = df.loc[df[sel_col].isin(values)]
    rates = df.groupby([time_col,sel_col])[count_col].nunique().reset_index()
    
    # smoothing is hard
    # rates = rates.groupby(level=1).rolling(smooth, min_periods=1).agg(smooth_agg)
    
    abbr_col = f'{sel_col} (first {abbr} chars)'
    rates[abbr_col] = rates[sel_col].str[:abbr]
    return px.line(rates.melt(id_vars=[time_col,sel_col,abbr_col]), 
                x=time_col, y='value', color=abbr_col,
                labels={'value':f'Number of Unique {count_col.title()}s per {sel_col.title()}','timestamp':''}, 
                category_orders={abbr_col:[ v[:abbr] for v in values]},
                title=f'Unique {count_col.title()}s Associated with Top {ntop} {sel_col.title()}s',            
                **plotly_config
            ).update_traces(opacity=opacity)        
        
def plot_churn(df, time_col='timestamp', type='changed', step=1, smooth=1, smooth_agg='mean', opacity=0.5):
    """
    Produces a plotly figure which shows number of changed hotkeys in each step
    """
    
    def churn(s):
        results = [{'delta':np.nan}]
        for i, idx in enumerate(s.index[1:]):
    
            curr = s.loc[idx]
            prev = s.iloc[i]
            if type == 'changed':
                delta = curr.symmetric_difference(prev)
            elif type == 'added':
                delta = curr.difference(prev)
            elif type == 'removed':
                delta = prev.difference(curr)
            else:
                raise ValueError(f'Unknown type {type!r}')
            
            results.append({'delta': len(delta)})
    
        return pd.DataFrame(results, index=s.index)
 
    churn_frame = churn(df.iloc[::step].groupby(['block','timestamp']).hotkey.unique().apply(set))
    
    return px.line(churn_frame.rolling(smooth, min_periods=1).agg(smooth_agg).reset_index(),
                   x=time_col, y='delta', 
                   labels={'delta':f'Number of {type.title()} Hotkeys','timestamp':''}, 
                   hover_name='block',
                   **plotly_config
            ).update_traces(opacity=opacity)    
    
    
def plot_occupancy(df, time_col='timestamp',step=1, smooth=1, smooth_agg='mean', opacity=0.5):
    """
    Produces a plotly figure which shows number of unique hotkeys in each step
    """
    occupancy_frame = df.iloc[::step].assign(
        Type=df.iloc[::step].validator_trust.apply(lambda x: 'Miner' if x==0 else 'Validator')
        ).groupby(['Type','timestamp','block']).hotkey.nunique()

    # make two plots, with a secondary y axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    trace1 = px.line(occupancy_frame.loc['Miner'].rolling(smooth, min_periods=1).agg(smooth_agg).reset_index(), 
                     x='timestamp',y='hotkey', hover_name='block')
    trace2 = px.line(occupancy_frame.loc['Validator'].rolling(smooth, min_periods=1).agg(smooth_agg).reset_index(), 
                     x='timestamp', y='hotkey', hover_name='block')
    
    fig.add_trace(trace1.data[0])
    fig.add_trace(trace2.update_traces(line_color='red').data[0], secondary_y=True, row=1,col=1)
    
    fig.update_yaxes(title_text='Miner Hotkeys', secondary_y=False)  # Customize primary y-axis title
    fig.update_yaxes(title_text='Validator Hotkeys', secondary_y=True, tickfont=dict(color='red'), title=dict(font_color='red'))  # Customize secondary y-axis title
    
    return fig.update_layout( **plotly_config).update_traces(opacity=opacity)

def plot_animation(df, x='emission_sum', y='total_stake_sum', color='emission_mean', size='hotkey_nunique', step=10, opacity=0.5):
    
    agg_dict = {}
    for column_name in [x, y, color, size]:
        column, agg_name = column_name.rsplit('_', 1)

        if column not in agg_dict:
            agg_dict[column] = [agg_name]
        else:
            agg_dict[column].append(agg_name)
    
    # select every nth block
    if step>1:
        blocks_subset = df.block.unique()[::step]
        df = df.loc[df.block.isin(blocks_subset)]
        
    df_agg = df.groupby(['block','timestamp','coldkey']).agg({'hotkey':'nunique', 'ip':'nunique', **agg_dict})
    df_agg.columns = ['_'.join(col).strip() for col in df_agg.columns]
    print(df_agg.columns)
    
    return px.scatter(df_agg.reset_index(), 
                x=x, range_x=[-df_agg[x].max()*0.1, df_agg[x].max()*1.1],
                y=y, range_y=[-df_agg[y].max()*0.1, df_agg[y].max()*1.1],
                size=size, 
                opacity=opacity,
                color=color, 
                color_continuous_scale='BlueRed',
                animation_frame='block', 
                animation_group='coldkey',
                hover_name='coldkey',
                **plotly_config
            )   