import time
import pandas as pd
import bittensor as bt
from .base import DatasetEval
from datasets import load_dataset
from openai_utils import get_completions, OpenAIModel, calculate_openai_cost


class ArcDatasetEval(DatasetEval):
    def get_system_template(self, few_shot_examples:str = '') -> str:
        system_template = f"""You are a helpful AI assistant that answers the questions that are provided to you.
You will be prompted with a question, some examples and a list of possible answers.
You should output the correct answer that best answers the question, with one single letter(s) or number(s) that corresponds to the correct answer.
Here are some examples of questions and answers that you will be asked to answer:
{few_shot_examples}
"""
        return system_template

    def load_dataset(self, split:str = 'train') -> pd.DataFrame:        
        dataset = load_dataset("ai2_arc", "ARC-Challenge", split=split)
        return dataset.to_pandas()
    

    def prepare_examples(self, n_shots:int) -> str:
        arc_validation_sample = self.load_dataset('validation').sample(n_shots).reset_index(drop=True)

        few_shot_samples = ''
        for i, row in arc_validation_sample.iterrows():
            choices_dict = row['choices']    

            txt = [f"{label} - {text}" for label, text in zip(choices_dict['label'], choices_dict['text'])]
            concatenated_choices_str = '\n'.join(txt)

            few_shot_samples += f"""Example {i + 1}:
Question: {row['question']} 
Choices: {concatenated_choices_str}
Correct Answer: {row['answerKey']}
"""

        return few_shot_samples
    

    def create_prompts(self, row):
        prompt_template = """Question: {question}
Choices: 
{choices}
Correct answer: 
"""
        choices_dict = row['choices']    

        formatted_choices = [f"{label} - {text}" for label, text in zip(choices_dict['label'], choices_dict['text'])]
        concatenated_choices_str = '\n'.join(formatted_choices)

        row["prompt"] = prompt_template.format(question=row['question'], choices=concatenated_choices_str)

        return row
    

    def create_baseline_dataset(self, model:OpenAIModel, n_few_shots:int, output_path:str) -> pd.DataFrame:        
        max_token_output = 5
        # Load dataset
        dataset = self.load_dataset()        
        dataset = dataset.apply(self.create_prompts, axis=1)
        dataset = calculate_openai_cost(dataset, 'prompt', model, max_token_output=max_token_output)
            
        # Ask for confirmation before proceeding
        estimated_price = round(dataset['estimated_total_price'].sum(), 2)
        time.sleep(1) # Wait for logging to finish
        confirmation = input(f"Estimated cost: {estimated_price}\nDo you want to proceed? (yes/no): ")
        if confirmation.lower() == 'yes' or confirmation.lower() == 'y':
            print("Proceeding...")
        else:
            print("Operation cancelled.")
            return

        # Get baseline answers
        n_few_shots_examples = self.prepare_examples(n_few_shots)
        system_template = self.get_system_template(n_few_shots_examples)
        dataset['baseline_answer'] = get_completions(
            dataframe=dataset, 
            prompt_column='prompt',
            system_template=system_template,
            max_tokens=max_token_output,
            model=model.model_name,
            rest_time=5
        )

        # Export dataset
        filename = f'arc_{model.model_name}_baseline.csv'
        filepath = f'{output_path}/{filename}' 
        bt.logging.success(f"Collection completed, exporting dataset to {filepath}...")        
        dataset.to_csv(filepath, index=False)

        return dataset