# ...existing code...

# Arquivo: Capybara.GF.0.6.py
#PECUNIA IMPROMPTA
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

log_file = os.path.normpath(os.path.join(os.getcwd(), "trade_log.txt"))

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
account_type = "PRACTICE"  # Conta Real - AGORA É PRA VALER!
instrument_types = ["binary", "crypto", "digital", "otc"]  # Tipos de instrumentos suportados

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
        else:
            log_message(f"Falha ao conectar à API IQ Option: {reason}")
            iq = None  # Garantir que iq seja None se a conexão falhar
    except json.JSONDecodeError as e:
        log_message(f"Erro ao decodificar JSON durante a conexão: {e}")
        iq = None
    except Exception as e:
        log_message(f"Erro inesperado durante a conexão: {e}")
        iq = None
    return check, reason

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
        # Replace the following line with a valid method to fetch asset volumes
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
    global iq
    if iq is None or not iq.check_connect():
        log_message("API desconectada. Tentando reconectar...")
        connect_to_iq_option(email, password)
        if not iq or not iq.check_connect():
            log_message("Falha na reconexão. Saindo...")
            running = False

def fetch_historical_data(asset, duration, candle_count):
    reconnect_if_needed()
    ignored_assets = {"yahoo", "twitter", "AGN:US"}
    candles = iq.get_candles(asset, duration * 60, candle_count, time.time())
    df = pd.DataFrame(candles)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["max"].astype(float)
    df["low"] = df["min"].astype(float)
    return df

# Função para reconectar à API
def reconnect():
    global iq
    while True:
        if iq is None or not iq.check_connect():
            logging.info("Reconectando à API IQ Option...")
            iq = IQ_Option(email, password)
            try:
                check, reason = iq.connect()
                if check:
                    iq.change_balance(account_type)
                    logging.info("Reconexão bem-sucedida.")
                else:
                    logging.error(f"Falha na reconexão: {reason}")
            except json.JSONDecodeError as e:
                logging.error(f"Erro ao decodificar JSON durante a reconexão: {e}")
                iq = None
            except Exception as e:
                logging.error(f"Erro inesperado durante a reconexão: {e}")
                iq = None
        time.sleep(5)

# Substituir chamada de ativos pelo novo método ordenado
threading.Thread(target=reconnect, daemon=True).start()

# Define the ignore_assets function
assets_to_ignore = set(["CSGNZ-CHIX","TA25","DUBAI","YAHOO", "TWITTER", "AGN:US", "CXO:US","DNB:US","DOW:US","DTE:US","DUK:US","DVA:US","DVN:US","DXC:US","DXCM:US", "ETFC:US", "TWX:US"])

def ignore_assets(asset):
    return asset.upper() in assets_to_ignore or "-CHIX" in asset.upper() or "XEMUSD-" in asset.upper() or "BSVUSD-" in asset.upper()

def analyze_trend(data):
    """
    Analyzes the trend of the last 30 candles.
    Returns 'up', 'down', or 'neutral' based on the analysis.
    """
    if len(data) < 30:
        log_message("Dados insuficientes para análise de tendência.")
        return "neutral"

    if data["close"].iloc[-30:].mean() > data["open"].iloc[-30:].mean():
        return "up"
    elif data["close"].iloc[-30:].mean() < data["open"].iloc[-30:].mean():
        return "down"
    else:
        return "neutral"

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

