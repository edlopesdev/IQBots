import pandas as pd

# Carregar os dados do arquivo CSV em um DataFrame
file_path = 'f:/Users/xdgee/Downloads/IQ bots/venv_name/merged_data.csv'
df = pd.read_csv(file_path)

# Salvar o DataFrame em um arquivo pickle
pickle_file_path = 'f:/Users/xdgee/Downloads/IQ bots/venv_name/merged_data.pkl'
df.to_pickle(pickle_file_path)

# Exibir o DataFrame
print(df)