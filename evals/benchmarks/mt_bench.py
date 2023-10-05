import requests
import json
import pandas as pd
from benchmarks import DatasetEval, prompt_confirmation_cost
import pandas as pd
import tqdm
import concurrent.futures
import time
import bittensor as bt
from openai_utils import (    
    engage_conversation, 
    concatenate_messages_into_txt_dialogue,
    calculate_openai_cost,
    OpenAIModel
)


# Downloads directly from GitHub since lmsys did not upload the dataset to HuggingFace
QUESTION_DATASET_URL = "https://raw.githubusercontent.com/lm-sys/FastChat/c3ad73a854c912132683b0a6b3df06596040385c/fastchat/llm_judge/data/mt_bench/question.jsonl"

# Sampling temperature configs used by lm-sys
# https://github.com/lm-sys/FastChat/blob/c3ad73a854c912132683b0a6b3df06596040385c/fastchat/llm_judge/common.py#L35-L46
TEMPERATURE_CONFIG = {
    "writing": 0.7,
    "roleplay": 0.7,
    "extraction": 0.0,
    "math": 0.0,
    "coding": 0.0,
    "reasoning": 0.0,
    "stem": 0.1,
    "humanities": 0.1,
}

def download_jsonl_dataset(url: str) -> pd.DataFrame:
    response = requests.get(url)
    response.raise_for_status()
    lines = response.text.splitlines()
    return pd.DataFrame([json.loads(line) for line in lines])


class MTBenchDatasetEval(DatasetEval):
    def prepare_examples(dataset: pd.DataFrame) -> pd.DataFrame:
        pass


    def load_dataset(self) -> pd.DataFrame:
        dataset = download_jsonl_dataset(QUESTION_DATASET_URL)
        return dataset

    def create_answers_dataset(
        self,         
        model: OpenAIModel,
        rest_time: int = 3, 
        max_retries_per_conv: int = 5
    ) -> pd.DataFrame:
        # Loads the dataset
        dataframe = self.load_dataset()[:5]
        dataframe['concatenated_inputs'] = dataframe['turns'].apply(' '.join)
        # Calculate cost
        dataframe = calculate_openai_cost(dataframe, 'concatenated_inputs', model, max_token_output=1000)

        # Ask for confirmation before proceeding
        estimated_price = round(dataframe['estimated_total_price'].sum(), 2)
        # Return if user doesn't confirm
        if not prompt_confirmation_cost(estimated_price):
            return

        # Creates array to store conversation logs
        conversation_history_logs = []

        # Iterate over the dataframe and get the conversation history
        pbar = tqdm.tqdm(dataframe.iterrows(), total=len(dataframe), desc="Getting baseline answers")        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for i, row in pbar:            
                turns = row['turns']
                temperature = TEMPERATURE_CONFIG[row['category']]

                retries = 0
                while retries < max_retries_per_conv:
                    try:                            
                        bt.logging.info('Starting index {}'.format(i))    
                        future = executor.submit(engage_conversation, turns, model.model_name, temperature)
                        conversation_log = future.result(timeout=30)
                        bt.logging.info(f'✅ - Success: {conversation_log}')
                        conversation_history_logs.append(conversation_log)
                        time.sleep(rest_time)
                        break  # If successful, break the retry loop

                    except Exception as e:
                        bt.logging.error(f"Exception of type {type(e).__name__} occurred for index: {i}. Retry {retries+1} of {max_retries_per_conv}")               
                        retries += 1  # Increment the retry counter

                if retries == max_retries_per_conv:
                    conversation_history_logs.append(None)  # If all retries failed, append None

        dataframe['conversation_log'] = conversation_history_logs
        dataframe['concatenated_conversation'] = dataframe['conversation_log'].apply(concatenate_messages_into_txt_dialogue)
        dataframe['prompt_id'] = 'mt-bench_prompt_' + dataframe.index.astype(str)
        return dataframe    
        