#!/usr/bin/env python
# Arquivo: Capybara.7.9.py
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
import numpy as np
import json
import logging
import warnings
from sklearn.ensemble import RandomForestClassifier
import joblib
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

# Caminhos dos arquivos
csv_path = "trading_data.csv"
model_path = "trading_model.pkl"


def check_file_accessibility():
    """Verifica se os arquivos necessários (.csv e .pkl) estão acessíveis."""
    if not os.path.exists(csv_path):
        print(f"Arquivo CSV não encontrado. Criando {csv_path}...")
        recreate_csv()
    elif os.stat(csv_path).st_size == 0:
        print(f"Arquivo CSV {csv_path} está vazio. Criando estrutura padrão...")
        recreate_csv()
    
    if not os.path.exists(model_path):
        print(f"Arquivo do modelo {model_path} não encontrado. Um novo será treinado quando necessário.")
    else:
        try:
            model = joblib.load(model_path)
            if not isinstance(model, RandomForestClassifier):
                raise ValueError("O arquivo carregado não é um modelo válido.")
            print("Modelo carregado com sucesso!")
        except Exception as e:
            print(f"Erro ao carregar o modelo {model_path}: {e}. Um novo modelo será treinado quando necessário.")

# Função para validar o arquivo CSV antes do treinamento
def validate_csv():
    if not os.path.exists(csv_path) or os.stat(csv_path).st_size == 0:
        print("Erro: O arquivo de dados está ausente ou vazio.")
        return False

    try:
        df = pd.read_csv(csv_path)
        if df.empty or 'target' not in df.columns or df.shape[1] < 2:
            print("Erro: O arquivo CSV não contém a estrutura esperada.")
            return False
    except Exception as e:
        print(f"Erro ao ler o CSV: {e}")
        return False

    return True

# Função para capturar candles
def fetch_candles(asset, period=1, count=60):
    """Obtém os últimos 60 candles de 1 minuto para o ativo especificado."""
    try:
        candles = iq.get_candles(asset, 60, 60, time.time())  # 60 segundos x 60 candles
        if not candles:
            print(f"Erro: Nenhum dado de candle recebido para {asset}.")
            return None
        df = pd.DataFrame(candles)
        expected_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in expected_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Aviso: Colunas ausentes nos dados de {asset}: {missing_columns}")
            for col in missing_columns:
                df[col] = df['close'] if 'close' in df.columns else 0  # Preenche com fechamento ou zero
        
        return df[expected_columns].values.flatten()
    except Exception as e:
        print(f"Erro ao buscar candles para {asset}: {e}")
        return None

def recreate_csv():
    """Cria um novo arquivo CSV com a estrutura correta caso não exista ou esteja corrompido."""
    column_names = [f"feature_{i}" for i in range(300)] + ["target"]
    pd.DataFrame(columns=column_names).to_csv(csv_path, index=False)
    print("Novo arquivo CSV criado com estrutura correta.")


def train_and_save_model():
    """Treina o modelo e salva no arquivo .pkl."""
    if not validate_csv():
        print("Erro: CSV inválido, modelo não pode ser treinado.")
        return False
    try:
        df = pd.read_csv(csv_path)
        X = df.drop(columns=['target']).values
        y = df['target'].astype(int).values
        
        if len(y) < 10:
            print("Dados insuficientes para treinamento. Aguardando mais negociações vencedoras.")
            return False
        
        model = RandomForestClassifier(n_estimators=200, random_state=42, max_depth=10, min_samples_split=5)
        model.fit(X, y)
        joblib.dump(model, model_path)
        print("Modelo treinado e salvo com sucesso! Acessando .pkl para verificação...")
        if os.path.exists(model_path):
            print(f"Arquivo {model_path} atualizado com sucesso!")
        else:
            print(f"Erro: {model_path} não foi encontrado após o treinamento!")
        return True
    except Exception as e:
        print(f"Erro ao treinar o modelo: {e}")
        return False
    
