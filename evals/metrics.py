import pandas as pd
from typing import Tuple

def calculate_accuracy(dataframe: pd.DataFrame, answer_column: str, answer_key: str) -> Tuple[pd.DataFrame, float]:
    pattern = r'^([ABCDEFGH12345678])\s?-?.*'
    dataframe['clean_answers'] = dataframe[answer_column].str.extract(pattern)[0]
    dataframe['is_correct'] = dataframe['clean_answers'].str.lower() == dataframe[answer_key].str.lower()
    accuracy = dataframe['is_correct'].sum() / len(dataframe) * 100        
    return dataframe, accuracy