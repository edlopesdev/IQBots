# Arquivo: ASonic.0.9.py

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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
running_s = False
icon_label_s = None
initial_amount_s = 2
current_amount_s = 2  # Acompanhar o valor atual da negociação para estratégia Martingale
max_simultaneous_trades_s = 3
simultaneous_trades_s = 0  # Inicializar o contador de negociações simultâneas
martingale_limit_s = 5  # Limite de negociações Martingale consecutivas
consecutive_losses_s = 0
session_profit_s = 0
iq_s = None  # Instância da API IQ Option
trade_list_s = []

# Conectar à API IQ Option
def connect_to_iq_option_s(email, password):
    global iq_s
    log_message("Tentando conectar à API IQ Option...")
    iq_s = IQ_Option(email, password)
    check, reason = iq_s.connect()
    if check:
        iq_s.change_balance(account_type)  # Alternar entre 'PRACTICE' e 'REAL'
        log_message("Conexão bem-sucedida com a API IQ Option.")
    else:
        log_message(f"Falha ao conectar à API IQ Option: {reason}")
        iq_s = None  # Garantir que iq seja None se a conexão falhar
    return check, reason

def fetch_sorted_assets_s():
    logging.info("Buscando e classificando ativos por lucratividade e volume para negociações de 1 minuto...")
    reconnect_if_needed_s()

    if iq_s is None:
        logging.info("API desconectada. Não é possível buscar ativos.")
        return []

    try:
        assets = iq_s.get_all_ACTIVES_OPCODE()
        raw_profitability = iq_s.get_all_profit()
        # Replace the following line with a valid method to fetch asset volumes
        raw_volume = {}  # Placeholder for actual volume fetching logic

        profitability = {}
        volume = {}
        for asset, values in raw_profitability.items():
            if isinstance(values, dict):  # Tratamento para defaultdict
                profitability[asset] = float(values.get('turbo', 0.0))  # 'turbo' is used for 1-minute trades
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

        log_message(f"Ativos classificados por lucratividade e volume para negociações de 1 minuto: {sorted_assets}")
        return sorted_assets
    except Exception as e:
        log_message(f"Erro ao buscar e classificar ativos: {e}")
        return []

def add_trade_to_list_s(trade_id):
    global trade_list_s
    trade_list_s.append(trade_id)
    print(f"Trade ID {trade_id} added to the monitoring list.")
    log_message(f"Trade ID {trade_id} added to the monitoring list.")

def reconnect_if_needed_s():
    global iq_s
    if iq_s is None or not iq_s.check_connect():
        log_message("API desconectada. Tentando reconectar...")
        connect_to_iq_option_s(email, password)
        if not iq_s or not iq_s.check_connect():
            log_message("Falha na reconexão. Saindo...")
            running_s = False

def fetch_historical_data_s(asset, duration, candle_count):
    reconnect_if_needed_s()
    ignored_assets = {"yahoo", "twitter", "AGN:US"}
    candles = iq_s.get_candles(asset, duration * 60, candle_count, time.time())
    df = pd.DataFrame(candles)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["max"].astype(float)
    df["low"] = df["min"].astype(float)
    return df

 #Função para reconectar à API

def reconnect_s():
    global iq_s
    while True:
        if iq_s is None or not iq_s.check_connect():
            logging.info("Reconectando à API IQ Option...")
            iq_s = IQ_Option(email, password)
            check, reason = iq_s.connect()
            if check:
                iq_s.change_balance(account_type)
                logging.info("Reconexão bem-sucedida.")
            else:
                logging.error(f"Falha na reconexão: {reason}")
        time.sleep(5)

# Substituir chamada de ativos pelo novo método ordenado
threading.Thread(target=reconnect_s, daemon=True).start()

# Atualização da função analyze_indicators

