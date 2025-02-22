#!/usr/bin/env python
# Arquivo: Capybara.7.7.py
#PECUNIA IMPROMPTA
#Código construido com Copilot e otimizado utilizando DeepSeek, o ChatGPT de flango.
from iqoptionapi.stable_api import IQ_Option
import threading
import time
import os
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import PhotoImage
import pandas as pd
import pandas_ta as ta
import json
import logging
import warnings
import sys
import yfinance as yf  # Import yfinance library
import requests  # Import requests library
from pyti.relative_strength_index import relative_strength_index as pyti_rsi
from pyti.moving_average_convergence_divergence import moving_average_convergence_divergence as pyti_macd
from pyti.simple_moving_average import simple_moving_average as pyti_sma
from pyti.exponential_moving_average import exponential_moving_average as pyti_ema
from pyti.bollinger_bands import percent_b as pyti_bollinger
from pyti.average_true_range import average_true_range as pyti_atr
from pyti.stochastic import percent_k as pyti_stochastic
from pyti.williams_percent_r import williams_percent_r as pyti_willr
from pyti.commodity_channel_index import commodity_channel_index as pyti_cci
from pyti.rate_of_change import rate_of_change as pyti_roc
from pyti.on_balance_volume import on_balance_volume as pyti_obv
from pyti.money_flow_index import money_flow_index as pyti_mfi
from pyti.detrended_price_oscillator import detrended_price_oscillator as pyti_dpo
from pyti.ultimate_oscillator import ultimate_oscillator as pyti_ultimate
from pyti.aroon import aroon_up as pyti_aroon_up, aroon_down as pyti_aroon_down
from trading_strategy import should_open_trade, should_abandon_trade, calculate_success_probability, should_enter_trade
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from model_management import load_model, save_model



# Função para ler as credenciais do arquivo credentials.txt
def read_credentials(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        email = lines[0].strip()
        password = lines[1].strip()
    return email, password

# Caminho para o arquivo de credenciais
credentials_file = 'credentials.txt'

# Ler as credenciais do arquivo
email, password = read_credentials(credentials_file)

# Instancie a classe IQ_Option com os argumentos necessários
iq = IQ_Option(email, password)
## Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("training.log"),
    logging.StreamHandler()
])


class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.insert(tk.END, str, (self.tag,))
        self.widget.see(tk.END)

    def flush(self):
        pass


# Função para buscar os 60 candles de 1 minuto antes de cada trade
def fetch_candles(asset, timestamp):
    candles = iq.get_candles(asset, 60, 60, timestamp)
    return candles

# Função para buscar os dados de indicadores e volatilidade
def fetch_additional_data(asset, timestamp):
    # Exemplo de como buscar dados adicionais (substitua pela lógica real da sua API)
    # Aqui você pode adicionar a lógica para buscar indicadores e volatilidade
    return {
        'indicators': {},  # Substitua pela lógica real para buscar indicadores
        'volatility': 0.0  # Substitua pela lógica real para buscar volatilidade
    }

def store_data(data):
    # Store the data in a file or database for training the AI model
    with open('trading_data.json', 'a') as f:
        json.dump(data, f)
        f.write('\n')

def on_trade_open(asset, timestamp):
    # Fetch candles and additional data when a trade is opened
    candles = fetch_candles(asset, timestamp)
    additional_data = fetch_additional_data(asset, timestamp)
    return candles, additional_data

def on_trade_close(trade_result, trade_value, asset, timestamp):
    # Fetch candles and additional data when a trade is closed
    candles, additional_data = on_trade_open(asset, timestamp)
    if candles and additional_data:
        data = {
            'asset': asset,
            'timestamp': timestamp,
            'trade_result': trade_result,
            'trade_value': trade_value,
            'candles': candles,
            'indicators': additional_data.get('indicators'),
            'volatility': additional_data.get('volatility')
        }
  

def open_trade(asset, amount, action):
    # Open a real trade using IQ Option API
    logging.info(f"Abrindo negociação: {asset}, {amount}, {action}")
    timestamp = int(time.time())
    candles, additional_data = on_trade_open(asset, timestamp)
    check, trade_id = iq.buy(amount, asset, action, 1)  # Exemplo de abertura de negociação
    if check:
        logging.info(f"Negociação aberta com sucesso: {trade_id}")
        # Esperar o resultado da negociação
        while True:
            check, win = iq.check_win_v3(trade_id)
            if check:
                trade_result = "win" if win > 0 else "loss"
                trade_value = win
                on_trade_close(trade_result, trade_value, asset, timestamp)
                break
    else:
        logging.error("Falha ao abrir a negociação")

def save_console_output():
    current_date = time.strftime("%Y-%m-%d")
    log_filename = f"console_output_{current_date}.txt"
    log_filepath = os.path.join(os.getcwd(), log_filename)
    
    with open(log_filepath, "w") as file:
        file.write(log_text.get(1.0, tk.END))

def process_message(message):
    try:
        # Assuming the message is a JSON string and contains relevant fields
        decoded_message = json.loads(message)
        asset = decoded_message.get('asset')
        timestamp = decoded_message.get('timestamp')

        # Fetch candles and additional data
        candles = fetch_candles(asset, timestamp)
        additional_data = fetch_additional_data(asset, timestamp)

        if candles and additional_data:
            data = {
                'asset': asset,
                'price': decoded_message.get('price'),
                'timestamp': timestamp,
                'indicators': additional_data.get('indicators'),
                'volatility': additional_data.get('volatility'),
                'candles': candles,
                'trade_result': decoded_message.get('trade_result')
            }
            store_data(data)
    except Exception as e:
        logging.error(f"Erro ao processar mensagem: {e}")
        return None

def store_data(data):
    # Store the data in a file or database for training the AI model
    with open('trading_data.json', 'a') as f:
        json.dump(data, f)
        f.write('\n')

def on_trade_open(asset, timestamp):
    # Fetch candles and additional data when a trade is opened
    candles = fetch_candles(asset, timestamp)
    additional_data = fetch_additional_data(asset, timestamp)
    return candles, additional_data

