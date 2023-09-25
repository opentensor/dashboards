import bittensor as bt
import pandas as pd
from typing import List
import time
from typing import List
import bittensor as bt
import asyncio
import pandas as pd
from functools import lru_cache
from bittensor._dendrite.text_prompting.dendrite import DendriteForwardCall
import concurrent.futures
from traceback import print_exception
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm.notebook import tqdm


def sample_n_from_top_100_incentive(n_sample:int, netuid: int = 1) -> List[int]:
    """Sample n uids from the top 100 uids with the highest incentive"""
    # Creates dataframe with uids, incentives and their ranks
    metagraph = bt.metagraph(netuid)
    df = pd.DataFrame({
        'uid': list(map(lambda uid: uid.item(), metagraph.uids)),
        'incentive': list(map(lambda incentive: incentive.item(), metagraph.incentive)),
    })
    df = df.sort_values(by='incentive', ascending=False)
    df['rank'] = df['incentive'].rank(method='min', ascending=False).astype(int)

    # Sample n uids from the top 100 uids with the highest incentive
    top_100 = df.sort_values(by='rank').head(100)
    samples = top_100.sample(n_sample)

    # Get uids and ranks of the samples    
    samples_uids = samples['uid'].tolist()
    samples_ranks = samples['rank'].tolist()

    # Log uids and ranks of the samples
    bt.logging.info(f'Sample uids: {samples_uids}')
    bt.logging.info(f'Sample ranks: {samples_ranks}')    

    return samples_uids


async def query_uid(dendrite, prompt:str, timeout:int=10, retries:int=5):
    for i in range(retries):
        response : DendriteForwardCall = await dendrite.async_forward(
            roles=['user'],
            messages=[prompt],
            return_call=True,
            timeout=timeout
        )        

        if str(response.return_code) == '1':
            return response
        else:            
            bt.logging.error(f'Error on dendrite of UID {dendrite.uid}: RC: {response.return_code}, Attempt number: {i} ')
            time.sleep(timeout * i) 
        
    return response


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def export_df_to_hf(df, output_file):
    # Since under the hood HuggingFace integration works in a single thread, it's easy to lose the commit head in a concurrent context.
    # This can be easily worked around by retrying the upload with a small time sleep in between.
    df.to_csv(output_file, index=False)


async def evaluate_uid(dendrite, prompts: List[str], prompts_ids: List[str], output_path: str, block_stamp:int, rest_time:int=0):
    """Evaluates a single UID with a list of prompts
    Args:
        dendrite: Dendrite instance
        prompts: List of prompts to evaluate
        prompts_ids: List of prompts ids
        output_path: Path to save the output file
        block_stamp: Block stamp of the metagraph
        rest_time: Time to wait between each prompt evaluation
    """            
    responses: List[DendriteForwardCall] = []
    non_successful_calls = 0 # Counter of non successful calls to be shown in the progress bar
    pbar = tqdm(prompts, desc=f"UID {dendrite.uid}", position=dendrite.uid)
    
    for prompt in pbar:
        response = asyncio.run(query_uid(dendrite=dendrite, prompt=prompt))
        responses.append(response)

        if rest_time > 0:
            await asyncio.sleep(rest_time)            

        if str(response.return_code) != '1':
            non_successful_calls += 1
            pbar.set_postfix({"non_successful_calls": non_successful_calls}, refresh=True)
            pbar.update(1)
    
    # Transform responses to dictionaries
    data = {}
    for idx, obj in enumerate(responses):
        obj_dict = vars(obj)
        data[idx] = obj_dict

    # Create dataframe
    df = pd.DataFrame.from_dict(data, orient='index')
    df['prompt_id'] = prompts_ids
    df['prompt'] = prompts
    df['block_stamp'] = block_stamp
    df['uid'] = dendrite.uid

    # Export dataframe to hugging face
    output_file = f'{output_path}/arc_net1_uid{dendrite.uid}.csv'
    export_df_to_hf(df, output_file)
    
    return df


async def evaluate_uids(uids: List[int], prompt_ids: List[str], prompts: List[str], output_path: str):
    """Evaluates a list of uids with a list of prompts
    Args:
        uids: List of uids to evaluate
        prompt_ids: List of prompts ids to track the prompt
        prompts: List of prompts to evaluate
        output_path: Path to save the output file
    """
    try:
        # Load wallet and metagraph
        wallet = bt.wallet(name='opentensor', hotkey='main')
        bt.logging.info("Loaded wallet: {}".format(wallet.hotkey.ss58_address))
        bt.logging.info("Loading/Syncing metagraph from chain...")
        metagraph = bt.metagraph(1)
        metagraph.sync()

        # Create dendrites and tasks to be executed concurrently
        dendrites = [bt.text_prompting(axon=axon, keypair=wallet.hotkey, uid=uid) for uid, axon in enumerate(metagraph.axons)]
        tasks = [evaluate_uid(
                    dendrite=dendrites[uid],
                    prompts=prompts,
                    prompts_ids=prompt_ids,
                    output_path=output_path,
                    block_stamp=metagraph.block.item(),            
                    rest_time=3
                ) for uid in uids]
        
        # Execute tasks concurrently and save results in a dictionary
        uid_dfs = {}
        results = await asyncio.gather(*tasks)
        for uid, uid_df in zip(uids, results):
            uid_dfs[uid] = uid_df        

        return uid_dfs
    except Exception as err:
        print_exception(type(err), err, err.__traceback__)
        raise err
    

