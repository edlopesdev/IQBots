# Arquivo: ASonic.0.7.py

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
import concurrent.futures

class TimeoutException(Exception):
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
    print(message)

# Função para tratar mensagens recebidas
def on_message(message):
    try:
        if not message:
            logging.error("Mensagem vazia recebida. Verifique o servidor ou a conexão.")
            return
        decoded_message = json.loads(message)
        logging.info(f"Mensagem decodificada: {decoded_message}")
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar mensagem JSON: {e}. Mensagem: {message}")

# Exemplo de uso da função on_message
on_message('{"key": "value"}')
on_message('')
on_message('not a json')

# Inicializar a API IQ Option
account_type = "PRATICE"  # Conta Real - ALTERADO PARA TESTE
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
win_count = 0  # Adicionar contagem de vitórias
loss_count = 0  # Adicionar contagem de perdas
iq = None  # Instância da API IQ Option
trade_list = []

# Conectar à API IQ Option
def connect_to_iq_option(email, password):
    global iq
    log_message("Tentando conectar à API IQ Option...")
    iq = IQ_Option(email, password)
    check, reason = iq.connect()
    if check:
        iq.change_balance(account_type)  # Alternar entre 'PRACTICE' e 'REAL'
        log_message("Conexão bem-sucedida com a API IQ Option.")
    else:
        log_message(f"Falha ao conectar à API IQ Option: {reason}")
        iq = None  # Garantir que iq seja None se a conexão falhar
    return check, reason

def fetch_sorted_assets():
    logging.info("Buscando e classificando ativos por volume e lucratividade...")
    reconnect_if_needed()

    if iq is None:
        logging.info("API desconectada. Não é possível buscar ativos.")
        return []

    try:
        assets = iq.get_all_ACTIVES_OPCODE()
        raw_profitability = iq.get_all_profit()

        profitability = {}
        for asset, values in raw_profitability.items():
            if isinstance(values, dict):  # Tratamento para defaultdict
                profitability[asset] = float(values.get('binary', 0.0))
            else:
                profitability[asset] = float(values)

        sorted_assets = sorted(
            assets.keys(),
            key=lambda asset: profitability.get(asset, 0.0),
            reverse=True
        )

        log_message(f"Ativos classificados: {sorted_assets}")
        return sorted_assets
    except Exception as e:
        log_message(f"Erro ao buscar e classificar ativos: {e}")
        return []

def add_trade_to_list(trade_id):
    global trade_list
    trade_list.append(trade_id)
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
    df["volume"] = df["volume"].astype(float)  # Ensure volume is cast to float
    return df

# Função para reconectar à API
def reconnect():
    global iq
    while True:
        if iq is None or not iq.check_connect():
            logging.info("Reconectando à API IQ Option...")
            iq = IQ_Option(email, password)
            check, reason = iq.connect()
            if check:
                iq.change_balance(account_type)
                logging.info("Reconexão bem-sucedida.")
            else:
                logging.error(f"Falha na reconexão: {reason}")
        time.sleep(5)

# Substituir chamada de ativos pelo novo método ordenado
threading.Thread(target=reconnect, daemon=True).start()