# Update the analyze_indicators function to include the new indicators
def analyze_indicators(asset):
    if ignore_assets(asset):
        log_message(f"Ignorando ativo {asset}.")
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
            "bollinger_high": lambda: ta.bbands(data["close"])["BBU_20_2.0"],  # Corrected key
            "bollinger_low": lambda: ta.bbands(data["close"])["BBL_20_2.0"],   # Corrected key
            "cci": lambda: ta.cci(data["high"], data["low"], data["close"], length=20),
            "willr": lambda: ta.willr(data["high"], data["low"], data["close"], length=14),
            "roc": lambda: ta.roc(data["close"], length=12),
            "obv": lambda: ta.obv(data["close"], data["volume"]),
            "trix": lambda: ta.trix(data["close"], length=15),
            "vwma": lambda: ta.vwma(data["close"], data["volume"], length=20),
            "mfi": lambda: ta.mfi(data["high"], data["low"], data["close"], data["volume"], length=14).astype(float),  # Cast to float
            "dpo": lambda: ta.dpo(data["close"], length=14),
            "keltner_upper": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCUp_20_2.1"],
            "keltner_lower": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCLo_20_2.1"],
            "ultimate_oscillator": lambda: ta.uo(data["high"], data["low"], data["close"]),
            "tsi": lambda: ta.tsi(data["close"]),
            "aroon_up": lambda: ta.aroon(data["high"], data["low"], length=25)["AROONU_25"],
            "aroon_down": lambda: ta.aroon(data["high"], data["low"], length=25)["AROOND_25"],
            "trend": lambda: analyze_trend(data),
            "last_candles": lambda: analyze_last_candles(data)
        }

        for key, func in available_indicators.items():
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("error", category=FutureWarning)
                    result = func()
                    if result is not None and not result.empty:
                        indicators[key] = result.iloc[-1] if isinstance(result, pd.Series) else result
            except FutureWarning as fw:
                log_message(f"FutureWarning ao calcular {key.upper()} para {asset}: {fw}. Pulando ativo.")
                return None
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
            if data["close"].iloc[-1] > indicators["ema"]:
                decisions.append("buy")
            else:
                decisions.append("sell")

        if indicators.get("sma") is not None:
            if data["close"].iloc[-1] > indicators["sma"]:
                decisions.append("buy")
            else:
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

        if indicators.get("trend") is not None:
            if indicators["trend"] == "up":
                decisions.append("buy")
            elif indicators["trend"] == "down":
                decisions.append("sell")

        if indicators.get("last_candles") is not None:
            if indicators["last_candles"] == "up":
                decisions.append("buy")
            elif indicators["last_candles"] == "down":
                decisions.append("sell")

        buy_votes = decisions.count("buy")
        sell_votes = decisions.count("sell")

        log_message(f"Votação de indicadores para {asset}: BUY={buy_votes}, SELL={sell_votes}")

        if buy_votes > sell_votes:
            return "buy"
        elif sell_votes > buy_votes:
            return "sell"
        else:
            log_message("Consenso insuficiente entre os indicadores. Pulando ativo.")
            return None

    except Exception as e:
        log_message(f"Erro ao analisar indicadores para {asset}: {e}")
        return None

# ...existing code...

# Adapted countdown function
def countdown(seconds):
    while seconds > 0:
        log_message(f"Aguardando {seconds} segundos...")
        time.sleep(1)
        seconds -= 1

