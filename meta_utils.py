import os
import glob
import tqdm
import dill as pickle
import subprocess
import pandas as pd
import datetime
from functools import lru_cache

block_time_500k = datetime.datetime(2023, 5, 29, 5, 29, 0)
block_time_800k = datetime.datetime(2023, 7, 9, 21, 32, 48)
dt = (pd.Timestamp(block_time_800k)-pd.Timestamp(block_time_500k))/(800_000-500_000)

def run_subprocess(*args):
    # Trigger the multigraph.py script to run and save metagraph snapshots
    return subprocess.run('python multigraph.py'.split()+list(args), 
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)    

def load_metagraph(path, extra_cols=None, rm_cols=None):
    
    with open(path, 'rb') as f:
        metagraph = pickle.load(f)

    df = pd.DataFrame(metagraph.axons)
    df['block'] = metagraph.block.item()
    df['timestamp'] = block_time_500k + dt*(df['block']-500_000)
    df['difficulty'] = metagraph.difficulty
    for c in extra_cols:
        vals = getattr(metagraph,c)
        df[c] = vals        
    
    return df.drop(columns=rm_cols)

@lru_cache(maxsize=16)
def load_metagraphs(block_start, block_end, block_step=1000, datadir='data/metagraph/1/', extra_cols=None):
    
    if extra_cols is None:
        extra_cols = ['total_stake','ranks','incentive','emission','consensus','trust','validator_trust','dividends']

    blocks = range(block_start, block_end, block_step)
    print(f'Loading blocks {blocks[0]}-{blocks[-1]} from {datadir}')
    filenames = sorted(filename for filename in os.listdir(datadir) if filename.split('.')[0].isdigit() and int(filename.split('.')[0]) in blocks)
    print(f'Found {len(filenames)} files in {datadir}')
    
    metagraphs = []
    
    pbar = tqdm.tqdm(filenames)
    for filename in pbar:
        pbar.set_description(f'Processing {filename}')

        try:
            metagraph = load_metagraph(os.path.join(datadir, filename), extra_cols=extra_cols, rm_cols=['protocol','placeholder1','placeholder2'])
            
            metagraphs.append(metagraph)
        except Exception as e:
            print(f'filename {filename!r} generated an exception: { e }')
            
    return pd.concat(metagraphs)