def on_trade_close(trade_result, trade_value, asset, timestamp):
    # Fetch candles and additional data when a trade is closed
    candles, additional_data = on_trade_open(asset, timestamp)
    if candles and additional_data:
        data = {
            'asset': asset,
            'timestamp': timestamp,
            'trade_result': trade_result,
            'trade_value': trade_value,
            'candles': candles,
            'indicators': additional_data.get('indicators'),
            'volatility': additional_data.get('volatility')
        }
        store_data(data)

def save_console_output():
    current_date = time.strftime("%Y-%m-%d")
    log_filename = f"console_output_{current_date}.txt"
    log_filepath = os.path.join(os.getcwd(), log_filename)
    
    with open(log_filepath, "w") as file:
        file.write(log_text.get(1.0, tk.END))


# Schedule the save_console_output function to run every day at midnight
def schedule_daily_save():
    now = time.localtime()
    midnight = time.mktime((now.tm_year, now.tm_mon, now.tm_mday + 1, 0, 0, 0, 0, 0, 0))
    delay = midnight - time.mktime(now)
    threading.Timer(delay, save_console_output).start()

# Call the schedule_daily_save function to start the daily saving process
schedule_daily_save()

# Define the model file path
model_file = "IA/capybara-ai-project/models/trained_model.pkl"

# Trade data collection
trade_data = []

def collect_trade_data(trade_id, opening_price, closing_price, result, candles):
    logging.info(f"Collecting trade data for trade_id: {trade_id}")
    trade_data.append({
        'trade_id': trade_id,
        'opening_price': opening_price,
        'closing_price': closing_price,
        'price_diff': closing_price - opening_price,
        'price_ratio': closing_price / opening_price,
        'result': result,
        'candles': candles
    })

def preprocess_data(csv_data):
    logging.info("Preprocessing data...")
    # Drop rows with missing values
    csv_data = csv_data.dropna()
    
    # Convert categorical columns to numerical
    for column in csv_data.select_dtypes(include=['object']).columns:
        csv_data[column] = csv_data[column].astype('category').cat.codes
    
    # Normalize numerical columns
    for column in csv_data.select_dtypes(include=['number']).columns:
        csv_data[column] = (csv_data[column] - csv_data[column].mean()) / csv_data[column].std()
    
    # Ensure required columns are present
    required_columns = ['opening_price', 'closing_price', 'price_diff', 'price_ratio']
    for column in required_columns:
        if column not in csv_data.columns:
            raise ValueError(f"Missing required column: {column}")
    
    logging.info(f"Processed data shape: {csv_data.shape}")
    return {'features': csv_data[required_columns], 'labels': csv_data['result']}


