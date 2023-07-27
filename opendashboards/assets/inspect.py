
import streamlit as st
import pandas as pd
import opendashboards.utils.utils as utils

def clean_data(df):
    return df.dropna(subset=df.filter(regex='completions|rewards').columns, how='any')

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

def highlight_row(row, expr, color='lightgrey', bg_color='white'):
    return [f'background-color:{color}' if expr else f'background-color:{bg_color}'] * len(row)