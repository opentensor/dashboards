import pandas as pd

def diversity(x):
    return x.nunique()/len(x) if len(x)>0 else 0

def _nonempty(x):
    return x[x.astype(str).str.len()>0]

def successful_diversity(x):
    return diversity(_nonempty(x))

def success_rate(x):
    return len(_nonempty(x))/len(x) if len(x)>0 else 0

def threshold_rate(x, threshold):
    return (x>threshold).sum()/len(x)

def successful_nonzero_diversity(x):
    # To be used with groupby.apply
    return pd.Series({'completions_successful_nonzero_diversity': successful_diversity(x.loc[x['rewards']>0,'completions'])})
    
def completion_top_stats(x, exclude=None, ntop=1):
    # To be used with groupby.apply
    vc = x['completions'].value_counts()
    if exclude is not None:
        vc.drop(exclude, inplace=True, errors='ignore')
        
    rewards = x.loc[x['completions'].isin(vc.index[:ntop])].groupby('completions').rewards.agg(['mean','std','max'])
    return pd.DataFrame({
        'completions_top':rewards.index.tolist(),
        'completions_freq':vc.values[:ntop],
        'completions_reward_mean':rewards['mean'].values,
        'completions_reward_std':rewards['std'].values
        })

def top(x, i=0, exclude=''):
    return _nonempty(x).value_counts().drop(exclude, errors='ignore').index[i]

def freq(x, i=0, exclude=''):
    return _nonempty(x).value_counts().drop(exclude, errors='ignore').values[i]

def nonzero_rate(x):
    return (x>0).sum()/len(x)

def nonzero_mean(x):
    return x[x>0].mean()

def nonzero_std(x):
    return x[x>0].std()

def nonzero_median(x):
    return x[x>0].median()