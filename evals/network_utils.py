import bittensor as bt
import pandas as pd
from typing import List
import time
from typing import List, Union
import bittensor as bt
import asyncio
import pandas as pd
from traceback import print_exception
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm.notebook import tqdm
import prompting
from openai_utils import concatenate_messages_into_txt_dialogue


def check_uid_availability(metagraph: "bt.metagraph.Metagraph", uid: int):
    """Check if a uid is available in the metagraph"""
    uid_is_serving = metagraph.axons[uid].is_serving
    uid_has_validator_permit = metagraph.validator_permit[uid]

    is_uid_available = uid_is_serving and not uid_has_validator_permit
    return is_uid_available


def sample_n_from_top_100_emission(n_sample:int, netuid: int = 1, inverse: bool = False) -> List[int]:
    """Sample n uids from the top 100 uids with the highest incentive
    Args:
        n_sample: Number of uids to sample
        netuid: Network id
        inverse: If True, sample uids from the bottom 100 uids with the lowest incentive
    """
    # Creates dataframe with uids, incentives and their ranks
    metagraph = bt.metagraph(netuid)

    # Filters uids that are available defined by the rules in `check_uid_availability`
    available_uids = [uid.item() for uid in metagraph.uids if check_uid_availability(metagraph, uid.item())]
    available_uids_emissions = [metagraph.emission[uid].item() for uid in available_uids]
    bt.logging.info(f'Available uids: {len(available_uids)} / {len(metagraph.uids)}')
        
    # Create dataframe with uids, emissions and their ranks
    df = pd.DataFrame({
        'uid': available_uids,
        'emission': available_uids_emissions,
    })
    df = df.sort_values(by='emission', ascending=False)
    df['rank'] = df['emission'].rank(method='min', ascending=False).astype(int)

    # Sample n uids from the top 100 uids with the highest incentive
    if not inverse:
        samples = df.sort_values(by='rank').head(100).sample(n_sample)
    else:
        samples = df.sort_values(by='rank').tail(100).sample(n_sample)

    # Get uids and ranks of the samples    
    samples_uids = samples['uid'].tolist()
    samples_ranks = samples['rank'].tolist()

    # Log uids and ranks of the samples
    bt.logging.info(f'Sample uids: {samples_uids}')
    bt.logging.info(f'Sample ranks: {samples_ranks}')    

    return samples_uids


async def query_uid(dendrite: "bt.dendrite", axon: "bt.axon", prompt:str, timeout:int=10, retries:int=3):
    synapse = prompting.protocol.Prompting(roles=["user"], messages=[prompt])

    for i in range(retries):
        response:bt.Synapse  = await dendrite(axons=[axon], synapse=synapse,timeout=timeout)

        if str(response.dendrite.status_code) == '1':
            return response
        else:            
            bt.logging.error(f'Error on dendrite of UID {dendrite.uid}: RC: {response.return_code}, Attempt number: {i} ')
            time.sleep(timeout) 
        
    return response


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def export_df_to_hf(df, output_file):
    # Since under the hood HuggingFace integration works in a single thread, it's easy to lose the commit head in a concurrent context.
    # This can be easily worked around by retrying the upload with a small time sleep in between.
    df.to_csv(output_file, index=False)


def check_if_prompts_are_multiturn(value: Union[List[str], List[List[str]]]) -> bool:
    if all(isinstance(i, list) and all(isinstance(j, str) for j in i) for i in value):
        return True
    elif all(isinstance(i, str) for i in value):
        return False
    else:
        raise ValueError("Input should be either a list of strings or a list of list of strings")


async def evaluate_uid(
    dendrite: bt.dendrite,
    axon : bt.axon,
    uid: int,
    prompts: List[str], 
    prompts_ids: Union[List[str], List[List[str]]], 
    output_path: str, 
    block_stamp:int, 
    rest_time:int=0, 
    benchmark_name:str='undefined'
):
    """Evaluates a single UID with a list of prompts
    Args:
        dendrite: Dendrite instance
        prompts: List of prompts to evaluate
        prompts_ids: List of prompts ids
        output_path: Path to save the output file
        block_stamp: Block stamp of the metagraph
        rest_time: Time to wait between each prompt evaluation
    """            
        
    responses = [] # Miner responses
    all_conversation_logs = [] # Create conversation logs
    non_successful_calls = 0 # Counter of non successful calls to be shown in the progress bar
    multiturn_prompts = check_if_prompts_are_multiturn(prompts)

    if multiturn_prompts:
        pbar = tqdm(prompts, desc=f"UID {uid}", position=uid)

        for multi_turn_prompt in pbar:
            conversation_logs = []
            concatenated_prompt = ''

            for turn in multi_turn_prompt:
                conversation_logs.append({"role": "user", "content": turn})
                concatenated_prompt += f'{turn}\n'

                response = asyncio.run(query_uid(dendrite=dendrite, axon=axon, prompt=concatenated_prompt))
                
                concatenated_prompt += f'{response.messages}\n'                
                conversation_logs.append({"role": "assistant", "content": response})
                responses.append(response)                

                if rest_time > 0:
                    await asyncio.sleep(rest_time)    

            all_conversation_logs.append(conversation_logs)                   
    else:        
        pbar = tqdm(prompts, desc=f"UID {uid}", position=dendrite.uid)
        for prompt in pbar:            
            response = asyncio.run(query_uid(dendrite=dendrite, axon=axon, prompt=prompt))
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
    df['uid'] = uid

    if multiturn_prompts:
        df['conversation_log'] = all_conversation_logs
        df['concatenated_conversation'] = df['conversation_log'].apply(concatenate_messages_into_txt_dialogue)        

    # Export dataframe to hugging face
    output_file = f'{output_path}/{benchmark_name}_net1_uid{dendrite.uid}.csv'
    export_df_to_hf(df, output_file)
    
    return df


async def evaluate_uids(
    uids: List[int], 
    prompt_ids: List[str], 
    prompts: Union[List[str] , List[List[str]]], 
    output_path: str, 
    benchmark_name:str    
):
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
        dendrite = bt.dendrite(wallet)        
        tasks = [evaluate_uid(
                    dendrite=dendrite,
                    axon=metagraph.axons[uid],
                    prompts=prompts,
                    prompts_ids=prompt_ids,
                    output_path=output_path,
                    block_stamp=metagraph.block.item(),            
                    rest_time=3,
                    benchmark_name=benchmark_name                    
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
    


