import os
import pandas as pd
from iqoptionapi.stable_api import IQ_Option
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
import numpy as np
import time
import json
import logging
import torch
import torch.nn as nn
import argparse
import joblib  # For saving and loading the model

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define file paths
credentials_file = os.path.normpath(os.path.join(os.getcwd(), "credentials.txt"))
csv_file_path = os.path.normpath(os.path.join(os.getcwd(), "merged_data.csv"))  # Update this path
progress_file = "progress.txt"
model_file = "trained_model.pkl"

def load_credentials():
    try:
        with open(credentials_file, "r") as file:
            lines = file.readlines()
            creds = {line.split('=')[0].strip(): line.split('=')[1].strip() for line in lines if '=' in line}
            return creds.get("email"), creds.get("password")
    except FileNotFoundError:
        logging.error("Credentials file not found.")
        return None, None

def load_data():
    expected_columns = [
        "Position ID", "Instrument", "Opening Date Time", "Asset", "Direction", "Quantity", "Opening price", 
        "Leverage", "TP", "SL", "Closing Date Time", "Closing price", "Investments", "Equity", "Commission", 
        "Overnight fee", "Swap", "Custodial fee", "Total PnL", "Gross PnL", "Net PnL", "Option Price", "Currency Conversion"
    ]
    try:
        data = pd.read_csv(csv_file_path)
        logging.info(f"CSV file loaded successfully with shape: {data.shape}")
        if not all(column in data.columns for column in expected_columns):
            missing_columns = set(expected_columns) - set(data.columns)
            raise ValueError(f"Missing columns in CSV file: {missing_columns}")
        return data
    except FileNotFoundError:
        logging.error("CSV file not found.")
        return None
    except ValueError as e:
        logging.error(e)
        return None
    
def connect_to_iq_option(email, password):
    global iq
    logging.info("Tentando conectar à API IQ Option...")
    iq = IQ_Option(email, password)
    try:
        check, reason = iq.connect()
        if check:
            iq.change_balance("PRACTICE")  # Alternar entre 'PRACTICE' e 'REAL'
            logging.info("Conexão bem-sucedida com a API IQ Option.")
        else:
            logging.error(f"Falha ao conectar à API IQ Option: {reason}")
            iq = None  # Garantir que iq seja None se a conexão falhar
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar JSON durante a conexão: {e}")
        iq = None
    except Exception as e:
        logging.error(f"Erro inesperado durante a conexão: {e}")
        iq = None
    return check if 'check' in locals() else False, reason if 'reason' in locals() else "Unknown error"

def fetch_historical_data(asset, duration, candle_count):
    if iq is None:
        logging.error(f"API desconectada. Não é possível buscar dados históricos para {asset}.")
        return pd.DataFrame()  # Return an empty DataFrame if disconnected
    candles = iq.get_candles(asset, duration * 60, candle_count, time.time())
    df = pd.DataFrame(candles)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["max"].astype(float)
    df["low"] = df["min"].astype(float)
    return df


def load_csv_file(filepath):
    df = pd.read_csv(filepath)
    return df

def preprocess_data(csv_data):
    print("Preprocessing data...")
    # Drop rows with missing values
    csv_data = csv_data.dropna()
    
    # Convert categorical columns to numerical
    for column in csv_data.select_dtypes(include=['object']).columns:
        csv_data[column] = pd.factorize(csv_data[column])[0]
    
    # Normalize numerical columns
    for column in csv_data.select_dtypes(include=['number']).columns:
        csv_data[column] = (csv_data[column] - csv_data[column].mean()) / csv_data[column].std()
    
    # Ensure required columns are present
    if 'opening_price' not in csv_data.columns:
        csv_data['opening_price'] = csv_data['Opening price']
    if 'closing_price' not in csv_data.columns:
        csv_data['closing_price'] = csv_data['Closing price']
    if 'price_diff' not in csv_data.columns:
        csv_data['price_diff'] = csv_data['closing_price'] - csv_data['opening_price']
    if 'price_ratio' not in csv_data.columns:
        csv_data['price_ratio'] = csv_data['closing_price'] / csv_data['opening_price']
    
    return {'features': csv_data.iloc[:, :-1], 'labels': csv_data.iloc[:, -1]}


