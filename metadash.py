import os
import pandas as pd
import streamlit as st
from meta_utils import run_subprocess, load_metagraphs
# from opendashboards.assets import io, inspect, metric, plot
from meta_plotting import plot_trace, plot_cabals
import asyncio
from functools import lru_cache

## TODO: Read blocks from a big parquet file instead of loading all the pickles -- this is slow

def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
import bittensor

datadir='data/metagraph/1/'
blockfiles = sorted(int(filename.split('.')[0]) for filename in os.listdir(datadir))
DEFAULT_SRC = 'miner'
DEFAULT_BLOCK_START = blockfiles[0]
DEFAULT_BLOCK_END = blockfiles[-1]
DEFAULT_BLOCK_STEP = 1000
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

netuid = 1
subtensor = bittensor.subtensor(network='finney')
current_block = subtensor.get_current_block()

@lru_cache(maxsize=1)
def _metagraph(block):
    
    print('rerunning cache')
    return ( 
            subtensor.metagraph(netuid, block=block), 
            subtensor.metagraph(netuid, block=block - 7200),
            subtensor.burn(netuid=netuid, block=block),
            subtensor.burn(netuid=netuid, block=block - 7200),
    )
    
current_metagraph, yesterday_metagraph, current_burn, yesterday_burn = _metagraph(10*current_block//10)

current_vcount = current_metagraph.validator_permit.sum().item()
current_mcount = (~current_metagraph.validator_permit).sum().item()
yesterday_vcount = yesterday_metagraph.validator_permit.sum().item()
yesterday_mcount = (~yesterday_metagraph.validator_permit).sum().item()

mcol1, mcol2, mcol3, mcol4 = st.columns(4)
mcol1.metric('Block', current_block, delta='+7200 [24hr]')
mcol2.metric('Register Cost', f'{current_burn.unit}{current_burn.tao:.3f}', delta=f'{current_burn.tao-yesterday_burn.tao:.3f}')
mcol3.metric('Validators', current_vcount, delta=current_vcount-yesterday_vcount)
mcol4.metric('Miners', current_mcount, delta=current_mcount-yesterday_mcount)


st.markdown('#')    
st.markdown('#')    

bcol1, bcol2, bcol3 = st.columns([0.6, 0.1, 0.2])    
block_start, block_end = bcol1.select_slider(
    'Select a **block range**',
    options=blockfiles,
    value=(DEFAULT_BLOCK_START, DEFAULT_BLOCK_END),
    format_func=lambda x: f'{x:,}'
)

with bcol3:
    st.markdown('#')    
    st.button('Refresh', on_click=run_subprocess)


with st.spinner(text=f'Loading data...'):
    # df = load_metagraphs(block_start=block_start, block_end=block_end, block_step=DEFAULT_BLOCK_STEP)
    df = pd.read_parquet('blocks_600100_807300_100')

blocks = df.block.unique()

df_sel = df.loc[df.block.between(block_start, block_end)]


# add vertical space
st.markdown('#')
st.markdown('#')

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Miners", "Validators", "Block"])

miner_choices = ['total_stake','ranks','incentive','emission','consensus','trust','validator_trust','dividends']
cabal_choices = ['hotkey','ip','coldkey']

### Overview  ###
with tab1:
    
    x_col = st.radio('X-axis', ['block','timestamp'], index=0, horizontal=True)
    
    acol1, acol2 = st.columns([0.3, 0.7])
    sel_ntop = acol1.slider('Number:', min_value=1, max_value=50, value=10, key='sel_ntop')    
    #horizontal list
    miner_choice = acol2.radio('Select:', miner_choices, horizontal=True, index=0)
    st.plotly_chart(
        plot_trace(df_sel, time_col=x_col,col=miner_choice, ntop=sel_ntop),
        use_container_width=True
    )

    col1, col2 = st.columns(2)
    count_col = col1.radio('Count', cabal_choices, index=0, horizontal=True)
    y_col = col2.radio('Agg on', cabal_choices, index=2, horizontal=True)

    st.plotly_chart(
        plot_cabals(df_sel, time_col=x_col, count_col=count_col, sel_col=y_col, ntop=sel_ntop), 
        use_container_width=True
    )

with tab2:
    
    # plot of miner weights versus time/block
    pass