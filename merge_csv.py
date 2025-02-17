import os
import pandas as pd

def merge_csv_files(directory, output_file):
    dataframes = []
    for filename in os.listdir(directory):
        if filename.endswith(".csv"):
            df = pd.read_csv(os.path.join(directory, filename))
            dataframes.append(df)
    if dataframes:  # Check if there are any dataframes to concatenate
        merged_df = pd.concat(dataframes, ignore_index=True)
        merged_df.to_csv(output_file, index=False)
    else:
        print("No CSV files found in the directory.")

# Merge all CSV files in the 'CSV' directory into a single file
merge_csv_files("CSV", "merged_data.csv")
