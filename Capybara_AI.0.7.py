#!/usr/bin/env python
# Arquivo: Capybara_AI.0.7.py
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
import joblib
import numpy as np
from sklearn.neural_network import MLPClassifier
from model_management import load_model, save_model

# Carregar o modelo de machine learning
model_path = os.path.normpath(os.path.join(os.getcwd(), "IA/capybara-ai-project/models/trained_model.pkl"))
model = joblib.load(model_path)

def get_data_for_model(asset):
    # Coletar dados reais de volatilidade, indicadores e candles
    data = fetch_historical_data(asset, 1, 60)  # Fetch last 60 candles of 1 minute each
    if data.empty:
        raise ValueError(f"No data returned for asset {asset}")
    
    # Garantir que todas as funções retornem arrays NumPy
    try:
        volatility = np.array(calculate_volatility(data)).reshape(1, -1)  # Função que retorna os dados de volatilidade
    except Exception as e:
        log_message(f"Erro ao calcular volatilidade para o ativo {asset}: {e}")
        raise

    try:
        indicators = calculate_indicators(data)
        log_message(f"Indicadores calculados para o ativo {asset}: {indicators}")
        indicators = np.array([float(value) for value in indicators.values()]).reshape(1, -1)  # Função que retorna os dados de indicadores
    except Exception as e:
        log_message(f"Erro ao calcular indicadores para o ativo {asset}: {e}")
        raise

    try:
        candles = np.array(fetch_candles(asset, 60, 60)).reshape(1, -1)  # Função que retorna os dados de candles
    except Exception as e:
        log_message(f"Erro ao buscar candles para o ativo {asset}: {e}")
        raise
    
    # Combine os dados em um único array
    try:
        combined_data = np.concatenate((volatility, indicators, candles), axis=1)
    except Exception as e:
        log_message(f"Erro ao combinar dados para o ativo {asset}: {e}")
        raise
    
    # Verifique o tamanho dos dados e ajuste se necessário
    expected_features = 82
    if combined_data.shape[1] != expected_features:
        log_message(f"Warning: Expected {expected_features} features, but got {combined_data.shape[1]}")
    
    return combined_data

def make_decision(asset):
    try:
        data = get_data_for_model(asset)
        decision = model.predict(data)
        return decision[0]  # Assuming the model returns an array, get the first element
    except Exception as e:
        log_message(f"Erro ao tomar decisão para o ativo {asset}: {e}")
        raise

def save_model():
    joblib.dump(model, model_path)
    log_message("Model saved successfully.")



def fetch_candles(asset, interval, count):
    """Obtém os candles do ativo na IQ Option API, garantindo que a conexão esteja ativa."""
    global iq
    if iq is None or not iq.check_connect():
        log_message("API desconectada. Tentando reconectar...")
        connect_to_iq_option(email, password)

        if iq is None or not iq.check_connect():
            log_message("Falha na reconexão. Não foi possível buscar candles.")
            return []

    try:
        candles = iq.get_candles(asset, interval, count, time.time())
        return [candle['close'] for candle in candles]
    except Exception as e:
        log_message(f"Erro ao buscar candles para {asset}: {e}")
        return []



def fetch_additional_data(asset, timestamp):
    """Obtém dados adicionais, como indicadores técnicos e volatilidade."""
    candles = fetch_candles(asset, 60, 60)  # Obtém os últimos 60 candles de 1 minuto
    if not candles:
        return None

    close_prices = [candle['close'] for candle in candles]
    high_prices = [candle['max'] for candle in candles]
    low_prices = [candle['min'] for candle in candles]
    volume = [candle['volume'] for candle in candles]

    indicators = {
        'rsi': pyti_rsi(close_prices, period=14)[-1],
        'macd': pyti_macd(close_prices, short_period=12, long_period=26, signal_period=9)[-1],
        'sma': pyti_sma(close_prices, period=14)[-1],
        'ema': pyti_ema(close_prices, period=14)[-1],
        'bollinger': pyti_bollinger(close_prices, period=20)[-1],
        'atr': pyti_atr(high_prices, low_prices, close_prices, period=14)[-1],
        'stochastic': pyti_stochastic(close_prices, high_prices, low_prices, period=14)[-1],
        'willr': pyti_willr(close_prices, high_prices, low_prices, period=14)[-1],
        'cci': pyti_cci(close_prices, high_prices, low_prices, period=14)[-1],
        'roc': pyti_roc(close_prices, period=14)[-1],
        'obv': pyti_obv(close_prices, volume)[-1],
        'mfi': pyti_mfi(close_prices, high_prices, low_prices, volume, period=14)[-1],
        'dpo': pyti_dpo(close_prices, period=14)[-1],
        'ultimate': pyti_ultimate(close_prices, high_prices, low_prices, period1=7, period2=14, period3=28)[-1],
        'aroon_up': pyti_aroon_up(close_prices, period=14)[-1],
        'aroon_down': pyti_aroon_down(close_prices, period=14)[-1]
    }

    volatility = calculate_volatility(close_prices)

    return {
        'indicators': indicators,
        'volatility': volatility
    }


