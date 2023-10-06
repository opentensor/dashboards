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

    # Calculates initial results for each miner including their accuracy and error rate
    summary_df = tqa_eval.evaluate_initial_results(
        uids_dict=uids_dict,
        baseline_df=df,
    )
    summary_df.to_csv(output_path + '/uids/truthfulqa_initial_results_summary.csv', index=False)


if __name__ == '__main__':
    openai.api_key = 'YOUR_API_KEY'
    perform_arc_evaluation()