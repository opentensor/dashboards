import numpy as np
import plotly.express as px

def plot_trace(df, col='emission', agg='mean', time_col='timestamp', ntop=10, hotkeys=None, hotkey_regex=None, abbrev=8, type='Miners'):
    
    if hotkeys is not None:
        df = df.loc[df.hotkey.isin(hotkeys)]
    if hotkey_regex is not None:
        df = df.loc[df.hotkey.str.contains(hotkey_regex)]
        
    top_miners = df.groupby('hotkey')[col].agg(agg).sort_values(ascending=False)
    
    stats = df.loc[df.hotkey.isin(top_miners.index[:ntop])].sort_values(by=time_col)
    
    stats['hotkey_abbrev'] = stats.hotkey.str[:abbrev]
    stats['coldkey_abbrev'] = stats.coldkey.str[:abbrev]
    stats['rank'] = stats.hotkey.map({k:i for i,k in enumerate(top_miners.index, start=1)})
    
    return px.line(stats.sort_values(by=[time_col,'rank']),
                    x=time_col, y=col, color='coldkey_abbrev', line_group='hotkey_abbrev',
                    hover_data=['hotkey','rank'],
                    labels={col:col.title(),'timestamp':'','coldkey_abbrev':f'Coldkey (first {abbrev} chars)','hotkey_abbrev':f'Hotkey (first {abbrev} chars)'},
                    title=f'Top {ntop} {type}, by {col.title()}',
                    template='plotly_white', width=800, height=600,
                    ).update_traces(opacity=0.7)
    
    
def plot_cabals(df, sel_col='coldkey', count_col='hotkey', time_col='timestamp', values=None, ntop=10, abbr=8):
    
    if values is None:
        values = df[sel_col].value_counts().sort_values(ascending=False).index[:ntop].tolist()
        print(f'Automatically selected {sel_col!r} = {values!r}')
        
    df = df.loc[df[sel_col].isin(values)]
    rates = df.groupby([time_col,sel_col])[count_col].nunique().reset_index()
    abbr_col = f'{sel_col} (first {abbr} chars)'
    rates[abbr_col] = rates[sel_col].str[:abbr]
    return px.line(rates.melt(id_vars=[time_col,sel_col,abbr_col]), 
            x=time_col, y='value', color=abbr_col,
            #facet_col='variable',  facet_col_wrap=1,
            labels={'value':f'Number of Unique {count_col.title()}s per {sel_col.title()}','timestamp':''}, 
            category_orders={abbr_col:[ v[:abbr] for v in values]},
            # title=f'Unique {count_col.title()}s Associated with Selected {sel_col.title()}s in Metagraph',
            title=f'Impact of Validators Update on Cabal',           
            width=800, height=600, template='plotly_white',
            )
        
        