def set_amount(amount=None):
    """Define o valor da negociação como 2% do saldo ou um valor especificado."""
    global initial_amount, current_amount, iq
    if amount is not None:
        current_amount = amount
    else:
        if iq is None or not iq.check_connect():
            log_message("API desconectada. Não foi possível definir o valor da negociação.")
            return
        balance = iq.get_balance()
        initial_amount = balance * 0.02  # Define 2% do saldo
        current_amount = initial_amount
        log_message(f"Valor inicial definido: R${initial_amount:.2f}")

def calculate_volatility(data):
    # Exemplo de cálculo de volatilidade
    return [np.std(data['close'])]


def on_trade_open(asset, timestamp):
    """Obtém os candles e dados adicionais quando uma negociação é aberta."""
    candles = fetch_candles(asset, 60, 60)  # Agora fornecendo todos os argumentos necessários
    additional_data = fetch_additional_data(asset, timestamp)
    
    return {
        'candles': candles,
        'additional_data': additional_data
    }

def on_trade_open(asset, timestamp):
    """Obtém os candles e dados adicionais ao abrir uma negociação."""
    candles = fetch_candles(asset, 60, 60)  # Agora fornecendo todos os argumentos necessários
    additional_data = fetch_additional_data(asset, timestamp)

    if additional_data is None:
        log_message(f"Erro ao obter dados adicionais para {asset}. Retornando apenas candles.")
        return {'candles': candles}  # Retorna apenas candles se os dados adicionais falharem

    return {
        'candles': candles,
        'volatility': additional_data.get('volatility', None),
        'indicators': additional_data.get('indicators', {})
    }



def store_data(data):
    # Store the data in a file or database for training the AI model
    with open('trading_data.json', 'a') as f:
        json.dump(data, f)
        f.write('\n')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.insert(tk.END, str, (self.tag,))
        self.widget.see(tk.END)

    def flush(self):
        pass

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
    log_message(f"Ativo adicionado à lista de ignorados: {asset}")

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
asset = "AssetName"  # Nome do ativo para negociação
# Define preset trade value
auto_initial_amount = 2
smart_stop = False

def print_account_balance():
    balance = iq.get_balance()
    account_type_str = "PRACTICE" if account_type == "REAL" else "DEMO"
    log_message(f"Saldo: R${balance:.2f} - Conta {account_type_str}")

# Conectar à API IQ Option
def connect_to_iq_option(email, password):
    """Conecta à API IQ Option e configura a conta."""
    global iq
    log_message("Tentando conectar à API IQ Option...")
    iq = IQ_Option(email, password)
    
    try:
        check, reason = iq.connect()
        if check:
            iq.change_balance(account_type)  # Alternar entre 'PRACTICE' e 'REAL'
            log_message("Conexão bem-sucedida com a API IQ Option.")
            set_amount()  # Definir o valor inicial da negociação
        else:
            log_message(f"Falha ao conectar à API IQ Option: {reason}")
            iq = None  # Garante que iq seja None se a conexão falhar
    except Exception as e:
        log_message(f"Erro inesperado durante a conexão: {e}")
        iq = None
    return check if 'check' in locals() else False, reason if 'reason' in locals() else "Erro desconhecido"


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

