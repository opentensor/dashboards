from abc import ABC, abstractmethod

class DatasetEval(ABC):        
    @abstractmethod    
    def get_system_template(self, few_shot_examples:str = '') -> str:
        pass
    
    @abstractmethod
    def load_dataset(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def prepare_examples(self, n_shots:int) -> str:
        pass