# Atualização da função analyze_indicators
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

        indicators = {}
        available_indicators = {
            "rsi": lambda: ta.rsi(data["close"], length=14),
            "macd": lambda: ta.macd(data["close"])["MACD_12_26_9"],
            "ema": lambda: ta.ema(data["close"], length=9),
            "sma": lambda: ta.sma(data["close"], length=20),
            "stochastic": lambda: ta.stoch(data["high"], data["low"], data["close"])["STOCHk_14_3_3"],
            "atr": lambda: ta.atr(data["high"], data["low"], data["close"], length=14),
            "adx": lambda: ta.adx(data["high"], data["low"], data["close"], length=14),
            "bollinger_high": lambda: ta.bbands(data["close"])["BBU_20_2.1"],
            "bollinger_low": lambda: ta.bbands(data["close"])["BBL_20_2.1"],
            "cci": lambda: ta.cci(data["high"], data["low"], data["close"], length=20),
            "willr": lambda: ta.willr(data["high"], data["low"], data["close"], length=14),
            "roc": lambda: ta.roc(data["close"], length=12),
            "obv": lambda: ta.obv(data["close"], data["volume"]),
            "trix": lambda: ta.trix(data["close"], length=15),
            "vwma": lambda: ta.vwma(data["close"], data["volume"], length=20),
            "mfi": lambda: ta.mfi(data["high"], data["low"], data["close"], data["volume"], length=14),
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
            if data["close"].iloc[-1] < indicators["bollinger_low"]():
                decisions.append("buy")
            elif data["close"].iloc[-1] > indicators["bollinger_high"]():
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

def countdown(seconds):
    while seconds > 0:
        log_message(f"Aguardando {seconds} segundos...")
        time.sleep(1)
        seconds -= 1

# Execução de trades
def execute_trades():
    global running
    global current_amount
    global consecutive_losses
    global session_profit
    global simultaneous_trades

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

            if simultaneous_trades >= max_simultaneous_trades:
                log_message("Limite máximo de negociações simultâneas atingido. Aguardando 5 minutos...")
                countdown(300)  # 5-minute countdown
                check_trade_results()
                update_session_profit()
                continue

            decision = analyze_indicators(asset)
            if decision == "buy":
                action = "call"
            elif decision == "sell":
                action = "put"
            else:
                log_message(f"Pulando negociação para {asset}. Sem consenso.")
                continue

            log_message(f"Tentando realizar negociação: Ativo={asset}, Ação={action}, Valor=${current_amount}")

            try:
                success, trade_id = iq.buy(current_amount, asset, action, 5)
                if success:
                    simultaneous_trades += 1
                    add_trade_to_list(trade_id)
                    log_message(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
                    threading.Thread(target=monitor_trade, args=(trade_id, asset)).start()
                else:
                    log_message(f"Falha ao realizar negociação para {asset}.")
            except Exception as e:
                log_message(f"Erro durante a execução da negociação para {asset}: {e}")

        # Ensure results are checked periodically
        check_trade_results()
        update_session_profit()

# Atualização da função monitor_trade
def monitor_trade(trade_id, asset):
    global simultaneous_trades
    global session_profit
    global consecutive_losses
    global current_amount

    try:
        log_message(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        result = None
        while result is None:
            try:
                result = iq.check_win_v4(trade_id)
                if result is None:
                    log_message(f"Negociação {trade_id} ainda não concluída. Tentando novamente em 5 segundos...")
                    time.sleep(5)
            except Exception as e:
                log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")
                time.sleep(5)

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

        session_profit += result
        log_message(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")

        update_session_profit()

        if result < 0:
            consecutive_losses += 1
            if consecutive_losses >= martingale_limit:
                current_amount = initial_amount
                consecutive_losses = 0
                log_message("Limite do Martingale atingido. Redefinindo valor para o inicial.")
            else:
                current_amount *= 2
                log_message(f"Dobrar valor da negociação. Próximo valor de negociação: ${current_amount}")
        else:
            consecutive_losses = 0
            current_amount = initial_amount

    finally:
        simultaneous_trades -= 1

# Função para ignorar ativos específicos
def ignore_assets(asset):
    assets_to_ignore = ["YAHOO", "TWITTER"]
    return asset.upper() in assets_to_ignore

# Função para zerar limite de negociações simultâneas e iniciar checagem de resultados
def reset_simultaneous_trades():
    global simultaneous_trades, current_amount, consecutive_losses
    while True:
        time.sleep(300)  # 5 minutos
        logging.info("Zerando limite de negociações simultâneas e iniciando checagem de resultados...")
        while simultaneous_trades > 0:
            time.sleep(5)  # Aguarda até que todas as negociações sejam monitoradas
        check_trade_results()  # Ensure results are checked after countdown

# Função para reduzir o número de negociações simultâneas após 5 minutos
def decrease_simultaneous_trades():
    global simultaneous_trades
    while True:
        time.sleep(180)  # 3 minutos
        if simultaneous_trades > 0:
            simultaneous_trades -= 1
            logging.info(f"Reduzindo negociações simultâneas. Atual: {simultaneous_trades}")

# Função para checar resultados de negociações
def check_trade_results():
    global trade_list, session_profit, win_count, loss_count, current_amount, consecutive_losses
    log_message("Checking trade results...")
    for trade_id in trade_list[:]:  # Iterate over a copy of the list
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
                            log_message(f"Erro ao converter resultado para float: {result}")
                            result = 0.0  # Default to 0.0 if conversion fails

                session_profit += result
                log_message(f"Trade ID {trade_id} result: {'WIN' if result > 0 else 'LOSS'}, Profit: {result}, Session Profit: {session_profit}")
                if result > 0:
                    win_count += 1
                else:
                    loss_count += 1
                    session_profit -= abs(current_amount)  # Subtract the loss from the session profit
                    current_amount *= 2  # Double the amount for the next trade
                    if current_amount > initial_amount * (2 ** martingale_limit):
                        log_message("Martingale limit reached. Resetting to initial amount.")
                        current_amount = initial_amount
                trade_list.remove(trade_id)  # Ensure the trade is removed from the list after checking
            else:
                log_message(f"Trade ID {trade_id} is still open. Skipping for now.")
        except Exception as e:
            log_message(f"Error checking result for trade ID {trade_id}: {e}")

def check_all_results():
    global consecutive_losses, current_amount
    try:
        logging.info("Checando resultados de negociações...")
        trades = iq.get_positions("closed")  # Atualizado para método correto
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
                consecutive_losses += 1
                if consecutive_losses >= martingale_limit:
                    current_amount = initial_amount
                    consecutive_losses = 0
                    logging.info("Limite do Martingale atingido. Reiniciando o valor para o inicial.")
                else:
                    current_amount *= 2
                    logging.info(f"Aplicando Martingale. Próximo valor: {current_amount}")
            else:
                consecutive_losses = 0
                current_amount = initial_amount
    except Exception as e:
        logging.error(f"Erro ao checar resultados: {e}")

# Inicializar threads
threading.Thread(target=reconnect, daemon=True).start()
threading.Thread(target=reset_simultaneous_trades, daemon=True).start()
threading.Thread(target=decrease_simultaneous_trades, daemon=True).start()

# Exemplo de teste da função on_message
on_message('{"key": "value"}')

# GUI Setup with dark theme
def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=execute_trades).start()

def stop_trading():
    global running
    running = False
    icon_label.config(image=static_icon)
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
    if running:
        root.after(1000, update_log)

def update_session_profit():
    profit_label.config(text=f"Lucro: R${session_profit:.2f}", fg="green" if session_profit >= 0 else "red")

def set_amount(amount):
    global initial_amount
    global current_amount
    initial_amount = amount
    current_amount = amount
    log_message(f"Initial amount set to: ${initial_amount}")

def switch_account_type():
    global account_type
    reconnect_if_needed()
    if iq is None:
        log_message("Unable to switch account. IQ Option API is not connected.")
        return

    previous_account = account_type
    account_type = "REAL" if account_type == "PRACTICE" else "PRACTICE"
    success = iq.change_balance(account_type)
    if success:
        log_message(f"Successfully switched to {'Demo' if account_type == 'PRACTICE' else 'Real'} account")
    else:
        log_message(f"Failed to switch account type. Current type remains as {'Demo' if previous_account == 'PRACTICE' else '             '}")

# GUI Configuration
root = tk.Tk()
root.title("Sonic v0.7")
root.configure(bg="#05071f")

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_sonic.png")
icon_label = tk.Label(root, image=static_icon, bg="#05071f")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

start_button = tk.Button(root, text="Start", command=start_trading, bg="#4CAF50", fg="white", font=("Helvetica", 12))
start_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=2, padx=5, pady=5)

switch_account_button = tk.Button(root, text="Switch Account", command=switch_account_type, bg="#2196F3", fg="white", font=("Helvetica", 12))
switch_account_button.grid(row=0, column=3, padx=5, pady=5)

amount_label = tk.Label(root, text="Initial Amount:", bg="#05071f", fg="white", font=("Helvetica", 12))
amount_label.grid(row=1, column=1, padx=5, pady=5)

amount_entry = tk.Entry(root, font=("Helvetica", 12))
amount_entry.insert(0, "2")
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#05071f", fg="white")
log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#05071f", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

win_label = tk.Label(root, text="Wins: 0", font=("Helvetica", 16), bg="#05071f", fg="green")
win_label.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

loss_label = tk.Label(root, text="Losses: 0", font=("Helvetica", 16), bg="#05071f", fg="red")
loss_label.grid(row=4, column=2, columnspan=2, padx=10, pady=10)

footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - Deus Seja Louvado",
    bg="#05071f",
    fg="#A9A9A9",
    font=("Helvetica", 5)
)
footer_label.grid(row=5, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")
#À∴G∴D∴G∴A∴D∴U∴
update_log()
update_session_profit()
root.mainloop()

# Fim do arquivo ACapybara.4.0.py