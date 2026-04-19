import pandas as pd

def load_data(filepath):
    return pd.read_csv(filepath)

def clean_data(df):
    df = df.drop_duplicates()
    df = df.fillna('Unknown')
    return df