def create_model(input_shape):
    print("Creating model...")
    # Define a simple neural network model
    model = nn.Sequential(
        nn.Linear(input_shape, 128),
        nn.ReLU(),
        nn.Linear(128, 64),
        nn.ReLU(),
        nn.Linear(64, 1),
        nn.Sigmoid()
    )
    return model

# Load CSV data
csv_data = pd.read_csv(csv_file_path)

# Preprocess data
processed_data = preprocess_data(csv_data)

clf = MLPClassifier(hidden_layer_sizes=(100,), max_iter=500)
clf.fit(processed_data['features'], processed_data['labels'])


def preprocess_new_data(new_data):
    # Assuming new_data is a DataFrame similar to the training data
    new_data = new_data.dropna()
    
    for column in new_data.select_dtypes(include=['object']).columns:
        new_data[column] = pd.factorize(new_data[column])[0]
    
    for column in new_data.select_dtypes(include=['number']).columns:
        new_data[column] = (new_data[column] - new_data[column].mean()) / new_data[column].std()
    
    if 'opening_price' not in new_data.columns:
        new_data['opening_price'] = new_data['Opening price']
    if 'closing_price' not in new_data.columns:
        new_data['closing_price'] = new_data['Closing price']
    if 'price_diff' not in new_data.columns:
        new_data['price_diff'] = new_data['closing_price'] - new_data['opening_price']
    if 'price_ratio' not in new_data.columns:
        new_data['price_ratio'] = new_data['closing_price'] / new_data['opening_price']
    
    return new_data

def make_predictions(model, new_data):
    print("Making predictions...")
    # Check if CUDA is available and move data to GPU if needed
    device = torch.device('cuda' if use_cuda else 'cpu')
    
    try:
        with torch.no_grad():
            model.eval()
            inputs = preprocess_new_data(new_data)
            inputs = torch.tensor(inputs).to(device)
            
            outputs = model(inputs)
            return outputs.cpu().numpy()  # Move back to CPU for user
    except:
        print("Error: Could not make predictions due to device mismatch.")
        return None

def save_progress(index):
    with open(progress_file, "w") as file:
        file.write(str(index))

def load_progress():
    try:
        with open(progress_file, "r") as file:
            return int(file.read().strip())
    except FileNotFoundError:
        logging.warning("Progress file not found. Starting from the beginning.")
        return 0
    except ValueError:
        logging.warning("Invalid progress file content. Starting from the beginning.")
        return 0


def train_model():
    # Load pickle data
    logging.info("Loading pickle data...")
    pickle_file_path = 'f:/Users/xdgee/Downloads/IQ bots/venv_name/merged_data.pkl'
    csv_data = pd.read_pickle(pickle_file_path)
    logging.info(f"Pickle data loaded with shape: {csv_data.shape}")
    
    # Check if the DataFrame is empty
    if csv_data.empty:
        raise ValueError("The loaded DataFrame is empty.")
    
    # Load progress
    start_index = load_progress()
    logging.info(f"Resuming from index: {start_index}")
    
    processed_data = preprocess_data(csv_data)
    logging.info(f"Processed data shape: {processed_data['features'].shape}")
    
    # Check if processed data is empty
    if processed_data['features'].shape[0] == 0:
        raise ValueError("No samples found in the processed data.")
    
    # Define and train the model
    clf = MLPClassifier(hidden_layer_sizes=(100,), max_iter=500)
    clf.fit(processed_data['features'], processed_data['labels'])
    
    # Save the trained model
    joblib.dump(clf, model_file)
    logging.info("Model training complete and saved to", model_file)

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description='Train a machine learning model for trading.')
    parser.add_argument('--use-cuda', dest='use_cuda', action='store_true',
                        help='Use CUDA-enabled GPUs for training (if available).')
    args = parser.parse_args()
    
    use_cuda = args.use_cuda and torch.cuda.is_available()
    
    # Train the model
    train_model()

# Example usage
email, password = load_credentials()
data = load_data()
if data is not None:
    logging.info("Data loaded successfully.")
else:
    logging.error("Failed to load data.")