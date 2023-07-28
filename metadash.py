import os
import time
import pandas as pd
import streamlit as st
from meta_utils import run_subprocess, load_metagraphs
# from opendashboards.assets import io, inspect, metric, plot
import meta_plotting as plotting 
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

netuid = 1
datadir=f'data/metagraph/{netuid}/'
blockfiles = sorted(int(filename.split('.')[0]) for filename in os.listdir(datadir) if filename.split('.')[0].isdigit())
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

subtensor = bittensor.subtensor(network='finney')
current_block = subtensor.get_current_block()

@st.cache_data
def _metagraph(block, subnet):
    
    print(f'rerunning cache with block {block}')
    return ( 
            subtensor.metagraph(subnet, block=block), 
            subtensor.metagraph(subnet, block=block - 7200),
            subtensor.burn(netuid=subnet, block=block),
            subtensor.burn(netuid=subnet, block=block - 7200),
    )

current_metagraph, yesterday_metagraph, current_burn, yesterday_burn = _metagraph(10*(current_block//10), netuid)
current_validators = current_metagraph.validator_permit[current_metagraph.validator_trust > 0.0]
yesterday_validators = yesterday_metagraph.validator_permit[yesterday_metagraph.validator_trust > 0.0]
current_vcount = current_validators.sum().item()
current_mcount = (current_metagraph.trust > 0.0).sum().item()
yesterday_vcount = yesterday_validators.sum().item()
yesterday_mcount = (yesterday_metagraph.trust > 0.0).sum().item()

st.markdown('#')    

mcol1, mcol2, mcol3, mcol4 = st.columns(4)
mcol1.metric('Block', current_block, delta='+7200 [24hr]')
mcol2.metric('Register Cost', f'{current_burn.unit}{current_burn.tao:.3f}', delta=f'{current_burn.tao-yesterday_burn.tao:.3f}')
mcol3.metric('Validators', current_vcount, delta=current_vcount-yesterday_vcount)
mcol4.metric('Miners', current_mcount, delta=current_mcount-yesterday_mcount)


st.markdown('#')    


with st.sidebar:
    st.title('Options')
    st.markdown('#')    
    
    netuid = st.selectbox('Netuid', [1,11], index=0)

    st.markdown('#')    

    c1, c2 = st.columns([0.7,0.3])
    staleness =  current_block - blockfiles[-1]
    msg = c1.warning(f'Out of date ({staleness})') if staleness >= 100 else c1.info('Up to date')
    if c2.button('Update', type='primary'):
        msg.info('Downloading')      
        return_code = run_subprocess()
        if return_code == 0:
            msg.success('Up to date')
            time.sleep(1)
            msg.empty()
        else:
            msg.error('Error')

    st.markdown('#')    
    
    block_start, block_end = st.select_slider(
        'Select a **block range**',
        options=blockfiles,
        value=(DEFAULT_BLOCK_START, DEFAULT_BLOCK_END),
        format_func=lambda x: f'{x:,}'
    )
    
    st.markdown('#')    
    st.markdown('#')    
    # horizontal line
    st.markdown('<hr>', unsafe_allow_html=True)

    r1c1, r1c2 = st.columns(2)
    x = r1c1.selectbox('**Time axis**', ['block','timestamp'], index=0)
    color = r1c2.selectbox('**Color**', ['coldkey','hotkey','ip'], index=0)
    r2c1, r2c2 = st.columns(2)
    ntop = r2c1.slider('**Sample top**', min_value=1, max_value=50, value=10, key='sel_ntop')    
    opacity = r2c2.slider('**Opacity**', min_value=0., max_value=1., value=0.5, key='opacity')    
    r3c1, r3c2 = st.columns(2)
    smooth = r3c1.slider('Smoothing', min_value=1, max_value=100, value=1, key='sel_churn_smooth')
    smooth_agg = r3c2.radio('Smooth Aggregation', ['mean','std','max','min','sum'], horizontal=True, index=0)
        

with st.spinner(text=f'Loading data...'):
    # df = load_metagraphs(block_start=block_start, block_end=block_end, block_step=DEFAULT_BLOCK_STEP)
    df = pd.read_parquet(os.path.join(datadir,'df.parquet'))

blocks = df.block.unique()

df_sel = df.loc[df.block.between(block_start, block_end)].sort_values(by='block')
miners = df_sel.loc[df_sel.validator_trust == 0]
validators = df_sel.loc[df_sel.validator_trust > 0]

# add vertical space
st.markdown('#')
st.markdown('#')

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Miners", "Validators", "Block"])

validator_choices = ['total_stake','incentive','emission','consensus','validator_trust','dividends']
miner_choices = ['total_stake','incentive','emission','consensus','trust']
cabal_choices = ['hotkey','ip','coldkey']
cabal_choices.remove(color)

### Overview  ###
with tab1:
    
    st.markdown('#')
    st.markdown('#')
    st.subheader('Hotkey Churn')
    st.info('**Churn** *measures the change in network participants over time*')
    
    churn_choice = st.radio('Hotkey event', ['changed','added','removed'], horizontal=True, index=0)

    st.plotly_chart(
        plotting.plot_churn(df_sel, time_col=x, type=churn_choice, smooth=smooth, smooth_agg=smooth_agg, opacity=opacity),
        use_container_width=True
    )
    
    st.markdown('#')
    st.markdown('#')
    st.subheader('Network Occupancy')
    st.info('**Occupancy** *measures the number of network participants at a given time*')    
    st.plotly_chart(
        plotting.plot_occupancy(df_sel, time_col=x, smooth=smooth, smooth_agg=smooth_agg, opacity=opacity),
        use_container_width=True
    )

animation_aggs = ['mean','sum','std','max','min']
mac_choices = [f'{col}_{agg}' for col in miner_choices for agg in animation_aggs]+['hotkey_nunique','ip_nunique']
vac_choices = [f'{col}_{agg}' for col in validator_choices for agg in animation_aggs]+['hotkey_nunique','ip_nunique']

with tab2:
    
    st.markdown('#')
    st.markdown('#')
    st.subheader('Miner Activity')
    st.info('**Activity** *shows the change in stake and emission over time for **miners**, grouped by coldkey*')
    
    mac1, mac2, mac3, mac4 = st.columns(4)
    mac_x = mac1.selectbox('**x**', mac_choices, index=mac_choices.index('emission_mean'))
    mac_y = mac2.selectbox('**y**', mac_choices, index=mac_choices.index('trust_mean'))
    mac_size = mac3.selectbox('**marker size**', mac_choices, index=mac_choices.index('hotkey_nunique'))
    mac_color = mac4.selectbox('**marker color**', mac_choices, index=mac_choices.index('total_stake_sum'))

    st.plotly_chart(
        plotting.plot_animation(miners, x=mac_x, y=mac_y, color=mac_color, size=mac_size, opacity=opacity),
        use_container_width=True
    )    
    
    miner_choice = st.radio('Select:', miner_choices, horizontal=True, index=0)
    with st.expander(f'Show **{miner_choice}** trends for top **{ntop}** miners'):
    
        st.plotly_chart(
            plotting.plot_trace(miners, time_col=x, col=miner_choice, ntop=ntop, smooth=smooth, smooth_agg=smooth_agg, opacity=opacity),
            use_container_width=True
        )

    count_col = st.radio('Count', cabal_choices, index=0, horizontal=True, key='sel_miner_count')
    with st.expander(f'Show **{count_col}** trends for top **{ntop}** miners'):

        st.plotly_chart(
            plotting.plot_cabals(miners, time_col=x, count_col=count_col, sel_col=color, ntop=ntop, smooth=smooth, smooth_agg=smooth_agg, opacity=opacity), 
            use_container_width=True
        )

with tab3:
    
    st.markdown('#')
    st.markdown('#')
    st.subheader('Validator Activity')
    st.info('**Activity** *shows the change in stake and emission over time for **validators**, grouped by coldkey*')
    
    vac1, vac2, vac3, vac4 = st.columns(4)
    vac_x = vac1.selectbox('**x**', vac_choices, index=vac_choices.index('incentive_mean'))
    vac_y = vac2.selectbox('**y**', vac_choices, index=vac_choices.index('validator_trust_mean'))
    vac_size = vac3.selectbox('**marker size**', vac_choices, index=vac_choices.index('hotkey_nunique'))
    vac_color = vac4.selectbox('**marker color**', vac_choices, index=vac_choices.index('total_stake_sum'))
    
    st.plotly_chart(
        plotting.plot_animation(validators, x=vac_x, y=vac_y, color=vac_color, size=vac_size, opacity=opacity),
        use_container_width=True
    )    
    validator_choice = st.radio('Select:', validator_choices, horizontal=True, index=0)
    with st.expander(f'Show **{validator_choice}** trends for top **{ntop}** validators'):
    
        st.plotly_chart(
            plotting.plot_trace(validators, time_col=x,col=validator_choice, ntop=ntop, smooth=smooth, smooth_agg=smooth_agg, opacity=opacity),
            use_container_width=True
        )

    count_col = st.radio('Count', cabal_choices, index=0, horizontal=True, key='sel_validator_count')
    with st.expander(f'Show **{count_col}** trends for top **{ntop}** validators'):

        st.plotly_chart(
            plotting.plot_cabals(validators, time_col=x, count_col=count_col, sel_col=color, ntop=ntop, smooth=smooth, smooth_agg=smooth_agg, opacity=opacity), 
            use_container_width=True
        )