# Função para carregar o modelo salvo
def load_model():
    """Carrega um modelo salvo ou treina um novo se não existir."""
    if not os.path.exists(model_path):
        print("Modelo não encontrado. Treinando um novo...")
        if train_and_save_model():
            return joblib.load(model_path)
        else:
            return None
    try:
        model = joblib.load(model_path)
        if not isinstance(model, RandomForestClassifier):
            raise ValueError("O arquivo carregado não é um modelo válido.")
        print("Modelo carregado com sucesso!")
        return model
    except Exception as e:
        print(f"Erro ao carregar o modelo: {e}")
        return None


def validate_csv():
    """Verifica se o arquivo CSV existe e está formatado corretamente."""
    if not os.path.exists(csv_path) or os.stat(csv_path).st_size == 0:
        print("Arquivo de dados ausente ou vazio. Criando...")
        recreate_csv()
        return False
    try:
        df = pd.read_csv(csv_path)
        if df.empty or 'target' not in df.columns or df.shape[1] < 2:
            print("Arquivo CSV inválido. Recriando...")
            recreate_csv()
            return False
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}. Recriando...")
        recreate_csv()
        return False
    return True


def store_trade_data(features, target, result):
    """Salva os dados da negociação no CSV apenas se for uma negociação vencedora (win)."""
    if result <= 0:  # Apenas salvar se for um win
        print("Negociação perdida. Dados não serão armazenados.")
        return
    if not validate_csv():
        return
    features = np.array(features).flatten()
    new_data = pd.DataFrame([np.append(features, target)], 
                             columns=[f"feature_{i}" for i in range(len(features))] + ['target'])
    
    df = pd.read_csv(csv_path)
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(csv_path, index=False)
    print("Dados da negociação vencedora armazenados.")
    

def store_trade_data_and_update_model(features, target, result, asset):
    """Salva os dados da negociação vencedora e treina o modelo."""
    if result <= 0:
        print("Negociação perdida. Dados não serão armazenados.")
        return
    print("Salvando dados da negociação vencedora...")
    
    # Obtém os últimos 60 candles antes de salvar
    historical_features = fetch_candles(asset)
    if historical_features is None:
        print(f"Erro ao obter candles históricos para {asset}. Pulando armazenamento de dados.")
        return
    
    full_features = np.concatenate((features, historical_features))
    
    if not validate_csv():
        return
    
    new_data = pd.DataFrame([np.append(full_features, target)], 
                             columns=[f"feature_{i}" for i in range(len(full_features))] + ['target'])
    
    df = pd.read_csv(csv_path)
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(csv_path, index=False)
    print("Dados da negociação vencedora armazenados.")
    
    print("Treinando o modelo com os novos dados...")
    success = train_and_save_model()
    if success:
        print("Modelo atualizado e salvo em .pkl com sucesso!")
    else:
        print("Erro: Modelo não foi atualizado corretamente.")



# Função para usar o modelo na decisão de negociação

def predict_trade(features):
    """Faz uma previsão com base no modelo treinado."""
    model = load_model()
    if model is None:
        return None
    features = np.array(features).reshape(1, -1)
    prediction = model.predict(features)
    probability = model.predict_proba(features)[0]
    confidence = max(probability)
    return prediction[0], confidence

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

