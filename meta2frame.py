import glob
import tqdm
import pickle
import os
import datetime

import torch
import bittensor as bt
import pandas as pd
import plotly.express as px


ROOT_DIR = './data/metagraph/'


def load_metagraphs(root_dir, netuid, block_min=0, block_max=3_000_000):

    metagraphs = []
    match_path = os.path.join(root_dir, str(netuid), '*.pkl')
    files = glob.glob(match_path)
    print(f'Found {len(files)} metagraphs in {match_path}')

    valid_files = [path for path in files if block_min <= int(path.split('/')[-1].split('.')[0]) <= block_max]
    pbar = tqdm.tqdm(valid_files, desc=f'Loading {len(valid_files)} metagraph snapshots')
    for path in pbar:

        with open(path, 'rb') as f:
            metagraph = pickle.load(f)
            metagraphs.append(metagraph)

    return sorted(metagraphs, key=lambda x: x.block)


def get_block_timestamp(block, subtensor):

    info = subtensor.substrate.get_block(block_number=int(block))
    extrinsic_call = info['extrinsics'][0]['call']
    return extrinsic_call.value_serialized['call_args'][0]['value']


def block_to_time(blocks, subtensor=None):

    if not isinstance(blocks, pd.Series):
        blocks = pd.Series(blocks)

    if subtensor is None:
        subtensor = bt.subtensor(network='archive')

    timestamps = {}
    unique_blocks = set(blocks)
    for block in tqdm.tqdm(unique_blocks, desc=f'Mapping {len(unique_blocks)} blocks to timestamps'):
        timestamps[block] = get_block_timestamp(block, subtensor)

    return blocks.map(timestamps).apply(pd.to_datetime, unit='ms')


def make_dataframe(netuid, root_dir=ROOT_DIR, cols=None, block_min=0, block_max=3_000_000, weights=False):
    if cols is None:
        cols = ['stake','emission','trust','validator_trust','dividends','incentive','R', 'consensus','validator_permit']
    frames = []
    metagraphs = load_metagraphs(root_dir, netuid, block_min, block_max)

    for m in metagraphs:
        frame = pd.DataFrame({k: getattr(m, k) for k in cols})
        frame['block'] = m.block.item()
        frame['netuid'] = netuid
        frame['uid'] = range(len(frame))
        frame['hotkey'] = [axon.hotkey for axon in m.axons]
        frame['coldkey'] = [axon.coldkey for axon in m.axons]
        if weights and m.W is not None:
            # convert NxN tensor to a list of lists so it fits into the dataframe
            frame['weights'] = [w.tolist() for w in m.W]

        frames.append(frame)

    df = pd.concat(frames)
    df['timestamp'] = block_to_time(df['block'])
    return df.sort_values(by=['timestamp','block','uid'])
