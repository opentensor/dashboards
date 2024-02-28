import glob
import tqdm
import pickle
import os
import datetime

import torch
import bittensor as bt
import pandas as pd
import plotly.express as px

def trust(W, S, threshold=0):
    """Trust vector for subnets with variable threshold"""

    # assert (S.sum()-1).abs()<1e-4, f'Stake must sum to 1, got {S.sum()}'
    Wn = (W > 0).float()
    return Wn.T @ S
    # return ( (W > threshold)*S.reshape(-1,1) ).sum(axis=0)

def rank(W, S):
    """Rank vector for subnets"""
    # assert (S.sum()-1).abs()<1e-4, f'Stake must sum to 1, got {S.sum()}'

    R = W.T @ S
    return R / R.sum()

def emission(C, R):
    """Emission vector for subnets"""

    E = C*R
    return E / E.sum()

def YC1(T, a=0.5, b=10):
    """Yuma Consensus 1"""

    return torch.sigmoid( b * (T - a) )


def load_metagraphs(root_dir, netuid, block_min=0, block_max=3_000_000):

    metagraphs = []
    match_path = os.path.join(root_dir, str(netuid), '*.pkl')
    files = glob.glob(match_path)
    print(f'Found {len(files)} metagraphs in {match_path}')
    for path in tqdm.tqdm(files):
        block = int(path.split('/')[-1].split('.')[0])
        if not block_min <= block <= block_max:
            continue
        with open(path, 'rb') as f:
            metagraph = pickle.load(f)
            metagraphs.append(metagraph)

    return sorted(metagraphs, key=lambda x: x.block)


# TODO: can calculate the emission trend using each subnet or just using root subnet
def plot_emission_trend(metagraphs, netuid, max_uids=32):

    df = pd.DataFrame()
    max_uids = max_uids or max(m.W.shape[1] for m in metagraphs)

    for metagraph in metagraphs:
        E = m.W.mean(axis=0)
        df = pd.concat([df, pd.DataFrame({'emission':E}).assign(block=metagraph.block)])

    df.sort_values(by='block', inplace=True)

    fig = px.line(df, x=df.index, y='emission',line_group='',
                  title='Emission Trend',

                  width=800, height=600, template='plotly_white')
    fig.update_xaxes(title_text='Block Height')
    fig.update_yaxes(title_text='Emission')
    fig.show()

    return fig

def block_to_time(blocks):
    if not isinstance(blocks, pd.Series):
        blocks = pd.Series(blocks)
    
    block_time_500k = datetime.datetime(2023, 5, 29, 5, 29, 0)
    block_time_800k = datetime.datetime(2023, 7, 9, 21, 32, 48)
    dt = (pd.Timestamp(block_time_800k)-pd.Timestamp(block_time_500k))/(800_000-500_000)
    return block_time_500k + dt*(blocks-500_000)

root_dir = os.path.expanduser('~/Desktop/py/opentensor/metagraph/subnets/')

metagraphs = load_metagraphs(root_dir, 0)
metagraphs

def make_dataframe_old(metagraphs, netuid):
    df = pd.DataFrame()
    # max_uids=max(m.W.shape[1] for m in metagraphs)
    for metagraph in sorted(metagraphs, key=lambda m: m.block):
        if metagraph.n.item() == 0:
            print(f'Block {metagraph.block} has no nodes, skipping')
            continue

        if netuid == 0:
            W = metagraph.W.float()
            Sn = (metagraph.S/metagraph.S.sum()).clone().float()

            T = trust(W, Sn)
            R = rank(W, Sn)
            C = YC1(T)
            E = emission(C, R)
        else:
            T = metagraph.T
            R = metagraph.R
            C = metagraph.C
            E = metagraph.E

        frame = pd.DataFrame({'Trust':T, 'Rank':R, 'Consensus':C, 'Emission':E, 'uid':range(len(E))}).assign(block=metagraph.block.item(), netuid=netuid)
        df = pd.concat([df, frame])

    df['alive'] = df.groupby('netuid')['Emission'].transform(lambda x: x > 0)
    df['owner_take'] = df['Emission'] * 7200 * 0.18
    df['timestamp'] = block_to_time(df['block'])
    df['day'] = df['timestamp'].dt.dayofyear
    df.sort_values(by=['block','netuid'], inplace=True)
    return df

def make_dataframe(root_dir, netuid, cols=None, block_min=0, block_max=3_000_000, weights=False):
    if cols is None:
        cols = ['stake','emission','trust','validator_trust','dividends','incentive','R', 'consensus','validator_permit']
    frames = []
    metagraphs = load_metagraphs(root_dir, netuid, block_min, block_max)
    print(f'Loaded {len(metagraphs)} metagraphs for netuid {netuid}')
    for m in metagraphs:
        frame = pd.DataFrame({k: getattr(m, k) for k in cols})
        frame['block'] = m.block.item()
        frame['timestamp'] = block_to_time(frame['block'])
        frame['netuid'] = netuid
        frame['uid'] = range(len(frame))
        frame['hotkey'] = [axon.hotkey for axon in m.axons]
        frame['coldkey'] = [axon.coldkey for axon in m.axons]
        if weights and m.W is not None:
            # convert NxN tensor to a list of lists so it fits into the dataframe
            frame['weights'] = [w.tolist() for w in m.W]
            
        frames.append(frame)
    return pd.concat(frames).sort_values(by=['timestamp','block','uid'])