# Adapted fetch_sorted_assets function
def fetch_sorted_assets():
    """Obtém e retorna os 10 melhores ativos ordenados por lucratividade e volume para negociações de 5 minutos."""
    logging.info("Buscando e classificando ativos por lucratividade e volume para negociações de 5 minutos...")
    reconnect_if_needed()

    if iq is None:
        logging.info("API desconectada. Não é possível buscar ativos.")
        return []

    try:
        assets = iq.get_all_ACTIVES_OPCODE()
        raw_profitability = iq.get_all_profit()
        raw_volume = {}  # Placeholder para lógica real de volume

        profitability = {}
        volume = {}
        for asset, values in raw_profitability.items():
            if isinstance(values, dict):  # Tratamento para defaultdict
                profitability[asset] = float(values.get('turbo', 0.0))  # 'turbo' é usado para negociações de 5 minutos
            else:
                profitability[asset] = float(values)

        # Preenchendo o dicionário de volume com valores reais
        for asset in assets.keys():
            volume[asset] = 0  # Placeholder para valores reais

        sorted_assets = sorted(
            assets.keys(),
            key=lambda asset: (profitability.get(asset, 0.0), volume.get(asset, 0)),
            reverse=True
        )[:10]  # Mantendo apenas os 10 melhores ativos

        log_message(f"Ativos classificados por lucratividade e volume para negociações de 5 minutos: {sorted_assets}")
        return sorted_assets
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

# Função para tomar decisão com base nos indicadores
def analyze_market(asset):
    data = fetch_candles(asset)
    if data is None:
        return None
    data = calculate_indicators(data)
    
    latest = data.iloc[-1]
    decision = "hold"
    
    if latest['rsi'] < 30 and latest['close'] > latest['sma']:
        decision = "buy"
    elif latest['rsi'] > 70 and latest['close'] < latest['sma']:
        decision = "sell"
    
    return decision

# Função para calcular indicadores técnicos
def calculate_indicators(asset):
    data = fetch_candles(asset)
    if data is None or data.empty:
        return None, 0
    
    data['sma'] = data['close'].rolling(10).mean()
    data['ema'] = data['close'].ewm(span=10, adjust=False).mean()
    data['volatility'] = data['close'].pct_change().rolling(10).std()
    data['rsi'] = 100 - (100 / (1 + (data['close'].diff(1).clip(lower=0).rolling(14).mean() / data['close'].diff(1).clip(upper=0).rolling(14).mean()).fillna(1)))
    data.dropna(inplace=True)
    
    if data.empty:
        return None, 0
    
    indicators = {
        "rsi": data.iloc[-1]['rsi'],
        "sma": data.iloc[-1]['sma'],
        "ema": data.iloc[-1]['ema'],
        "volatility": data.iloc[-1]['volatility']
    }
    
    total_votes = sum(1 for v in indicators.values() if pd.notna(v))
    return indicators, total_votes

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



# Função para armazenar negociações e atualizar o modelo
def store_trade_data(features, target):
    """Salva os dados da negociação no CSV sem treinar o modelo."""
    if not validate_csv():
        return
    features = np.array(features).flatten()
    new_data = pd.DataFrame([np.append(features, target)], 
                             columns=[f"feature_{i}" for i in range(len(features))] + ['target'])
    
    df = pd.read_csv(csv_path)
    if 'target' not in df.columns:
        print("Erro ao salvar dados: Coluna 'target' ausente. Recriando arquivo de dados...")
        recreate_csv()
        df = pd.read_csv(csv_path)
    
    expected_columns = df.shape[1]
    actual_columns = len(features) + 1
    
    if actual_columns != expected_columns:
        print(f"Erro ao salvar dados: {actual_columns} colunas encontradas, mas {expected_columns} esperadas. Ajustando arquivo...")
        recreate_csv()
        return
    
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(csv_path, index=False)
    print("Dados da negociação armazenados.")


def store_trade_data_and_update_model(features, target):
    """Salva os dados da negociação no CSV e atualiza o modelo."""
    store_trade_data(features, target)
    train_and_save_model()


def make_trade_decision(features, min_confidence=0.7):
    """Decide se deve fazer a negociação baseado na confiança do modelo."""
    prediction, confidence = predict_trade(features)
    if prediction is None or confidence < min_confidence:
        print("Confiança baixa. Negociação não realizada.")
        return None
    action = "buy" if prediction == 1 else "sell"
    print(f"Decisão do modelo: {action} com confiança de {confidence:.2f}")
    return action

