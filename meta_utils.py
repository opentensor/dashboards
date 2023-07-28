import os
import re
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

def run_subprocess(command='python multigraph.py', *args):
    try:
        # Run the subprocess with stdout and stderr pipes connected
        command = command + " ".join(args)
        print(f'{"===="*20}\nRunning: {command!r}')
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,  # Set to True for text mode
            bufsize=1,  # Line buffered, so output is available line by line
            shell=True  # Set to True to allow running shell commands (use with caution)
        )

        print(f'Subprocess started with pid {process.pid} and streaming output from stdout:')
        with process.stdout as output:
            for line in output:
                print(line, end='', flush=True)  # Print without adding an extra newline                
                if match := re.search('(?P<done>\\d+)/(?P<total>\\d+)',line):
                    print('---> match.groupdict():', match.groupdict())
                    # try yielding the line here
                
        # Wait for the subprocess to finish and get the return code
        process.wait()

        print("===="*20)
        return process.returncode 

    except subprocess.CalledProcessError as e:
        # If the subprocess returns a non-zero exit code, this exception will be raised
        return e.returncode

def load_metagraph(path, extra_cols=None, rm_cols=None):
    
    with open(path, 'rb') as f:
        metagraph = pickle.load(f)

    df = pd.DataFrame(metagraph.axons)
    df['block'] = metagraph.block.item()
    df['timestamp'] = block_time_500k + dt*(df['block']-500_000)
    df['difficulty'] = getattr(metagraph, 'difficulty', None)
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

