import time
import pandas as pd
from abc import ABC, abstractmethod
from openai_utils import OpenAIModel

class DatasetEval(ABC):        
    @abstractmethod
    def load_dataset(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def prepare_examples(self, n_shots:int) -> str:
        pass

    def create_baseline_dataset(self, model:OpenAIModel, n_few_shots:int, output_path:str) -> pd.DataFrame:
        pass




def prompt_confirmation_cost(estimated_price: float) -> bool:
    time.sleep(1) # Wait for logging to finish
    confirmation = input(f"Estimated cost: {estimated_price}\nDo you want to proceed? (yes/no): ")
    if confirmation.lower() == 'yes' or confirmation.lower() == 'y':
        print("Proceeding...")
        return True
    else:
        print("Operation cancelled.")
        return False