def fetch_historical_data(asset, interval, count):
    # Implementar a lógica para buscar dados históricos
    # Certifique-se de que o DataFrame retornado contenha a coluna 'close'
    candles = iq.get_candles(asset, interval, count, time.time())
    if not candles:
        raise ValueError(f"No data returned for asset {asset}")

    # Convert the list of candles to a DataFrame
    df = pd.DataFrame(candles)
    if 'close' not in df.columns:
        raise KeyError(f"'close' column not found in data for asset {asset}")
    df["close"] = df["close"].astype(float)
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

volatility = on_trade_open(asset, int(time.time()))['volatility']
if volatility is not None:
    indicators = {'volatility': volatility}
    
    try:
        decision = model.predict(indicators)
        
        if decision == 1:  # Assuming the model predicts buy
            log_message(f"Trade decided to buy based on {indicators}")
        elif decision == 0:  # Assuming the model predicts sell
            log_message(f"Trade decided to sell based on {indicators}")
    except Exception as e:
        log_message(f"Error making decision: {e}")


class CustomIndicator:
    def __init__(self, instrument, last_data, parameters):
        self.instrument = instrument
        self.last = last_data.copy()
        self.parameters = parameters
        self.last_data = last_data

    def is_enabled(self):
        try:
            candles = fetch_historical_data(self.instrument, 1, 60)
            if candles is not None and not candles.empty:
                return True
        except Exception as e:
            log_message(f"Error fetching data for {self.instrument}: {e}")
            return False
        return False

    def calculate_volatility(self, data):
        # Implemente seu cálculo de volatilidade aqui
        return 0.0  # Valor de retorno de exemplo

    def on_trade_open(self, timestamp):
        try:
            data = fetch_historical_data(self.instrument, 1, 60)  # Fetch últimos 60 candles de 1 minuto cada
            if data is not None and not data.empty:
                volatility = self.calculate_volatility(data)
                return {'volatility': volatility}
            else:
                log_message(f"Error fetching historical data for {self.instrument}")
                return None
        except Exception as e:
            log_message(f"Error processing trade open: {e}")
            return None

    def on_trade_close(self, trade_result, trade_value, timestamp):
        try:
            data = fetch_historical_data(self.instrument, 1, 60)  # Fetch últimos 60 candles de 1 minuto cada
            if data is not None and not data.empty:
                volatility = self.calculate_volatility(data)
                return {'volatility': volatility}
            else:
                log_message(f"Error fetching historical data for {self.instrument}")
                return None
        except Exception as e:
            log_message(f"Error processing trade close: {e}")
            return None

    def make_decision(self, indicators):
        try:
            decision = model.predict(indicators)
            return decision
        except Exception as e:
            log_message(f"Error making decision: {e}")
            return None

# # Exemplo de uso:
# instrument = "EURUSD"
# current_data = {
#     'last': data,
#     'parameters': None
# }
# indicator = CustomIndicator(instrument, current_data, {'last': data, 'parameters': None})

# if indicator.is_enabled():
#     decision = indicator.make_decision({'volatility': indicator.on_trade_open(int(time.time()))['volatility']})
#     if decision == 1:  # Supondo que 1 significa comprar
#         log_message(f"Decision: Buy {instrument}")
#         # Execute a lógica de compra aqui
#     elif decision == 0:  # Supondo que 0 significa vender
#         log_message(f"Decision: Sell {instrument}")
#         # Execute a lógica de venda aqui

#     # Execute a lógica de fechamento de negociação aqui
#     indicator.on_trade_close(trade_result, trade_value, int(time.time()))

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

# Carregar o modelo treinado
model = joblib.load('IA/capybara-ai-project/models/trained_model.pkl')
model_file = 'IA/capybara-ai-project/models/trained_model.pkl'
if model is None:
    model = MLPClassifier()
    print(f"Novo modelo criado, pois {model_file} não foi encontrado")

# Variável global para armazenar as classes
global_classes = np.array([0, 1])

# Verificar se o modelo já foi treinado anteriormente
if hasattr(model, 'classes_'):
    global_classes = model.classes_


def collect_data(asset):
    """Collect data for the last 60 minutes."""
    data = fetch_historical_data(asset, 1, 60)
    print(f"Dados coletados para o ativo {asset}: {data}")
    return data