def train_model_with_collected_data():
    if not trade_data:
        logging.warning("No trade data collected for training.")
        return

    logging.info("Starting model training with collected trade data...")
    df = pd.DataFrame(trade_data)
    logging.info(f"Collected trade data: {df.head()}")  # Log the first few rows of collected data
    processed_data = preprocess_data(df)

    X = processed_data['features']
    y = processed_data['labels']

    if X.empty or y.empty:
        logging.warning("Processed trade data is empty. Skipping training.")
        return

    logging.info("Splitting data into training and testing sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    logging.info("Initializing the MLPClassifier...")
    clf = MLPClassifier(max_iter=200)

    logging.info("Fitting the model...")
    clf.fit(X_train, y_train)

    logging.info("Predicting on the test set...")
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Model accuracy: {accuracy}")

    logging.info("Saving the trained model...")
    save_model(clf, "IA/capybara-ai-project/models/trained_model.pkl")
    logging.info("Model saved successfully.")

def get_trade_result(trade_id):
    # Implement logic to get the trade result (e.g., win or loss)
    # This is a placeholder implementation
    return 1  # Assume 1 for win and 0 for loss

def collect_candles(asset, interval, count):
    candles = IQ_Option.get_candles(asset, interval, count, time.time())
    return candles

def open_trade(asset, amount, action):
    # Open a real trade using IQ Option API
    logging.info(f"Opening trade for asset {asset} with amount {amount} and action {action}")
    check, trade_id = iq.buy(amount, asset, action, 1)  # 1 represents the duration in minutes

    if check:
        logging.info(f"Trade opened successfully with trade_id: {trade_id}")
        opening_price = iq.get_candles(asset, 60, 1, time.time())[0]['close']  # Get the opening price
        return trade_id, opening_price
    else:
        logging.error("Failed to open trade")
        return None, None

def monitor_trade(trade_id, asset, data_before, indicators_before):
    global simultaneous_trades
    global session_profit
    global consecutive_losses
    global current_amount
    global saldo_saida
    global amount_doubled

    try:
        logging.info(f"Monitoring trade {trade_id} for asset {asset}")
        # Collect candles during the trade
        candles = collect_candles(asset, 60, 10)  # Collect last 10 candles with 1-minute interval
        # Simulate getting new data for training
        result = get_trade_result(trade_id)
        closing_price = 1.2  # Placeholder closing price
        collect_trade_data(trade_id, data_before['opening_price'], closing_price, result, candles)
    except Exception as e:
        logging.error(f"Error monitoring trade {trade_id}: {e}")
    finally:
        # Existing code for monitoring trade
        pass

def end_trading_session():
    global data
    logging.info("Ending trading session...")
    train_model_with_collected_data()
    on_trade_close()
    logging.info("Trading session ended and model trained with collected data.")

# Carregar credenciais do arquivo
credentials_file = os.path.normpath(os.path.join(os.getcwd(), "credentials.txt"))

def load_credentials():
    try:
        with open(credentials_file, "r") as file:
            lines = file.readlines()
            creds = {line.split('=')[0].strip(): line.split('=')[1].strip() for line in lines if '=' in line}
            return creds.get("email"), creds.get("password")
    except FileNotFoundError:
        raise Exception("Arquivo de credenciais não encontrado. Certifique-se de que 'credentials.txt' está no diretório de trabalho.")

# Carregar credenciais
email, password = load_credentials()

log_file = os.path.normpath(os.path.join(os.getcwd(), f"trade_log_{time.strftime('%Y-%m-%d')}.txt"))

def log_message(message):
    try:
        with open(log_file, "a") as file:
            file.write(message + "\n")
    except FileNotFoundError:
        with open(log_file, "w") as file:
            file.write(message + "\n")
    logging.info(message)
    print(message)  # Ensure message is printed to the redirected stdout

# Função para tratar mensagens recebidas
def on_message(message):
    try:
        if not message:
            logging.error("Mensagem vazia recebida. Verifique o servidor ou a conexão.")
            return
        if not isinstance(message, str):
            logging.error(f"Mensagem não é uma string válida: {message}")
            return
        # Ensure the message is a valid JSON string
        if message.strip()[0] not in ['{', '[']:
            logging.error(f"Mensagem não é um JSON válido: {message}")
            return
        decoded_message = json.loads(message)
        logging.info(f"Mensagem decodificada: {decoded_message}")

        # Extract asset and timestamp from the message
        asset = decoded_message.get('asset')
        timestamp = decoded_message.get('timestamp')

        # Fetch candles and additional data
        candles = fetch_candles(asset, timestamp)
        additional_data = fetch_additional_data(asset, timestamp)

        if candles and additional_data:
            data = {
                'asset': asset,
                'price': decoded_message.get('price'),
                'timestamp': timestamp,
                'indicators': additional_data.get('indicators'),
                'volatility': additional_data.get('volatility'),
                'candles': candles,
                'trade_result': decoded_message.get('trade_result')
            }
            store_data(data)
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar mensagem JSON: {e}. Mensagem: {message}")
        # Add the asset to the ignore list
        asset = extract_asset_from_message(message)
        if asset:
            add_asset_to_ignore_list(asset)
        return  # Ignore the asset when a JSON decoding error occurs
    except Exception as e:
        logging.error(f"Erro inesperado ao processar mensagem: {e}. Mensagem: {message}")
        # Add the asset to the ignore list
        asset = extract_asset_from_message(message)
        if asset:
            add_asset_to_ignore_list(asset)
        return  # Ignore the asset when an unexpected error occurs

def store_data(data):
    # Store the data in a file or database for training the AI model
    with open('trading_data.json', 'a') as f:
        json.dump(data, f)
        f.write('\n')

def extract_asset_from_message(message):
    try:
        # Assuming the message is a JSON string and contains an 'asset' field
        decoded_message = json.loads(message)
        return decoded_message.get('asset')
    except Exception as e:
        logging.error(f"Erro ao extrair ativo da mensagem: {e}")
        return None

def add_asset_to_ignore_list(asset):
    global assets_to_ignore
    assets_to_ignore.add(asset.upper())


# Exemplo de uso da função on_message
on_message('{"key": "value"}')
on_message('')
on_message('not a json')

# Inicializar a API IQ Option
account_type = "PRACTICE"  # Conta Prática - Modo de teste
# account_type = "REAL"  # Conta Real
instrument_types = ["binary", "digital", "crypto", "otc"]  # Tipos de instrumentos suportados

# Definir variáveis globais
running = False
icon_label = None
initial_amount = 2
current_amount = 2  # Acompanhar o valor atual da negociação para estratégia Martingale
max_simultaneous_trades = 3
simultaneous_trades = 0  # Inicializar o contador de negociações simultâneas
martingale_limit = 5  # Limite de negociações Martingale consecutivas
consecutive_losses = 0
session_profit = 0
iq = None  # Instância da API IQ Option
trade_list = []
saldo_entrada = 0  # Saldo na hora de começar uma operação
saldo_saida = 0  # Saldo no fim da operação
amount_doubled = False  # Flag to track if the amount has been doubled

# Define preset trade value
auto_initial_amount = 2
smart_stop = False

def print_account_balance():
    balance = iq.get_balance()
    account_type_str = "PRACTICE" if account_type == "REAL" else "DEMO"
    log_message(f"Saldo: R${balance:.2f} - Conta {account_type_str}")

# Conectar à API IQ Option
def connect_to_iq_option(email, password):
    global iq
    log_message("Tentando conectar à API IQ Option...")
    iq = IQ_Option(email, password)
    try:
        check, reason = iq.connect()
        if check:
            iq.change_balance(account_type)  # Alternar entre 'PRACTICE' e 'REAL'
            log_message("Conexão bem-sucedida com a API IQ Option.")
            set_amount()  # Definir o valor inicial da negociação
            print_account_balance()  # Print account balance after successful connection
            update_session_profit()  # Update session profit after successful connection
        else:
            log_message(f"Falha ao conectar à API IQ Option: {reason}")
            iq = None  # Garantir que iq seja None se a conexão falhar
    except json.JSONDecodeError as e:
        log_message(f"Erro ao decodificar JSON durante a conexão: {e}")
        iq = None
    except Exception as e:
        log_message(f"Erro inesperado durante a conexão: {e}")
        iq = None
    return check if 'check' in locals() else False, reason if 'reason' in locals() else "Unknown error"

#

# Adapted fetch_sorted_assets function
def fetch_sorted_assets():
    logging.info("Buscando e classificando ativos por lucratividade e volume para negociações de 5 minutos...")
    reconnect_if_needed()

    if iq is None:
        logging.info("API desconectada. Não é possível buscar ativos.")
        return []

    try:
        assets = iq.get_all_ACTIVES_OPCODE()
        raw_profitability = iq.get_all_profit()
        raw_volume = {}  # Placeholder for actual volume fetching logic

        profitability = {}
        volume = {}
        for asset, values in raw_profitability.items():
            if isinstance(values, dict):  # Tratamento para defaultdict
                profitability[asset] = float(values.get('turbo', 0.0))  # 'turbo' is used for 5-minute trades
            else:
                profitability[asset] = float(values)

        # Populate volume dictionary with actual volume data
        for asset in assets.keys():
            volume[asset] = 0  # Placeholder for actual volume data

        sorted_assets = sorted(
            assets.keys(),
            key=lambda asset: (profitability.get(asset, 0.0), volume.get(asset, 0)),
            reverse=True
        )

        log_message(f"Ativos classificados por lucratividade e volume para negociações de 5 minutos: {sorted_assets[:100]}")
        return sorted_assets[:100]  # Return top 100 assets
    except Exception as e:
        log_message(f"Erro ao buscar e classificar ativos: {e}")
        return []

def add_trade_to_list(trade_id):
    global trade_list
    trade_list.append(trade_id)
    print(f"Trade ID {trade_id} added to the monitoring list.")
    log_message(f"Trade ID {trade_id} added to the monitoring list.")

def reconnect_if_needed():
    global iq, running
    if iq is None or not iq.check_connect():
        log_message("API desconectada. Tentando reconectar...")
        connect_to_iq_option(email, password)
        if not iq or not iq.check_connect():
            log_message("Falha na reconexão. Saindo...")
            running = False
        else:
            if not running:
                running = True
                threading.Thread(target=execute_trades).start()  # Restart trading if it was stopped

def fetch_historical_data(asset, duration, candle_count):
    reconnect_if_needed()
    if iq is None:
        log_message(f"API desconectada. Não é possível buscar dados históricos para {asset}.")
        return pd.DataFrame()  # Return an empty DataFrame if disconnected
    candles = iq.get_candles(asset, duration * 60, candle_count, time.time())
    df = pd.DataFrame(candles)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["max"].astype(float)
    df["low"] = df["min"].astype(float)
    return df

# Função para reconectar à API
def reconnect():
    global iq, running
    while True:
        try:
            if iq is None or not iq.check_connect():
                logging.info("Reconectando à API IQ Option...")
                iq = IQ_Option(email, password)
                check, reason = iq.connect()
                if check:
                    iq.change_balance(account_type)
                    logging.info("Reconexão bem-sucedida.")
                    set_amount()  # Definir o valor inicial da negociação
                    print_account_balance()  # Print account balance after successful connection
                    update_session_profit()  # Update session profit after successful connection
                    if not running:
                        running = True
                        threading.Thread(target=execute_trades).start()  # Restart trading if it was stopped
                else:
                    logging.error(f"Falha na reconexão: {reason}")
            time.sleep(10)  # Increase sleep time to avoid rapid reconnection attempts
        except json.JSONDecodeError as e:
            logging.error(f"Erro ao decodificar JSON durante a reconexão: {e}")
            iq = None
        except Exception as e:
            logging.error(f"Erro inesperado durante a reconexão: {e}")
            iq = None

# Ensure reconnection logic is executed in the main thread
if __name__ == "__main__":
    threading.Thread(target=reconnect, daemon=True).start()

# Define the ignore_assets function
assets_to_ignore = set(["MSFT","AUDMXN","CSGNZ-CHIX","TA25","DUBAI","YAHOO", "TWITTER", "AGN:US", "CXO:US","DNB:US","DOW:US","DTE:US","DUK:US","DVA:US","DVN:US","DXC:US","DXCM:US", "ETFC:US", "TWX:US"])

def ignore_assets(asset):
    if instrument_types == ["forex"] and "-OTC" in asset.upper():
        return True
    return asset.upper() in assets_to_ignore or "-CHIX" in asset.upper() or "XEMUSD-" in asset.upper() or "BSVUSD-" in asset.upper()

def analyze_last_candles(data):
    """
    Analyzes the last 5 candles of 5 seconds each.
    Returns 'up', 'down', or 'neutral' based on the analysis.
    """
    if len(data) < 5:
        log_message("Dados insuficientes para análise dos últimos candles.")
        return "neutral"

    first_candle = data.iloc[-5]
    if first_candle["close"] > first_candle["open"]:
        return "up"
    elif first_candle["close"] < first_candle["open"]:
        return "down"
    else:
        return "neutral"

def analyze_trend(asset):
    """
    Analyzes the trend based on the last 15 minutes of 1-minute candles.
    Returns 'up', 'down', or 'neutral' based on the analysis.
    """
    data = fetch_historical_data(asset, 1, 15)
    if data is None or data.empty:
        log_message(f"Sem dados suficientes para análise de tendência de {asset}.")
        return "neutral"

    first_5_avg = data["close"].iloc[:5].mean()
    middle_5_avg = data["close"].iloc[5:10].mean()
    last_5_avg = data["close"].iloc[10:].mean()

    if first_5_avg > middle_5_avg > last_5_avg:
        return "down"
    elif first_5_avg < middle_5_avg < last_5_avg:
        return "up"
    else:
        return "neutral"

def analyze_indicators(asset):
    if ignore_assets(asset):
        log_message(f"Ignorando ativo {asset}.")
        return None

    trend = analyze_trend(asset)
    if trend == "neutral":
        log_message(f"Mercado lateralizado para {asset}. Pulando ativo.")
        return None

    log_message(f"Analisando indicadores para {asset}...")
    try:
        data = fetch_historical_data(asset, 1, 100)

        if data is None or data.empty:
            log_message(f"Sem dados suficientes para {asset}. Pulando ativo.")
            return None

        # Ensure all columns are cast to compatible dtypes
        data["close"] = data["close"].astype(float)
        data["open"] = data["open"].astype(float)
        data["high"] = data["high"].astype(float)
        data["low"] = data["low"].astype(float)
        if "volume" in data.columns:
            data["volume"] = data["volume"].astype(float)

        indicators = {}
        available_indicators = {
            "rsi": lambda: ta.rsi(data["close"], length=14),
            "macd": lambda: ta.macd(data["close"])["MACD_12_26_9"],
            "ema": lambda: ta.ema(data["close"], length=9),
            "sma": lambda: ta.sma(data["close"], length=20),
            "stochastic": lambda: ta.stoch(data["high"], data["low"], data["close"])["STOCHk_14_3_3"],
            "atr": lambda: ta.atr(data["high"], data["low"], data["close"], length=14),
            "adx": lambda: ta.adx(data["high"], data["low"], data["close"], length=14),
            "bollinger_high": lambda: ta.bbands(data["close"])["BBU_20_2.0"] if "BBU_20_2.0" in ta.bbands(data["close"]) else None,
            "bollinger_low": lambda: ta.bbands(data["close"])["BBL_20_2.0"] if "BBL_20_2.0" in ta.bbands(data["close"]) else None,
            "cci": lambda: ta.cci(data["high"], data["low"], data["close"], length=20),
            "willr": lambda: ta.willr(data["high"], data["low"], data["close"], length=14),
            "roc": lambda: ta.roc(data["close"], length=12),
            "obv": lambda: ta.obv(data["close"], data["volume"]),
            "trix": lambda: ta.trix(data["close"], length=15),
            "mfi": lambda: ta.mfi(data["high"], data["low"], data["close"], data["volume"], length=14).astype(float),
            "dpo": lambda: ta.dpo(data["close"], length=14),
            "keltner_upper": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCUp_20_2.1"] if "KCUp_20_2.1" in ta.kc(data["high"], data["low"], data["close"], length=20) else None,
            "keltner_lower": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCLo_20_2.1"] if "KCLo_20_2.1" in ta.kc(data["high"], data["low"], data["close"], length=20) else None,
            "ultimate_oscillator": lambda: ta.uo(data["high"], data["low"], data["close"]),
            "tsi": lambda: ta.tsi(data["close"]),
            "aroon_up": lambda: ta.aroon(data["high"], data["low"], length=25)["AROONU_25"],
            "aroon_down": lambda: ta.aroon(data["high"], data["low"], length=25)["AROOND_25"],
            "last_candles": lambda: analyze_last_candles(data),
        }

        for key, func in available_indicators.items():
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("error", category=FutureWarning)
                    result = func()
                    if result is not None and not isinstance(result, str) and not result.empty:
                        indicators[key] = result.iloc[-1] if isinstance(result, pd.Series) else result
            except FutureWarning as fw:
                log_message(f"FutureWarning ao calcular {key.upper()} para {asset}: {fw}. Pulando indicador.")
                indicators[key] = None
            except Exception as e:
                log_message(f"Erro ao calcular {key.upper()} para {asset}: {e}")
                indicators[key] = None

        decisions = []

        if indicators.get("rsi") is not None:
            if indicators["rsi"] < 30:
                decisions.append("buy")
            elif indicators["rsi"] > 70:
                decisions.append("sell")

        if indicators.get("macd") is not None:
            if indicators["macd"] > 0:
                decisions.append("buy")
            elif indicators["macd"] < 0:
                decisions.append("sell")

        if indicators.get("ema") is not None:
            if data["close"].iloc[-1] > indicators["ema"] and trend == "up":
                decisions.append("buy")
            elif data["close"].iloc[-1] < indicators["ema"] and trend == "down":
                decisions.append("sell")

        if indicators.get("sma") is not None:
            if data["close"].iloc[-1] > indicators["sma"] and trend == "up":
                decisions.append("buy")
            elif data["close"].iloc[-1] < indicators["sma"] and trend == "down":
                decisions.append("sell")

        if indicators.get("stochastic") is not None:
            if indicators["stochastic"] < 20:
                decisions.append("buy")
            elif indicators["stochastic"] > 80:
                decisions.append("sell")

        if indicators.get("bollinger_low") is not None and indicators.get("bollinger_high") is not None:
            if data["close"].iloc[-1] < indicators["bollinger_low"]:
                decisions.append("buy")
            elif data["close"].iloc[-1] > indicators["bollinger_high"]:
                decisions.append("sell")

        if indicators.get("cci") is not None:
            if indicators["cci"] < -100:
                decisions.append("buy")
            elif indicators["cci"] > 100:
                decisions.append("sell")

        if indicators.get("willr") is not None:
            if indicators["willr"] < -80:
                decisions.append("buy")
            elif indicators["willr"] > -20:
                decisions.append("sell")

        if indicators.get("roc") is not None:
            if indicators["roc"] > 0:
                decisions.append("buy")
            else:
                decisions.append("sell")

        if indicators.get("mfi") is not None:
            if indicators["mfi"] < 20:
                decisions.append("buy")
            elif indicators["mfi"] > 80:
                decisions.append("sell")

        if indicators.get("aroon_up") is not None and indicators.get("aroon_down") is not None:
            if indicators["aroon_up"] > 70:
                decisions.append("buy")
            if indicators["aroon_down"] > 70:
                decisions.append("sell")

        if indicators.get("last_candles") is not None:
            if indicators["last_candles"] == "up":
                decisions.append("buy")
            elif indicators["last_candles"] == "down":
                decisions.append("sell")

        buy_votes = decisions.count("buy")
        sell_votes = decisions.count("sell")
        total_votes = buy_votes + sell_votes

        log_message(f"Votação de indicadores para {asset}: BUY={buy_votes}, SELL={sell_votes}")
        log_message(f"Decisões: {decisions}")

        if total_votes == 0:
            log_message("Nenhum voto válido. Pulando ativo.")
            return None

        majority = (total_votes // 2) + 2  # Update majority to 50%+2

        if consecutive_losses >= 2:  # Invert votes starting from the third Martingale
            print("Terceiro Martingale - Invertendo indicadores")
            buy_votes, sell_votes = sell_votes, buy_votes

        if buy_votes >= majority:
            return "buy"
        elif sell_votes >= majority:
            return "sell"
        else:
            log_message("Consenso insuficiente entre os indicadores. Pulando ativo.")
            return None

    except Exception as e:
        log_message(f"Erro ao analisar indicadores para {asset}: {e}")
        return None

def countdown(seconds):
    while seconds > 0:
        log_message(f"Aguardando {seconds} segundos...")
        time.sleep(1)
        seconds -= 1

# Parâmetro de diferença mínima, perda máxima e probabilidade mínima
MIN_DIFFERENCE = 0.0005
MAX_LOSS = 0.0010
MIN_PROBABILITY = 0.6

def calculate_volatility(data):
    """
    Calculate the volatility of the asset based on historical data.
    """
    data['returns'] = data['close'].pct_change()
    volatility = data['returns'].std() * (252 ** 0.5)  # Annualized volatility
    return volatility

def is_high_volatility(asset):
    """
    Determine if the asset has high volatility.
    """
    data = fetch_historical_data(asset, 1, 20)  # Fetch last 20 candles of 1 minute each
    if data is None or data.empty:
        log_message(f"Sem dados suficientes para {asset}. Pulando ativo.")
        return False

    volatility = calculate_volatility(data)
    log_message(f"Volatilidade calculada para {asset}: {volatility:.2f}")
    return volatility > 0.05  # Example threshold for high volatility

def should_open_trade(opening_price, closing_price, min_difference):
    """
    Determine if a trade should be opened based on the price difference.
    """
    price_difference = abs(opening_price - closing_price)
    if price_difference < min_difference:
        log_message(f"Preço de abertura: {opening_price}, Preço de fechamento: {closing_price}, Diferença: {price_difference}")
        return False
    return True

# Adapted execute_trades function
def execute_trades():
    global running
    global current_amount
    global consecutive_losses
    global session_profit
    global simultaneous_trades
    global saldo_entrada
    global data

    while running:
        log_message("Executando negociações...")
        assets = fetch_sorted_assets()

        if not assets:
            log_message("Nenhum ativo encontrado. Parando execução.")
            break

        for asset in assets:
            if not running:
                log_message("Execução de negociações interrompida.")
                break

            if ignore_assets(asset):
                log_message(f"Ignorando ativo {asset}.")
                continue

            if simultaneous_trades >= max_simultaneous_trades:
                log_message("Número máximo de negociações simultâneas atingido. Aguardando...")
                countdown(50)  # Adjusted countdown for 5-minute trades
                check_trade_results()
                update_session_profit()                               
                continue

            # Ensure results are checked periodically and reset amount if needed
            check_trade_results()
            update_session_profit()
            
            

            if is_high_volatility(asset):
                log_message(f"Alta volatilidade detectada para {asset}. Pulando ativo.")
                continue

            decision = analyze_indicators(asset)
            if decision == "buy":
                action = "call"
            elif decision == "sell":
                action = "put"
            else:
                log_message(f"Pulando negociação para {asset}. Sem consenso ou tendência contrária.")
                continue

            log_message(f"Tentando realizar negociação: Ativo={asset}, Ação={action}, Valor = R${current_amount}")
            saldo_entrada = iq.get_balance()  # Store balance before trade
            print(f"Balance before opening trade: {saldo_entrada}")  # Display balance before trade

            # Verificar a disponibilidade do ativo antes de tentar negociar
            available_assets = iq.get_all_ACTIVES_OPCODE()
            if asset not in available_assets:
                log_message(f"Ativo {asset} não encontrado na plataforma. Pulando ativo.")
                continue

            try:
                success, trade_id = iq.buy(current_amount, asset, action, 5)  # Negociações de 5 minutos
                if success:
                    simultaneous_trades += 1
                    add_trade_to_list(trade_id)
                    log_message(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
                    print(f"Balance after opening trade: {iq.get_balance()}")  # Display balance after opening trade
                    threading.Thread(target=monitor_trade, args=(trade_id, asset)).start()
                else:
                    log_message(f"Falha ao realizar negociação para {asset}. Motivo: {trade_id}")  # Log the reason for failure
            except Exception as e:
                log_message(f"Erro durante a execução da negociação para {asset}: {e}")
                if "WinError 10054" in str(e):
                    log_message("Conexão perdida. Tentando reconectar...")
                    reconnect_if_needed()
                    if iq and iq.check_connect():
                        log_message("Reconexão bem-sucedida. Continuando operações.")
                        continue
                    else:
                        log_message("Falha na reconexão. Parando operações.")
                        running = False
                        break

        # Ensure results are checked periodically
        check_trade_results()
        update_session_profit()
        train_model_with_collected_data(data)
        

        if smart_stop and current_amount == initial_amount:
            running = False
            save_console_output()
            train_model_with_collected_data()
            data
            log_message("Smart Stop ativado. Parando execução após reset para valor inicial.")
            break

def monitor_trade(trade_id, asset):
    global simultaneous_trades
    global session_profit
    global consecutive_losses
    global current_amount
    global saldo_saida
    global amount_doubled

    try:
        print(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        log_message(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        result = None
        while result is None:
            try:
                result = iq.check_win_v4(trade_id)
                if result is None:
                    print(f"Negociação {trade_id} ainda não concluída. Tentando novamente em 1 segundo...")
                    log_message(f"Negociação {trade_id} ainda não concluída. Tentando novamente em 1 segundo...")
                    time.sleep(1)
            except Exception as e:
                print(f"Erro ao verificar status da negociação {trade_id}: {e}")
                log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")
                time.sleep(1)

        if isinstance(result, tuple):
            result = result[0]  # Assuming the first element of the tuple is the profit/loss value
        if isinstance(result, str):
            if result.lower() == "win":
                result = 1.0
            elif result.lower() == "loose":
                result = -1.0
            else:
                try:
                    result = float(result)  # Convert string to float
                except ValueError:
                    print(f"Erro ao converter resultado para float: {result}")
                    log_message(f"Erro ao converter resultado para float: {result}")
                    result = 0.0  # Default to 0.0 if conversion fails

        session_profit += result
        saldo_saida = iq.get_balance()  # Store balance after trade

        print(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")
        log_message(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")

        update_session_profit()

        if result <= 0:
            consecutive_losses += 1
            if consecutive_losses > 3:  # Reset to initial amount after 3 consecutive losses
                log_message("Número de perdas consecutivas excedido. Resetando valor inicial.")
                consecutive_losses = 0
                set_amount()  # Reset to initial amount
                amount_doubled = False
            else:
                log_message(f"Perda consecutiva #{consecutive_losses}.")
                if not amount_doubled:  # Ensure the amount is only doubled once per loss
                    current_amount *= 2  # Correctly double the amount
                    amount_doubled = True  # Set the flag to indicate the amount has been doubled
                    log_message(f"Dobrar valor da negociação. Próximo valor de negociação: R${current_amount}")
                    update_martingale_label()  # Update Martingale label
        else:
            consecutive_losses = 0
            set_amount()  # Reset to initial amount after a win
            amount_doubled = False  # Reset the flag
            print("Negociação Bem Sucedida, Restaurando Indicadores")
            log_message(f"Negociação bem-sucedida. Valor de negociação resetado para: R${current_amount}")
            update_martingale_label()  # Update Martingale label

    finally:
        simultaneous_trades -= 1
        if trade_id in trade_list:
            trade_list.remove(trade_id)  # Ensure the trade is removed from the list after checking
        print(f"Balance after closing trade: {iq.get_balance()}")  # Display balance after closing trade

def check_trade_results():
    global trade_list
    global session_profit
    global consecutive_losses
    global current_amount
    global amount_doubled
    
    for trade_id in trade_list.copy():
        try:
            result = iq.check_win_v4(trade_id)
            if result is not None:
                if isinstance(result, tuple):
                    result = result[0]  # Assuming the first element of the tuple is the profit/loss value
                if isinstance(result, str):
                    if result.lower() == "win":
                        result = 1.0
                        train_model_with_collected_data()
                    elif result.lower() == "loose":
                        result = -1.0
                        train_model_with_collected_data()
                    else:
                        try:
                            result = float(result)  # Convert string to float
                        except ValueError:
                            print(f"Erro ao converter resultado para float: {result}")
                            log_message(f"Erro ao converter resultado para float: {result}")
                            result = 0.0  # Default to 0.0 if conversion fails

                session_profit += result
                log_message(f"Resultado da negociação {trade_id}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")

                if result <= 0:
                    consecutive_losses += 1
                    if not amount_doubled:  # Ensure the amount is only doubled once per loss
                        current_amount *= 2  # Correctly double the amount
                        amount_doubled = True  # Set the flag to indicate the amount has been doubled
                        log_message(f"Dobrar valor da negociação. Próximo valor de negociação: R${current_amount}")
                        update_martingale_label()  # Update Martingale label
                else:
                    consecutive_losses = 0
                    set_amount()  # Reset to initial amount after a win
                    amount_doubled = False  # Reset the flag
                    log_message(f"Negociação bem-sucedida. Valor de negociação resetado para: R${current_amount}")
                    update_martingale_label()  # Update Martingale label

                trade_list.remove(trade_id)  # Ensure the trade is removed from the list after checking
        except Exception as e:
            print(f"Erro ao verificar status da negociação {trade_id}: {e}")
            log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")

def update_session_profit():
    global saldo_entrada, saldo_saida, session_profit
    total_profit = saldo_saida - saldo_entrada  # Calculate total profit based on balance difference
    profit_label.config(text=f"Lucro: R${total_profit:.2f}", fg="green" if total_profit >= 0 else "red")

# Função para iniciar a execução de trades
def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=execute_trades).start()

# Função para parar a execução de trades
def stop_trading():
    global running
    global smart_stop
    smart_stop = True
    running = False
    if 'static_icon' in globals():
        icon_label.config(image=static_icon)
    log_message("Smart Stop ativado. Parando execução após reset para valor inicial.")

def update_log():
    try:
        with open(log_file, "r") as file:
            lines = file.readlines()
            log_text.delete(1.0, tk.END)
            log_text.insert(tk.END, "".join(lines[-10:]))
    except FileNotFoundError:
        log_text.delete(1.0, tk.END)
        log_text.insert(tk.END, "Log file not found. Waiting for new entries...\n")
    if running:
        root.after(1000, update_log)

# Update the set_amount function to use 5% of the account balance
def set_amount():
    global initial_amount
    global current_amount
    balance = iq.get_balance()
    initial_amount = balance * 0.02  # Set to 2% of the balance
    current_amount = initial_amount
    log_message(f"Initial amount set to 2% of balance: R${initial_amount:.2f}")
    balance_label.config(text=f"Balance: R${balance:.2f}")
    update_martingale_label()  # Update Martingale label

# Function to update the Martingale label
def update_martingale_label():
    if current_amount > initial_amount:
        martingale_label.config(text="M", fg="red")
    else:
        martingale_label.config(text="M", fg="#000000")  # Same color as the background

# Function to stop and start trading if the code freezes for more than 15 seconds
def watchdog():
    global running
    last_check = time.time()
    
    while True:
        time.sleep(5)
        if running and (time.time() - last_check > 15):
            log_message("Detected freeze. Restarting trading session...")
            stop_trading()
            time.sleep(1)
            start_trading()
        last_check = time.time()

# Start the watchdog thread
threading.Thread(target=watchdog, daemon=True).start()

# GUI Configuration
root = tk.Tk()
root.title(f"Capybara v7.7 - Conta: {account_type} - {email}")
root.configure(bg="#000000")

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#000000")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

stop_button = tk.Button(root, text="Smart Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=1, padx=5, pady=5)

balance_label = tk.Label(root, text="Balance: R$0.00", bg="#000000", fg="white", font=("Helvetica", 12))
balance_label.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

# Add Martingale label
martingale_label = tk.Label(root, text="M", bg="#000000", fg="#000000", font=("Helvetica", 12))
martingale_label.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#000000", fg="white")
log_text.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Redirect stdout and stderr to the log_text widget
sys.stdout = TextRedirector(log_text, "stdout")
sys.stderr = TextRedirector(log_text, "stderr")

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#000000", fg="white")
profit_label.grid(row=4, column=0, columnspan=5, padx=10, pady=10)

footer_label = tk.Label(
    root,
     text="@oedlopes - 2025  - Deus Seja Louvado - Sola Scriptura - Sola Fide - Solus Christus - Sola Gratia - Soli Deo Gloria",
    bg="#000000",
    fg="#A9A9A9",
    font=("Helvetica", 7)
)
footer_label.grid(row=5, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")
#À∴G∴D∴G∴A∴D∴U∴
update_log()
update_session_profit()

# Start trading automatically
start_trading()

root.mainloop()

def update_open_trades_label():
    if running:
        root.after(1000, update_open_trades_label)

# Start updating the open trades label
update_open_trades_label()

# Ensure balance is fetched and initial amount is set at the start
connect_to_iq_option(email, password)
set_amount()

# Update balance label on initialization
balance_label.config(text=f"Balance: R${iq.get_balance():.2f}")

def simulate_trade(success):
    global current_amount, consecutive_losses, amount_doubled

    if success:
        log_message(f"Trade successful. Amount: ${current_amount}")
        consecutive_losses = 0
        current_amount = initial_amount
        amount_doubled = False
    else:
        log_message(f"Trade failed. Amount: ${current_amount}")
        consecutive_losses += 1
        if consecutive_losses <= martingale_limit and not amount_doubled:
            current_amount *= 2  # Correctly double the amount
            amount_doubled = True
        else:
            log_message("Martingale limit reached or amount already doubled. Resetting to initial amount.")
            consecutive_losses = 0
            current_amount = initial_amount
            amount_doubled = False

# Teste da lógica de Martingale
def test_martingale_logic():
    global current_amount, consecutive_losses, amount_doubled

    # Resetar variáveis
    current_amount = initial_amount
    consecutive_losses = 0
    amount_doubled = False

    # Simular uma série de negociações
    simulate_trade(False)  # Falha
    assert current_amount == initial_amount * 2, f"Expected {initial_amount * 2}, got {current_amount}"
    assert amount_doubled == True, "Expected amount_doubled to be True"

    simulate_trade(False)  # Falha
    assert current_amount == initial_amount * 4, f"Expected {initial_amount * 4}, got {current_amount}"
    assert amount_doubled == True, "Expected amount_doubled to be True"

    simulate_trade(True)  # Sucesso
    assert current_amount == initial_amount, f"Expected {initial_amount}, got {current_amount}"
    assert amount_doubled == False, "Expected amount_doubled to be False"

    simulate_trade(False)  # Falha
    assert current_amount == initial_amount * 2, f"Expected {initial_amount * 2}, got {current_amount}"
    assert amount_doubled == True, "Expected amount_doubled to be True"

    simulate_trade(False)  # Falha
    assert current_amount == initial_amount * 4, f"Expected {initial_amount * 4}, got {current_amount}"
    assert amount_doubled == True, "Expected amount_doubled to be True"

    simulate_trade(False)  # Falha
    assert current_amount == initial_amount * 8, f"Expected {initial_amount * 8}, got {current_amount}"
    assert amount_doubled == True, "Expected amount_doubled to be True"

    simulate_trade(False)  # Falha
    assert current_amount == initial_amount * 16, f"Expected {initial_amount * 16}, got {current_amount}"
    assert amount_doubled == True, "Expected amount_doubled to be True"

    simulate_trade(False)  # Falha
    assert current_amount == initial_amount, f"Expected {initial_amount}, got {current_amount}"
    assert amount_doubled == False, "Expected amount_doubled to be False"

    log_message("Martingale logic test completed successfully.")

# Executar o teste
test_martingale_logic()

# Configuração da GUI
root = tk.Tk()
root.title("Capybara v7.7")
root.configure(bg="#000000")


static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#000000")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

start_button = tk.Button(root, text="Start", command=start_trading, bg="#4CAF50", fg="white", font=("Helvetica", 12))
start_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=2, padx=5, pady=5)

amount_label = tk.Label(root, text="Initial Amount:", bg="#000000", fg="white", font=("Helvetica", 12))
amount_label.grid(row=1, column=1, padx=5, pady=5)

amount_entry = tk.Entry(root, font=("Helvetica", 12))
amount_entry.insert(0, "2")
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#000000", fg="white")
log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#000000", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Rodapé
footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - Deus seja louvado",
    bg="#000000",
    fg="#A9A9A9",
    font=("Helvetica", 8)
)
footer_label.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")

update_log()

invalid_credentials = False

if invalid_credentials:
    log_text.insert(tk.END, "Invalid credentials. Please check the credentials.txt file.\n")

root.mainloop()

def calculate_success_probability(asset, direction):
    """
    Calculate the probability of success based on technical indicators.
    """
    data = fetch_historical_data(asset, 1, 100)  # Fetch last 100 candles of 1 minute each

    if data is None or data.empty:
        log_message(f"Sem dados suficientes para {asset}. Pulando ativo.")
        return 0.0

    # Ensure all columns are cast to compatible dtypes
    data["close"] = data["close"].astype(float)
    data["open"] = data["open"].astype(float)
    data["high"] = data["high"].astype(float)
    data["low"] = data["low"].astype(float)
    if "volume" in data.columns:
        data["volume"] = data["volume"].astype(float)

    # Calculate technical indicators
    volume = data["volume"].iloc[-1]
    candle_strength = (data["close"].iloc[-1] - data["open"].iloc[-1]) / (data["high"].iloc[-1] - data["low"].iloc[-1])
    speed = (data["close"].iloc[-1] - data["close"].iloc[-2]) / data["close"].iloc[-2]
    popularity = volume / data["volume"].mean()

    # Combine indicators to calculate probability
    probability = 0.25 * volume + 0.25 * candle_strength + 0.25 * speed + 0.25 * popularity

    log_message(f"Probabilidade calculada para {asset}: {probability:.2f}")
    return probability

def should_open_trade(opening_price, closing_price, min_difference):
    """
    Determine if a trade should be opened based on the price difference.
    """
    price_difference = abs(opening_price - closing_price)
    if price_difference < min_difference:
        log_message(f"Preço de abertura: {opening_price}, Preço de fechamento: {closing_price}, Diferença: {price_difference}")
        return False
    return True

def save_console_output():
    current_date = time.strftime("%Y-%m-%d")
    log_filename = f"console_output_{current_date}.txt"
    log_filepath = os.path.join(os.getcwd(), log_filename)
    
    with open(log_filepath, "w") as file:
        file.write(log_text.get(1.0, tk.END))

# Schedule the save_console_output function to run every day at midnight
def schedule_daily_save():
    now = time.localtime()
    midnight = time.mktime((now.tm_year, now.tm_mon, now.tm_mday + 1, 0, 0, 0, 0, 0, 0))
    delay = midnight - time.mktime(now)
    threading.Timer(delay, save_console_output).start()

# Call the schedule_daily_save function to start the daily saving process
schedule_daily_save()

def update_balance():
    if iq is not None:
        balance = iq.get_balance()
        balance_label.config(text=f"Balance: R${balance:.2f}")
        log_message(f"Balance updated: R${balance:.2f}")
    root.after(60000, update_balance)  # Schedule the function to run every minute

# Ensure balance is fetched and initial amount is set at the start
connect_to_iq_option(email, password)
set_amount()
update_balance()  # Start the periodic balance update








