def analyze_indicators_s(asset):
    if ignore_assets_s(asset):
        log_message(f"Ignorando ativo {asset}.")
        return None

    log_message(f"Analisando indicadores para {asset}...")
    try:
        data = fetch_historical_data_s(asset, 1, 100)

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
        }

        for key, func in available_indicators.items():
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("error", category=FutureWarning)
                    result = func()
                    if result is not None and not result.empty:
                        indicators[key] = result.iloc[-1]
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

def countdown_s(seconds):
    while seconds > 0:
        log_message(f"Aguardando {seconds} segundos...")
        time.sleep(1)
        seconds -= 1
#Execução de trades

def execute_trades_s():
    global running_s
    global current_amount_s
    global consecutive_losses_s
    global session_profit_s
    global simultaneous_trades_s

    while running_s:
        log_message("Executando negociações...")
        assets = fetch_sorted_assets_s()

        if not assets:
            log_message("Nenhum ativo encontrado. Parando execução.")
            break

        for asset in assets:
            if not running_s:
                log_message("Execução de negociações interrompida.")
                break

            if simultaneous_trades_s >= 1:  # Ensure only one trade at a time
                log_message("Aguardando a conclusão da negociação atual...")
                countdown_s(10)  # Shorter countdown to check trade results more frequently
                check_trade_results_s()
                update_session_profit_s()
                continue

            # Ensure results are checked periodically and reset amount if needed
            check_trade_results_s()
            update_session_profit_s()

            decision = analyze_indicators_s(asset)
            if decision == "buy":
                action = "call"
            elif decision == "sell":
                action = "put"
            else:
                log_message(f"Pulando negociação para {asset}. Sem consenso.")
                continue

            log_message(f"Tentando realizar negociação: Ativo={asset}, Ação={action}, Valor = R${current_amount_s}")

            try:
                success, trade_id = iq_s.buy(current_amount_s, asset, action, 1)  # Negociações de 1 minuto
                if success:
                    simultaneous_trades_s += 1
                    add_trade_to_list_s(trade_id)
                    log_message(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
                    print(f"Balance after opening trade: {iq_s.get_balance()}")
                    threading.Thread(target=monitor_trade_s, args=(trade_id, asset)).start()
                    countdown_s(60)  # Aguardando o fim da negociação de 1 minuto
                else:
                    log_message(f"Falha ao realizar negociação para {asset}.")
            except Exception as e:
                log_message(f"Erro durante a execução da negociação para {asset}: {e}")

        # Ensure results are checked periodically
        check_trade_results_s()
        update_session_profit_s()

def monitor_trade_s(trade_id, asset):
    global simultaneous_trades_s
    global session_profit_s
    global consecutive_losses_s
    global current_amount_s

    try:
        print(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        log_message(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        result = None
        while result is None:
            try:
                result = iq_s.check_win_v4(trade_id)
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

        session_profit_s += result

        print(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")
        log_message(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")
        print(f"Balance after closing trade: {iq_s.get_balance()}")

        update_session_profit_s()

        if result <= 0:
            consecutive_losses_s += 1
            if consecutive_losses_s < martingale_limit_s:
                current_amount_s *= 2  # Double the amount for the next trade
                log_message(f"Dobrar valor da negociação. Próximo valor de negociação: R${current_amount_s}")
            else:
                log_message("Martingale limit reached. Resetting to initial amount.")
                current_amount_s = initial_amount_s
                consecutive_losses_s = 0
        else:
            consecutive_losses_s = 0
            current_amount_s = initial_amount_s  # Reset to initial amount after a win
            log_message(f"Negociação bem-sucedida. Valor de negociação resetado para: R${current_amount_s}")

    finally:
        simultaneous_trades_s -= 1
        if trade_id in trade_list_s:
            trade_list_s.remove(trade_id)  # Ensure the trade is removed from the list after checking

# Função para ignorar ativos específicos
assets_to_ignore = set([
    "CSGNZ-CHIX", "TA25", "DUBAI", "YAHOO", "TWITTER", "AGN:US", "CXO:US", "DNB:US", "DOW:US", "DTE:US", "DUK:US",
    "DVA:US", "DVN:US", "DXC:US", "DXCM:US", "ETFC:US", "TWX:US",
    "Expecting value: line 1 column 41 (char 40)"  # Added specific error message to ignore list
])
def ignore_assets_s(asset):
    return asset.upper() in assets_to_ignore or "-CHIX" in asset.upper()

# Função para zerar limite de negociações simultâneas e iniciar checagem de resultados
def reset_simultaneous_trades_s():
    global simultaneous_trades_s, current_amount_s, consecutive_losses_s
    while True:
        time.sleep(60)  # 1 minuto
        logging.info("Zerando limite de negociações simultâneas e iniciando checagem de resultados...")
        while simultaneous_trades_s > 0:
            time.sleep(5)  # Aguarda até que todas as negociações sejam monitoradas
        check_trade_results_s()  # Ensure results are checked after countdown
        log_message("Finished resetting simultaneous trades and checking results.")

# Função para reduzir o número de negociações simultâneas após 5 minutos
def decrease_simultaneous_trades_s():
    global simultaneous_trades_s
    while True:
        time.sleep(30)  # 30 segundos
        if simultaneous_trades_s > 0:
            simultaneous_trades_s -= 1
            logging.info(f"Reduzindo negociações simultâneas. Atual: {simultaneous_trades_s}")

# Função para checar resultados de negociações
def check_trade_results_s():
    global trade_list_s, session_profit_s, current_amount_s, consecutive_losses_s
    log_message("Checking trade results...")
    for trade_id in trade_list_s[:]:  # Iterate over a copy of the list
        try:
            result = iq_s.check_win_v4(trade_id)
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
                            log_message(f"Erro ao converter resultado para float: {result}")
                            result = 0.0  # Default to 0.0 if conversion fails

                session_profit_s += result
                log_message(f"Updated session profit: R${session_profit_s:.2f}")
                if result > 0:                    
                    consecutive_losses_s = 0
                    current_amount_s = initial_amount_s  # Reset to initial amount after a win
                else:                    
                    consecutive_losses_s += 1
                    if consecutive_losses_s < martingale_limit_s:
                        current_amount_s *= 2  # Double the amount for the next trade
                        log_message(f"Dobrar valor da negociação. Próximo valor de negociação: R${current_amount_s}")
                    else:
                        log_message("Martingale limit reached. Resetting to initial amount.")
                        current_amount_s = initial_amount_s
                        consecutive_losses_s = 0
                trade_list_s.remove(trade_id)  # Ensure the trade is removed from the list after checking
            else:
                log_message(f"Trade ID {trade_id} is still open. Skipping for now.")
        except Exception as e:
            log_message(f"Error checking result for trade ID {trade_id}: {e}")

    log_message("Finished checking trade results.")

def check_all_results():
    global consecutive_losses_s, current_amount_s
    try:
        logging.info("Checando resultados de negociações...")
        trades = iq_s.get_positions("closed")  # Atualizado para método correto
        if not isinstance(trades, list):  # Verifica se trades é uma lista
            logging.error("Formato inesperado de trades. Verifique a API.")
            return

        for trade in trades:
            if not isinstance(trade, dict):  # Certifique-se de que cada item é um dicionário
                logging.error(f"Formato inesperado para trade: {trade}")
                continue

            profit = trade.get('win', 0)  # Usa get para evitar exceções
            if isinstance(profit, tuple):
                profit = profit[0]  # Assuming the first element of the tuple is the profit/loss value
            if isinstance(profit, str):
                try:
                    profit = float(profit)  # Convert string to float
                except ValueError:
                    logging.error(f"Erro ao converter resultado para float: {profit}")
                    profit = 0.0  # Default to 0.0 if conversion fails

            if profit < 0:
                consecutive_losses_s += 1
                if consecutive_losses_s >= martingale_limit_s:
                    current_amount_s = initial_amount_s
                    consecutive_losses_s = 0
                    logging.info("Limite do Martingale atingido. Reiniciando o valor para o inicial.")
                else:
                    current_amount_s *= 2
                    logging.info(f"Aplicando Martingale. Próximo valor: {current_amount_s}")
            else:
                consecutive_losses_s = 0
                current_amount_s = initial_amount_s
    except Exception as e:
        logging.error(f"Erro ao checar resultados: {e}")

# Inicializar threads
threading.Thread(target=reconnect_s, daemon=True).start()
# threading.Thread(target=reset_simultaneous_trades, daemon=True).start()
# threading.Thread(target=decrease_simultaneous_trades, daemon=True).start()

# Exemplo de teste da função on_message
on_message('{"key": "value"}')

# GUI Setup with dark theme
def start_trading():
    global running_s
    if not running_s:
        running_s = True
        icon_label_s.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=execute_trades_s).start()

def stop_trading():
    global running_s
    running_s = False
    icon_label_s.config(image=static_icon)
    log_message("Trading session stopped.")

def update_log():
    try:
        with open(log_file, "r") as file:
            lines = file.readlines()
            log_text.delete(1.0, tk.END)
            log_text.insert(tk.END, "".join(lines[-10:]))
    except FileNotFoundError:
        log_text.delete(1.0, tk.END)
        log_text.insert(tk.END, "Log file not found. Waiting for new entries...\n")
    if running_s:
        root.after(1000, update_log)

def update_session_profit_s():
    profit_label.config(text=f"Lucro: R${session_profit_s:.2f}", fg="green" if session_profit_s >= 0 else "red")

def set_amount(amount):
    global initial_amount_s
    global current_amount_s
    initial_amount_s = amount
    current_amount_s = amount
    log_message(f"Initial amount set to: R${initial_amount_s}")


# Function to stop and start trading if the code freezes for more than 15 seconds
def watchdog():
    global running_s
    last_check = time.time()
    
    while True:
        time.sleep(5)
        if running_s and (time.time() - last_check > 15):
            log_message("Detected freeze. Restarting trading session...")
            stop_trading()
            time.sleep(1)
            start_trading()
        last_check = time.time()

# Start the watchdog thread
threading.Thread(target=watchdog, daemon=True).start()

# GUI Configuration
root = tk.Tk()
root.title("Sonic Trader v0.9")
root.configure(bg="#010124")

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_sonic.png")
icon_label_s = tk.Label(root, image=static_icon, bg="#010124")
icon_label_s.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

start_button = tk.Button(root, text="Start", command=start_trading, bg="#4CAF50", fg="white", font=("Helvetica", 12))
start_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=2, padx=5, pady=5)

amount_label = tk.Label(root, text="Initial Amount:", bg="#010124", fg="white", font=("Helvetica", 12))
amount_label.grid(row=1, column=1, padx=5, pady=5)

amount_entry = tk.Entry(root, font=("Helvetica", 12))
amount_entry.insert(0, "2")
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#010124", fg="white")
log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#010124", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - Deus Seja Louvado",
    bg="#010124",
    fg="#A9A9A9",
    font=("Helvetica", 5)
)
footer_label.grid(row=5, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")
#À∴G∴D∴G∴A∴D∴U∴
update_log()
update_session_profit_s()
root.mainloop()

# Fim do arquivo ASonic.0.9.py

# Ensure the WebsocketClient class uses the updated on_message function
class WebsocketClient:
    # ...existing code...
    def on_message(self, message):
        try:
            on_message(message)
        except json.JSONDecodeError as e:
            logging.error(f"JSONDecodeError in WebsocketClient.on_message: {e}. Message: {message}")
            # Add the asset to the ignore list
            asset = extract_asset_from_message(message)
            if asset:
                add_asset_to_ignore_list(asset)
            return  # Ignore the asset when a JSON decoding error occurs
        except Exception as e:
            logging.error(f"Error in WebsocketClient.on_message: {e}. Message: {message}")
            # Add the asset to the ignore list
            asset = extract_asset_from_message(message)
            if asset:
                add_asset_to_ignore_list(asset)
            return  # Ignore the asset when any error occurs
    # ...existing code...