
import streamlit as st
import pandas as pd
import opendashboards.utils.utils as utils

@st.cache_data
def explode_data(df):
    list_cols = utils.get_list_col_lengths(df)
    try:
        return utils.explode_data(df, list(list_cols.keys())).apply(pd.to_numeric, errors='ignore')
    except Exception as e:
        st.error(f'Error exploding data with columns')
        st.write(list_cols)
        st.exception(e)
        st.dataframe(df)
        st.stop()

@st.cache_data
def completions(df_long, col):
    return df_long[col].value_counts()

@st.cache_data
def weights(df, index='_timestamp'):
    # Create a column for each UID and show most recent rows
    scores = df['moving_averaged_scores'].apply(pd.Series).fillna(method='ffill')
    if index in df.columns:
        scores.index = df[index]

    # rename columns
    scores.rename({i: f'UID-{i}' for i in range(scores.shape[1])}, axis=1, inplace=True)
    return scores    
    
def run_event_data(df_runs, df, selected_runs):
    
    st.markdown('#')

    show_col1, show_col2 = st.columns(2)
    show_runs = show_col1.checkbox('Show runs', value=True)
    show_events = show_col2.checkbox('Show events', value=False)
    if show_runs:
        st.markdown(f'Wandb info for **{len(selected_runs)} selected runs**:')
        st.dataframe(df_runs.loc[df_runs.id.isin(selected_runs)],
                    column_config={
                        "url": st.column_config.LinkColumn("URL"),
                    }
        )

    if show_events:
        st.markdown(f'Raw events for **{len(selected_runs)} selected runs**:')
        st.dataframe(df.head(50),
                    column_config={
                        "url": st.column_config.LinkColumn("URL"),
                    }
        )