# Função para usar o modelo na decisão de negociação
def predict_trade_direction(asset, indicators, total_votes):
    model = load_model()
    if model is None:
        log_message(f"Sem modelo treinado para {asset}. Pulando decisão.")
        return None
    
    candles = fetch_candles(asset)
    if candles is None:
        log_message(f"Sem dados de candles para {asset}. Pulando decisão.")
        return None
    
    features = candles.flatten().reshape(1, -1)  # Transformando os dados para o formato esperado
    prediction = model.predict(features)
    model_decision = 'buy' if prediction == 1 else 'sell'
    
    # O modelo decide, mas leva em conta os indicadores
    if total_votes >= 3:
        decision = 'buy'
    elif total_votes <= 1:
        decision = 'sell'
    else:
        decision = model_decision
    
    log_message(f"Decisão final para {asset}: {decision} (Modelo: {model_decision}, Indicadores: {indicators})")
    return decision


# Função para executar negociações com IA integrada
def execute_trades():
    """Executa negociações com IA integrada."""
    global running, current_amount, consecutive_losses, session_profit, simultaneous_trades, saldo_entrada

    while running:
        print("Executando negociações...")
        model = load_model()
        if model is None:
            print("Modelo não carregado. Pulando execução de negociações.")
            break
        
        assets = fetch_sorted_assets()
        if not assets:
            print("Nenhum ativo encontrado. Parando execução.")
            break

        for asset in assets:
            if not running:
                print("Execução de negociações interrompida.")
                break
            
            if ignore_assets(asset):
                print(f"Ignorando ativo {asset}.")
                continue
            
            if simultaneous_trades >= max_simultaneous_trades:
                print("Número máximo de negociações simultâneas atingido. Aguardando...")
                time.sleep(50)
                check_trade_results()
                update_session_profit()
                continue
            
            check_trade_results()
            update_session_profit()
            
            candles = fetch_candles(asset)
            if candles is None or len(candles) == 0:
                print(f"Sem dados de candles para {asset}. Pulando ativo.")
                continue
            
            features = candles.flatten()
            decision = make_trade_decision(features)
            
            if decision is None:
                print(f"Decisão incerta para {asset}. Pulando negociação.")
                continue
            
            action = "call" if decision == "buy" else "put"
            print(f"Tentando realizar negociação: Ativo={asset}, Ação={action}, Valor=R${current_amount}")
            saldo_entrada = iq.get_balance()
            
            try:
                success, trade_id = iq.buy(current_amount, asset, action, 5)
                if success:
                    simultaneous_trades += 1
                    add_trade_to_list(trade_id)
                    print(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
                    threading.Thread(target=monitor_trade, args=(trade_id, asset, features, 1 if decision == 'buy' else 0)).start()

                else:
                    print(f"Falha ao realizar negociação para {asset}. Motivo: {trade_id}")
            except Exception as e:
                print(f"Erro durante a execução da negociação para {asset}: {e}")
                if "WinError 10054" in str(e):
                    print("Conexão perdida. Tentando reconectar...")
                    reconnect_if_needed()
                    if iq and iq.check_connect():
                        print("Reconexão bem-sucedida. Continuando operações.")
                        continue
                    else:
                        print("Falha na reconexão. Parando operações.")
                        running = False
                        break


def monitor_trade(trade_id, asset, features, target):
    """Monitora uma negociação e atualiza o modelo com o resultado."""
    global simultaneous_trades, session_profit, consecutive_losses, current_amount, saldo_saida, amount_doubled
    try:
        print(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        result = None
        while result is None:
            try:
                result = iq.check_win_v4(trade_id)
                if result is None:
                    print(f"Negociação {trade_id} ainda não concluída. Tentando novamente...")
                    time.sleep(1)
            except Exception as e:
                print(f"Erro ao verificar status da negociação {trade_id}: {e}")
                time.sleep(1)

        result = float(result) if isinstance(result, (int, float)) else -1.0
        session_profit += result
        saldo_saida = iq.get_balance()
        print(f"Resultado da negociação {trade_id}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")
        update_session_profit()
        
        if result > 0:
            store_trade_data_and_update_model(features, target, result)
        
        if result <= 0:
            consecutive_losses += 1
            if consecutive_losses > 3:
                print("Resetando valor inicial após múltiplas perdas.")
                consecutive_losses = 0
                set_amount()
                amount_doubled = False
            else:
                if not amount_doubled:
                    current_amount *= 2
                    amount_doubled = True
                    print(f"Dobrar valor da negociação. Próximo valor: R${current_amount}")
        else:
            consecutive_losses = 0
            set_amount()
            amount_doubled = False
            store_trade_data_and_update_model(features, target, result)
            print("Negociação bem-sucedida, resetando parâmetros.")
    finally:
        simultaneous_trades -= 1
        print(f"Balance after closing trade: {iq.get_balance()}")


def check_trade_results():
    """Verifica o status de todas as negociações pendentes."""
    global trade_list, session_profit, consecutive_losses, current_amount, amount_doubled
    for trade_id in trade_list.copy():
        try:
            result = iq.check_win_v4(trade_id)
            if result is not None:
                result = float(result) if isinstance(result, (int, float)) else -1.0
                session_profit += result
                print(f"Resultado da negociação {trade_id}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")
                if result <= 0:
                    consecutive_losses += 1
                    if not amount_doubled:
                        current_amount *= 2
                        amount_doubled = True
                        print(f"Dobrar valor da negociação. Próximo valor: R${current_amount}")
                else:
                    consecutive_losses = 0
                    set_amount()
                    amount_doubled = False
                    
                    print("Negociação bem-sucedida, resetando parâmetros.")
                trade_list.remove(trade_id)
        except Exception as e:
            print(f"Erro ao verificar status da negociação {trade_id}: {e}")

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
        martingale_label.config(text="M", fg="#011203")  # Same color as the background

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
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# GUI Configuration
root = tk.Tk()
root.title(f"Capybara v7.9 AI POWERED - Conta: {account_type} - {email}")
root.configure(bg="#011203")

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#011203")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

stop_button = tk.Button(root, text="Smart Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=1, padx=5, pady=5)

balance_label = tk.Label(root, text="Balance: R$0.00", bg="#011203", fg="white", font=("Helvetica", 12))
balance_label.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

# Add Martingale label
martingale_label = tk.Label(root, text="M", bg="#011203", fg="#011203", font=("Helvetica", 12))
martingale_label.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#011203", fg="white")
log_text.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Redirect stdout and stderr to the log_text widget
sys.stdout = TextRedirector(log_text, "stdout")
sys.stderr = TextRedirector(log_text, "stderr")

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#011203", fg="white")
profit_label.grid(row=4, column=0, columnspan=5, padx=10, pady=10)

footer_label = tk.Label(
    root,
     text="@oedlopes - 2025  - Deus Seja Louvado - Sola Scriptura - Sola Fide - Solus Christus - Sola Gratia - Soli Deo Gloria",
    bg="#011203",
    fg="#A9A9A9",
    font=("Helvetica", 7)
)
footer_label.grid(row=5, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")
#À∴G∴D∴G∴A∴D∴U∴
update_log()
update_session_profit()
check_file_accessibility()
# Start trading automatically
start_trading()

root.mainloop()
#-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
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
root.configure(bg="#011203")


static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#011203")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

start_button = tk.Button(root, text="Start", command=start_trading, bg="#4CAF50", fg="white", font=("Helvetica", 12))
start_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=2, padx=5, pady=5)

amount_label = tk.Label(root, text="Initial Amount:", bg="#011203", fg="white", font=("Helvetica", 12))
amount_label.grid(row=1, column=1, padx=5, pady=5)

amount_entry = tk.Entry(root, font=("Helvetica", 12))
amount_entry.insert(0, "2")
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#011203", fg="white")
log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#011203", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Rodapé
footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - Deus seja louvado",
    bg="#011203",
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








































