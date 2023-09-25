from benchmarks import ArcDatasetEval
from openai_utils import get_completions, gpt_3_5_turbo, gpt4
from network_utils import sample_n_from_top_100_incentive, evaluate_uids
import openai


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
    uids = sample_n_from_top_100_incentive(n_sample=10)
    evaluate_uids(
        uids=uids, 
        prompt_ids=df['prompt_id'].tolist(), 
        prompts=df['prompt'].tolist(),
        output_path=output_path,
    )


if __name__ == '__main__':
    openai.api_key = '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'
    perform_arc_evaluation()