import ta
def calculate_indicators(data):
    # Exemplo de cálculo de indicadores
    try:
        # Check if required columns are present
        required_columns = ["high", "low", "close", "volume"]
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")

        # Check for NaN or null values
        if data[required_columns].isnull().values.any():
            raise ValueError("Input data contains NaN or null values")

        indicators = {
            "rsi": ta.momentum.RSIIndicator(data["close"], window=14).rsi().iloc[-1],
            "macd": ta.trend.MACD(data["close"]).macd().iloc[-1],
            "ema": ta.trend.EMAIndicator(data["close"], window=9).ema_indicator().iloc[-1],
            "sma": ta.trend.SMAIndicator(data["close"], window=20).sma_indicator().iloc[-1],
            "stochastic": ta.momentum.StochasticOscillator(data["high"], data["low"], data["close"]).stoch().iloc[-1],
            "atr": ta.volatility.AverageTrueRange(data["high"], data["low"], data["close"], window=14).average_true_range().iloc[-1],
            "adx": ta.trend.ADXIndicator(data["high"], data["low"], data["close"], window=14).adx().iloc[-1],
            "bollinger_high": ta.volatility.BollingerBands(data["close"]).bollinger_hband().iloc[-1],
            "bollinger_low": ta.volatility.BollingerBands(data["close"]).bollinger_lband().iloc[-1],
            "cci": ta.trend.CCIIndicator(data["high"], data["low"], data["close"], window=20).cci().iloc[-1],
            "willr": ta.momentum.WilliamsRIndicator(data["high"], data["low"], data["close"], lbp=14).williams_r().iloc[-1],
            "roc": ta.momentum.ROCIndicator(data["close"], window=12).roc().iloc[-1],
            "obv": ta.volume.OnBalanceVolumeIndicator(data["close"], data["volume"]).on_balance_volume().iloc[-1],
            "trix": ta.trend.TRIXIndicator(data["close"], window=15).trix().iloc[-1],
            "mfi": ta.volume.MFIIndicator(data["high"], data["low"], data["close"], data["volume"], window=14).money_flow_index().iloc[-1],
            "dpo": ta.trend.DPOIndicator(data["close"], window=14).dpo().iloc[-1],
            "keltner_upper": ta.volatility.KeltnerChannel(data["high"], data["low"], data["close"]).keltner_channel_hband().iloc[-1],
            "keltner_lower": ta.volatility.KeltnerChannel(data["high"], data["low"], data["close"]).keltner_channel_lband().iloc[-1],
            "ultimate_oscillator": ta.momentum.UltimateOscillator(data["high"], data["low"], data["close"]).ultimate_oscillator().iloc[-1],
            "tsi": ta.momentum.TSIIndicator(data["close"]).tsi().iloc[-1],
            "aroon_up": ta.trend.AroonIndicator(data["close"]).aroon_up().iloc[-1],
            "aroon_down": ta.trend.AroonIndicator(data["close"]).aroon_down().iloc[-1]
        }
        return indicators
    except Exception as e:
        log_message(f"Erro ao calcular indicadores: {e}")
        log_message(f"Input data:\n{data}")
        raise

def update_model(model, X, y):
    """Update the model with new data."""
    global global_classes
    log_message(f"Atualizando o modelo com X={X} e y={y}")
    model.partial_fit(X, y, classes=global_classes)
    joblib.dump(model, model_file)
    log_message(f"Modelo salvo em {model_file}")
    print(f"Modelo atualizado com X={X} e y={y}")
    save_model(model, model_file)