# Adapted execute_trades function
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

            if simultaneous_trades >= 1:  # Ensure only one trade at a time
                log_message("Aguardando a conclusão da negociação atual...")
                countdown(50)  # Adjusted countdown for 5-minute trades
                check_trade_results()
                update_session_profit()
                continue

            # Ensure results are checked periodically and reset amount if needed
            check_trade_results()
            update_session_profit()

            decision = analyze_indicators(asset)
            if decision == "buy":
                action = "call"
            elif decision == "sell":
                action = "put"
            else:
                log_message(f"Pulando negociação para {asset}. Sem consenso.")
                continue

            log_message(f"Tentando realizar negociação: Ativo={asset}, Ação={action}, Valor = R${current_amount}")
            saldo_entrada = iq.get_balance()  # Store balance before trade
            print(f"Balance before opening trade: {saldo_entrada}")  # Display balance before trade
            try:
                success, trade_id = iq.buy(current_amount, asset, action, 5)  # Negociações de 5 minutos
                if success:
                    simultaneous_trades += 1
                    add_trade_to_list(trade_id)
                    log_message(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
                    print(f"Balance after opening trade: {iq.get_balance()}")  # Display balance after opening trade
                    threading.Thread(target=monitor_trade, args=(trade_id, asset)).start()
                    countdown(300)  # Aguardando o fim da negociação de 5 minutos
                else:
                    log_message(f"Falha ao realizar negociação para {asset}.")
            except Exception as e:
                log_message(f"Erro durante a execução da negociação para {asset}: {e}")

        # Ensure results are checked periodically
        check_trade_results()
        update_session_profit()

        if smart_stop and current_amount == initial_amount:
            running = False
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
            if consecutive_losses < 4:  # Change to 4 instead of 5
                current_amount *= 2  # Double the amount for the next trade
                amount_doubled = True  # Set the flag to indicate the amount has been doubled
                log_message(f"Dobrar valor da negociação. Próximo valor de negociação: R${current_amount}")
            else:
                log_message("Martingale limit reached. Reversing trade direction.")
                decision = analyze_indicators(asset)
                if decision == "buy":
                    action = "put"  # Reverse the decision
                elif decision == "sell":
                    action = "call"  # Reverse the decision
                else:
                    log_message(f"Pulando negociação para {asset}. Sem consenso.")
                    return
                current_amount *= 2  # Continue doubling the amount
                log_message(f"Reversed trade direction. Próximo valor de negociação: R${current_amount}, Ação={action}")
                consecutive_losses = 0
                amount_doubled = False  # Reset the flag
        else:
            consecutive_losses = 0
            set_amount()  # Reset to 2% of the balance after a win
            amount_doubled = False  # Reset the flag
            log_message(f"Negociação bem-sucedida. Valor de negociação resetado para: R${current_amount}")

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

                if result <= 0:
                    consecutive_losses += 1
                    if consecutive_losses < 4:  # Change to 4 instead of 5
                        current_amount *= 2  # Double the amount for the next trade
                        amount_doubled = True  # Set the flag to indicate the amount has been doubled
                        log_message(f"Dobrar valor da negociação. Próximo valor de negociação: R${current_amount}")
                    else:
                        log_message("Martingale limit reached. Reversing trade direction.")
                        decision = analyze_indicators(asset)
                        if decision == "buy":
                            action = "put"  # Reverse the decision
                        elif decision == "sell":
                            action = "call"  # Reverse the decision
                        else:
                            log_message(f"Pulando negociação para {asset}. Sem consenso.")
                            return
                        current_amount *= 2  # Continue doubling the amount
                        log_message(f"Reversed trade direction. Próximo valor de negociação: R${current_amount}, Ação={action}")
                        consecutive_losses = 0
                        amount_doubled = False  # Reset the flag
                else:
                    consecutive_losses = 0
                    set_amount()  # Reset to 2% of the balance after a win
                    amount_doubled = False  # Reset the flag
                    log_message(f"Negociação bem-sucedida. Valor de negociação resetado para: R${current_amount}")

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

# Update the set_amount function to use 2% of the account balance
def set_amount():
    global initial_amount
    global current_amount
    balance = iq.get_balance()
    initial_amount = balance * 0.02  # Set to 2% of the balance
    current_amount = initial_amount
    log_message(f"Initial amount set to 2% of balance: R${initial_amount:.2f}")
    balance_label.config(text=f"Balance: R${balance:.2f}")

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
root.title("Capybara Trader GFv0.6")
root.configure(bg="#001209")

rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=rotating_icon, bg="#001209")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

stop_button = tk.Button(root, text="Smart Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=1, padx=5, pady=5)

balance_label = tk.Label(root, text="Balance: R$0.00", bg="#001209", fg="white", font=("Helvetica", 12))
balance_label.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#001209", fg="white")
log_text.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Redirect stdout and stderr to the log_text widget
sys.stdout = TextRedirector(log_text, "stdout")
sys.stderr = TextRedirector(log_text, "stderr")

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#001209", fg="white")
profit_label.grid(row=4, column=0, columnspan=5, padx=10, pady=10)

footer_label = tk.Label(
    root,
     text="@oedlopes - 2025  - Deus Seja Louvado - Sola Scriptura - Sola Fide - Solus Christus - Sola Gratia - Soli Deo Gloria",
    bg="#001209",
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

# ...existing code...

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

# ...existing code...


