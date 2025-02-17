import os
import logging
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

import time
from model_management import load_model, save_model


def preprocess_data(csv_data):
    logging.info("Preprocessing data...")
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
    
    logging.info(f"Processed data shape: {csv_data.shape}")
    return {'features': csv_data[['opening_price', 'closing_price', 'price_diff', 'price_ratio']], 'labels': csv_data.iloc[:, -1]}

def preprocess_new_data(new_data):
    logging.info("Preprocessing new data...")
    # Drop rows with missing values
    new_data = new_data.dropna()
    
    # Convert categorical columns to numerical
    for column in new_data.select_dtypes(include=['object']).columns:
        new_data[column] = pd.factorize(new_data[column])[0]
    
    # Normalize numerical columns
    for column in new_data.select_dtypes(include=['number']).columns:
        new_data[column] = (new_data[column] - new_data[column].mean()) / new_data[column].std()
    
    # Ensure required columns are present
    if 'opening_price' not in new_data.columns:
        new_data['opening_price'] = new_data['Opening price']
    if 'closing_price' not in new_data.columns:
        new_data['closing_price'] = new_data['Closing price']
    if 'price_diff' not in new_data.columns:
        new_data['price_diff'] = new_data['closing_price'] - new_data['opening_price']
    if 'price_ratio' not in new_data.columns:
        new_data['price_ratio'] = new_data['closing_price'] / new_data['opening_price']
    
    logging.info(f"Processed new data shape: {new_data.shape}")
    return {'features': new_data[['opening_price', 'closing_price', 'price_diff', 'price_ratio']], 'labels': new_data.iloc[:, -1]}


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

def preprocess_data(csv_data):
    logging.info("Preprocessing data...")
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
    
    logging.info(f"Processed data shape: {csv_data.shape}")
    return {'features': csv_data.iloc[:, :-1], 'labels': csv_data.iloc[:, -1]}

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

# Function to create a new model
def create_model():
    return MLPClassifier(hidden_layer_sizes=(100,), max_iter=500)

# Function to train the model with new data
def train_model(model, X, y):
    model.fit(X, y)
    return model

# Function to save the trained model
def save_trained_model(model, model_file):
    save_model(model, model_file)

# Load the trained model or create a new one if it doesn't exist
model_file = "models/trained_model.pkl"
clf = load_model(model_file)

if clf is None:
    clf = create_model()

# Load new data for predictions
new_data_file = "data/new_data.csv"
new_data = pd.read_csv(new_data_file)

# Preprocess the new data
processed_data = preprocess_data(new_data)

# Ensure data is not empty
if processed_data.empty:
    raise ValueError("No data available for predictions.")

# Make predictions
X_new = processed_data[['opening_price', 'closing_price', 'price_diff', 'price_ratio']]
predictions = clf.predict(X_new)

# Output predictions
print("Predictions:", predictions)

# Function to monitor trades and train the model with new data
def monitor_trade(trade_id, asset, data_before, indicators_before):
    global clf
    try:
        print(f"Monitoring trade {trade_id} for asset {asset}...")
        log_message(f"Monitoring trade {trade_id} for asset {asset}...")
        result = None
        while result is None:
            try:
                result = iq.check_win_v4(trade_id)
                if result is None:
                    print(f"Trade {trade_id} not concluded yet. Trying again in 1 second...")
                    log_message(f"Trade {trade_id} not concluded yet. Trying again in 1 second...")
                    time.sleep(1)
            except Exception as e:
                print(f"Error checking trade status {trade_id}: {e}")
                log_message(f"Error checking trade status {trade_id}: {e}")
                time.sleep(1)

        # Simulate getting new data for training
        new_trade_data = {
            'opening_price': data_before['opening_price'],
            'closing_price': data_before['closing_price'],
            'price_diff': data_before['closing_price'] - data_before['opening_price'],
            'price_ratio': data_before['closing_price'] / data_before['opening_price'],
            'result': result
        }
        new_trade_df = pd.DataFrame([new_trade_data])

        # Preprocess new trade data
        processed_new_trade_data = preprocess_new_data(new_trade_df)

        # Train the model with new trade data
        X_train = processed_new_trade_data[['opening_price', 'closing_price', 'price_diff', 'price_ratio']]
        y_train = processed_new_trade_data['result']
        clf = train_model(clf, X_train, y_train)

        # Save the trained model
        save_trained_model(clf, model_file)

    except Exception as e:
        print(f"Error monitoring trade {trade_id}: {e}")
        log_message(f"Error monitoring trade {trade_id}: {e}")
# Define log_message function
def log_message(message):
    logging.info(message)

# Define or import iq object
class IQ:
    def check_win_v4(self, trade_id):
        # Placeholder for actual implementation
        return None

iq = IQ()


if __name__ == "__main__":
    # Simulate monitoring a trade
    monitor_trade(trade_id=12345, asset="EURUSD", data_before={'opening_price': 1.1, 'closing_price': 1.2}, indicators_before={})

# Carregar os dados do arquivo CSV em um DataFrame
file_path = 'f:/Users/xdgee/Downloads/IQ bots/venv_name/merged_data.csv'
df = pd.read_csv(file_path)

# Exibir o DataFrame
print(df)

# Função para treinar o modelo
def train_model(features, labels):
    if len(features) == 0 or len(labels) == 0:
        raise ValueError("Features and labels must not be empty.")
    
    # Dividir os dados em conjuntos de treinamento e teste
    X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
    
    # Criar e treinar o modelo
    clf = MLPClassifier(random_state=1, max_iter=300)
    clf.fit(X_train, y_train)
    
    # Avaliar o modelo
    predictions = clf.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Model accuracy: {accuracy * 100:.2f}%")
    
    return clf

# Exemplo de uso da função train_model
features = np.random.rand(100, 26)  # Exemplo de dados de entrada
labels = np.random.randint(2, size=100)  # Exemplo de rótulos


try:
    model = train_model(features, labels)
    print("Model trained successfully.")
except ValueError as e:
    print(f"Error: {e}")

# Salvar o modelo treinado
def save_trained_model(model, filename):
    import joblib
    joblib.dump(model, filename)
    print(f"Model saved to {filename}")

# Exemplo de uso da função save_trained_model
model_file = "trained_model.pkl"
save_trained_model(model, model_file)