def execute_trade(decision, asset, indicators):
    global current_amount
    global simultaneous_trades
    global saldo_entrada

    if decision == "buy":
        action = "call"
        log_message("Executing BUY trade...")
    elif decision == "sell":
        action = "put"
        log_message("Executing SELL trade...")
    else:
        log_message(f"Pulando negociação para {asset}. Sem consenso ou tendência contrária.")
        return

    log_message(f"Tentando realizar negociação: Ativo={asset}, Ação={action}, Valor = R${current_amount}")
    saldo_entrada = iq.get_balance()  # Store balance before trade
    print(f"Balance before opening trade: {saldo_entrada}")  # Display balance before trade

    # Verificar a disponibilidade do ativo antes de tentar negociar
    available_assets = iq.get_all_ACTIVES_OPCODE()
    if asset not in available_assets:
        log_message(f"Ativo {asset} não encontrado na plataforma. Pulando ativo.")
        return

    try:
        success, trade_id = iq.buy(current_amount, asset, action, 5)  # Negociações de 5 minutos
        if success:
            simultaneous_trades += 1
            add_trade_to_list(trade_id)
            log_message(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
            print(f"Balance after opening trade: {iq.get_balance()}")  # Display balance after opening trade
            threading.Thread(target=monitor_trade, args=(trade_id, asset, indicators)).start()
        else:
            log_message(f"Falha ao realizar negociação para {asset}. Motivo: {trade_id}")  # Log the reason for failure
    except Exception as e:
        log_message(f"Erro durante a execução da negociação para {asset}: {e}")
        if "WinError 10054" in str(e):
            log_message("Conexão perdida. Tentando reconectar...")
            reconnect_if_needed()
            return

# Carregar o modelo de machine learning
model = joblib.load('IA/capybara-ai-project/models/trained_model.pkl')

def execute_trades():
    global running
    global current_amount
    global consecutive_losses
    global session_profit
    global simultaneous_trades
    global saldo_entrada

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

            try:
                decision = make_decision(asset)
                if decision == 1:  # Assuming 1 means buy
                    log_message(f"Decision: Buy {asset}")
                    # Execute buy logic here
                elif decision == 0:  # Assuming 0 means sell
                    log_message(f"Decision: Sell {asset}")
                    # Execute sell logic here

                save_model()  # Save the model after each decision
            except Exception as e:
                log_message(f"Erro ao processar o ativo {asset}: {e}")

    # Implementação da função monitor_trade
                
def monitor_trade(trade_id, asset, indicators):
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

        print(f"Resultado bruto da negociação {trade_id}: {result}")

        # Adicione um print detalhado para inspecionar a estrutura da tupla
        if isinstance(result, tuple):
            print(f"Estrutura da tupla de resultados: {result}")
            for i, value in enumerate(result):
                print(f"Elemento {i}: {value}")

            result = result[0]  # Assuming the first element of the tuple is the profit/loss value
            print(f"Primeiro elemento da tupla result: {result}")
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

        # Coletar dados dos últimos 60 minutos
        data = collect_data(asset)
        
        # Calcular indicadores
        indicators = calculate_indicators(data)

        # Atualizar o modelo com o resultado da negociação
        y = [1 if result > 0 else 0]
        X = np.array(list(indicators.values())).reshape(1, -1)
        log_message(f"Dados para atualização do modelo: X={X}, y={y}")
        update_model(model, X, y)

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
                log_message(f"Resultado da negociação {trade_id}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")
                # Coletar dados dos últimos 60 minutos
                asset = iq.get_asset_by_id(trade_id)  # Get the asset for this trade
                data = collect_data(asset)
                
                # Calcular indicadores
                indicators = calculate_indicators(data)
                
                # Atualizar o modelo com o resultado da negociação
                y = [1 if result > 0 else 0]
                X = np.array(list(indicators.values())).reshape(1, -1)
                log_message(f"Dados para atualização do modelo: X={X}, y={y}")
                update_model(model, X, y)

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



# Function to update the Martingale label
def update_martingale_label():
    if current_amount > initial_amount:
        martingale_label.config(text="M", fg="red")
    else:
        martingale_label.config(text="M", fg="#000000")  # Same color as the background

# Carregar o modelo de machine learning
model = joblib.load('IA/capybara-ai-project/models/trained_model.pkl')

def update_model_with_results(results):
    # Função para retroalimentar o modelo com os dados de resultado
    # Substitua isso com a lógica para atualizar o modelo
    pass


# Modificar a função watchdog para incluir a lógica de decisão e negociação
def watchdog():
    while True:
        try:
            assets = fetch_sorted_assets()
            for asset in assets:
                try:
                    decision = make_decision(asset)
                    # Process the decision
                except Exception as e:
                    log_message(f"Erro ao processar o ativo {asset}: {e}")
        except Exception as e:
            log_message(f"Erro no watchdog: {e}")
            break


# Start the watchdog thread
threading.Thread(target=watchdog, daemon=True).start()

# GUI Configuration
root = tk.Tk()
root.title(f"Capybara AI v0.7 - Conta: {account_type} - {email}")
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

root.mainloop()

