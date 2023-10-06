import bittensor as bt
import openai
import pandas as pd
import tiktoken
import argparse
import time
import tqdm
import concurrent.futures
from dataclasses import dataclass
from typing import Tuple, List
from functools import lru_cache



@dataclass
class OpenAIModel:
    input_price_per_1k_tokens: float
    output_price_per_1k_tokens: float
    model_description: str
    model_name: str


gpt_3_5_turbo = OpenAIModel(input_price_per_1k_tokens=0.0015, output_price_per_1k_tokens=0.002,  model_description="gpt-3.5-turbo_4k-context", model_name="gpt-3.5-turbo")
gpt4 = OpenAIModel(input_price_per_1k_tokens=0.03, output_price_per_1k_tokens=0.06, model_description="gpt4_8k-context", model_name="gpt-4")


def concatenate_messages_into_txt_dialogue(messages):
    str_template = "##{role}:\n{content}\n"

    if messages is None:
        return None

    formatted_messages = []
    for msg in messages:
        formatted_message = str_template.format(role=msg['role'].upper(), content=msg['content'])
        formatted_messages.append(formatted_message)

    return '\n'.join(formatted_messages)


def engage_conversation(turns: List[str], model:str, temperature:float = 0.0, max_tokens:int = 1000) -> List[dict]:
    system_prompt_message = {"role": "system", "content": "You are a helpful assistant."}
    messages = [system_prompt_message]

    for turn in turns:
        messages.append({"role": "user", "content": turn})

        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )        

        response_content = response['choices'][0]['message']['content']
        messages.append({"role": "assistant", "content": response_content})
    
    return messages


@lru_cache(maxsize=10_000)
def get_response_from_openai(system_prompt: str, prompt: str, model: str = gpt_3_5_turbo.model_name, max_tokens:int=1000) -> str:    
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
    )
    response = response["choices"][0]["message"]["content"]

    return response


def get_completions(
    dataframe:pd.DataFrame, 
    prompt_column: str='prompt',
    system_template: str='user', 
    model: str = gpt_3_5_turbo.model_name,
    max_tokens:int=1000,
    rest_time: int=3
) -> List[str]:
    baseline_answers = []
    bt.logging.info(f'Starting collection of baseline answers with model {model}...')
    pbar = tqdm.tqdm(dataframe.iterrows(), total=len(dataframe), desc="Getting baseline answers")
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for i, row in pbar:            
            prompt = row[prompt_column]
            try:                            
                bt.logging.info('Starting index {}'.format(i))    
                future = executor.submit(get_response_from_openai, system_template, prompt, model, max_tokens)
                response = future.result(timeout=15)
                bt.logging.info(f'✅ - Success: {response}')
                baseline_answers.append(response)
                time.sleep(rest_time)
            except concurrent.futures.TimeoutError:
                bt.logging.error(f"TimeoutError for index: {i}")
                baseline_answers.append(None)            
                

    return baseline_answers


def calculate_openai_cost(
    dataframe: pd.DataFrame,
    input_column_name: str,
    model_api: OpenAIModel = gpt_3_5_turbo,
    max_token_output: int = 512
) -> pd.DataFrame:
    # Concatenate all the strings in the specified column
    encoding = tiktoken.encoding_for_model(model_api.model_name)

    # Calculate input_token_count    
    dataframe['input_token_count'] = dataframe[input_column_name].apply(lambda prompt: len(encoding.encode(prompt)))

    # Max tokens defined at inference time, default to 512 max output tokens
    estimated_output_token_count = max_token_output

    # Calculate input_price, output_price and total_price for each row
    dataframe['estimated_input_price'] =  dataframe['input_token_count'].apply(lambda token_count: token_count * model_api.input_price_per_1k_tokens / 1000)
    dataframe['estimated_output_price'] = dataframe['input_token_count'].apply(lambda _: estimated_output_token_count * model_api.output_price_per_1k_tokens / 1000)    
    dataframe['estimated_total_price'] = dataframe['estimated_input_price'] + dataframe['estimated_output_price']

    # Calculate overall training price
    overall_input_price = dataframe['estimated_input_price'].sum()
    overall_output_price = dataframe['estimated_output_price'].sum()
    overall_training_price = dataframe['estimated_total_price'].sum()

    bt.logging.info(f'******OpenAI {model_api.model_description}******')
    bt.logging.info('Total input cost: ', overall_input_price)
    bt.logging.info('Estimated output cost: ', overall_output_price)
    bt.logging.info('Overall training price: ', overall_training_price)

    return dataframe


if __name__ == "__main__":
    # Load data
    parser = argparse.ArgumentParser(description='OpenAI cost calculator')
    parser.add_argument('--dataset_path', type=str, help='Path of dataset to calculate cost from', default='uncertainty_dataset_eval.csv')
            
    args = parser.parse_args()

    bt.logging.info(f'⏳ Loading dataset from {args.dataset_path}...')
    dataframe = pd.read_csv(args.dataset_path)

    bt.logging.info(f'⏳💸 Calculating OpenAI cost for each row...')
    dataframe = calculate_openai_cost(dataframe, input_column_name='eval_prompt')
    dataframe.to_csv('eval_dataset_with_openai_cost.csv')

    bt.logging.success(f'✅ OpenAI inference cost calculated successfully for {len(dataframe)} rows')
