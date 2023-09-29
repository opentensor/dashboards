import openai
import asyncio
import pandas as pd
import bittensor as bt
from types import SimpleNamespace
from benchmarks import ArcDatasetEval, TruthfulQADatasetEval
from openai_utils import gpt_3_5_turbo, gpt4
from network_utils import sample_n_from_top_100_emission, evaluate_uids


N_FEW_SHOTS = 5

def perform_arc_evaluation(n_few_shots:int = N_FEW_SHOTS):
    # Evaluate baseline
    output_path = 'hf://datasets/opentensor/research-and-development/experiments/arc-evaluation'
    arc_eval = ArcDatasetEval()
    df = arc_eval.create_baseline_dataset(
        model=gpt4,
        n_few_shots=5,
        output_path=output_path
    )

    # Sample network
    uids = sample_n_from_top_100_emission(n_sample=10)
    evaluate_uids(
        uids=uids, 
        prompt_ids=df['prompt_id'].tolist(), 
        prompts=df['prompt'].tolist(),
        output_path=output_path,
    )


def perform_truthful_qa_dataset():
    output_path = 'hf://datasets/opentensor/research-and-development/experiments/truthfulqa-evaluation'
    tqa_eval = TruthfulQADatasetEval()
    # Sample baseline model
    df = tqa_eval.create_baseline_dataset(
        model=gpt_3_5_turbo,
        n_few_shots=0,
        output_path=output_path
    )

    # Sample network
    uids = sample_n_from_top_100_emission(n_sample=10)
    uids_dict = asyncio.run(evaluate_uids(
        uids=uids, 
        prompt_ids=df['mc1_prompt_id'].tolist(), 
        prompts=df['mc1_prompt'].tolist(),
        output_path=output_path,
        benchmark_name='truthfulqa',
    ))

    # Evaluate initial results and save summary results
    summary_results = []
    for uid, miner_df in uids_dict.items():
        miner_df.rename(columns={'prompt_id': 'mc1_prompt_id'}, inplace=True)
        if 'completion' not in miner_df.columns:
            miner_df['completion'] = 'N/A'

        dataframe = df.merge(miner_df, on='mc1_prompt_id')        
        _, accuracy = tqa_eval(dataframe, 'completion', 'mc1_answer_key')

        error_rate = sum(dataframe['return_code'].astype(str) != '1') / len(dataframe) * 100
        
        result = SimpleNamespace(
            uid=uid,
            accuracy=accuracy,
            error_rate=error_rate,
        )
        summary_results.append(result)

        bt.logging.info(f'UID: {uid}')
        bt.logging.info(f'Accuracy: {accuracy} %')
        bt.logging.info('-----------------')

    summary_dicts = [ns.__dict__ for ns in summary_results]
    summary_df = pd.DataFrame(summary_dicts, columns=['uids', 'accuracy', 'error_rate'])
    summary_df.to_csv(output_path + '/truthfulqa_initial_results_summary.csv', index=False)



if __name__ == '__main__':
    openai.api_key = 'YOUR_API_KEY'
    perform_arc_evaluation()