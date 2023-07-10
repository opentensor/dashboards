import os
import glob
import tqdm
import pickle
import subprocess
import pandas as pd


def run_subprocess(*args):
    # Trigger the multigraph.py script to run and save metagraph snapshots
    return subprocess.run('python multigraph.py'.split()+list(args), 
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)    

def load_metagraph(path, extra_cols=None, rm_cols=None):
    
    with open(path, 'rb') as f:
        metagraph = pickle.load(f)

    df = pd.DataFrame(metagraph.axons)
    df['block'] = metagraph.block.item()
    df['difficulty'] = metagraph.difficulty
    for c in extra_cols:
        vals = getattr(metagraph,c)
        df[c] = vals        
    
    return df.drop(columns=rm_cols)
        
def load_metagraphs(block_start, block_end, block_step=1000, datadir='data/metagraph/1/', extra_cols=None):
    
    if extra_cols is None:
        extra_cols = ['total_stake','ranks','incentive','emission','consensus','trust','validator_trust','dividends']

    blocks = range(block_start, block_end, block_step)
    filenames = sorted(path for path in os.listdir(datadir) if int(path.split('.')[0]) in blocks)

    metagraphs = []
    
    pbar = tqdm.tqdm(filenames)
    for filename in pbar:
        pbar.set_description(f'Processing {filename}')

        metagraph = load_metagraph(os.path.join(datadir, filename), extra_cols=extra_cols, rm_cols=['protocol','placeholder1','placeholder2'])
        
        metagraphs.append(metagraph)
        
    return pd.concat(metagraphs)

load_metagraphs(block_start=700_000, block_end=800_000, block_step=1000)