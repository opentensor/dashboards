import os
import sys
import argparse
from traceback import print_exc
import pickle
import tqdm
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import torch
import bittensor
from meta_utils import load_metagraphs
#TODO: make line charts and other cool stuff for each metagraph snapshot

def process(block, netuid=1, lite=True, difficulty=False, prune_weights=False, return_graph=False, half=True, subtensor=None):

    if subtensor is None:
        subtensor = bittensor.subtensor(network='archive')

    try:
        metagraph = subtensor.metagraph(block=block, netuid=netuid, lite=lite)
        if difficulty:
            metagraph.difficulty = subtensor.difficulty(block=block, netuid=netuid)

        if not lite:
            if half:
                metagraph.weights = torch.nn.Parameter(metagraph.weights.half(), requires_grad=False)
            if prune_weights:
                metagraph.weights = metagraph.weights[metagraph.weights.sum(axis=1) > 0]

        with open(f'data/metagraph/{netuid}/{block}.pkl', 'wb') as f:
            pickle.dump(metagraph, f)

        return metagraph if return_graph else True

    except Exception as e:
        print(f'Error processing block {block}: {e}')


def parse_arguments():
    parser = argparse.ArgumentParser(description='Process metagraphs for a given network.')
    parser.add_argument('--netuid', type=int, default=1, help='Network UID to use.')
    parser.add_argument('--lite', action='store_true', help='Do not include weights.')
    parser.add_argument('--difficulty', action='store_true', help='Include difficulty in metagraph.')
    parser.add_argument('--prune_weights', action='store_true', help='Prune weights in metagraph.')
    parser.add_argument('--return_graph', action='store_true', help='Return metagraph instead of True.')
    parser.add_argument('--no_dataframe', action='store_true', help='Do not create dataframe.')
    parser.add_argument('--max_workers', type=int, default=32, help='Max workers to use.')
    parser.add_argument('--start_block', type=int, default=None, help='Start block.')
    parser.add_argument('--num_blocks', type=int, default=0, help='Number of blocks.')
    parser.add_argument('--end_block', type=int, default=600_000, help='End block.')
    parser.add_argument('--step_size', type=int, default=100, help='Step size.')
    parser.add_argument('--overwrite', action='store_true',help='Overwrite existing files')
    return parser.parse_args()

if __name__ == '__main__':

    subtensor = bittensor.subtensor(network='archive')
    print(f'Current block: {subtensor.block}')

    args = parse_arguments()
    print(args)

    netuid=args.netuid
    lite=args.lite
    difficulty=args.difficulty
    return_graph=args.return_graph

    step_size = args.step_size
    start_block = args.start_block or subtensor.get_current_block()
    start_block = (min(subtensor.block, start_block)//step_size)*step_size # round to nearest step_size
    if args.num_blocks:
        end_block = start_block - int(args.num_blocks*step_size)
    else:
        end_block = args.end_block
        
    blocks = range(start_block, end_block, -step_size)


    max_workers = min(args.max_workers, len(blocks))

    datadir = f'data/metagraph/{netuid}'
    os.makedirs(datadir, exist_ok=True)
    if not args.overwrite:
        blocks = [block for block in blocks if not os.path.exists(f'data/metagraph/{netuid}/{block}.pkl')]

    metagraphs = []

    if len(blocks)>0:

        print(f'Processing {len(blocks)} blocks from {blocks[0]}-{blocks[-1]} using {max_workers} workers.')

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process, block, lite=args.lite, netuid=netuid, difficulty=difficulty)
                for block in blocks
                ]

            success = 0
            with tqdm.tqdm(total=len(futures)) as pbar:
                for block, future in zip(blocks,futures):
                    try:
                        metagraphs.append(future.result())
                        success += 1
                    except Exception as e:
                        print(f'generated an exception: {print_exc(e)}')
                    pbar.update(1)
                    pbar.set_description(f'Processed {success} blocks. Current block: {block}')

        if not success:
            raise ValueError('No blocks were successfully processed.')

        print(f'Processed {success} blocks.')
        if return_graph:
            for metagraph in metagraphs:
                print(f'{metagraph.block}: {metagraph.n.item()} nodes, difficulty={getattr(metagraph, "difficulty", None)}, weights={metagraph.weights.shape if hasattr(metagraph, "weights") else None}')

        print(metagraphs[-1])
    else:
        print(f'No blocks to process. Current block: {subtensor.block}')


    if not args.no_dataframe:
        save_path = f'data/metagraph/{netuid}/df.parquet'
        blocks = range(start_block, end_block, step_size)
        df_loaded = None
        if os.path.exists(save_path):
            df_loaded = pd.read_parquet(save_path)
            blocks = [block for block in blocks if block not in df_loaded.block.unique()]
            print(f'Loaded dataframe from {save_path!r}. {len(df_loaded)} rows. {len(blocks)} blocks to process.')
            if len(blocks)==0:
                print('No blocks to process.')
                sys.exit(0)

        df = load_metagraphs(blocks[0], blocks[-1], block_step=step_size, datadir=datadir)
        if df_loaded is not None:
            df = pd.concat([df, df_loaded], ignore_index=True)
        df.to_parquet(save_path)
        print(f'Saved dataframe to {save_path!r}')