# Arquivo: ACapybara.2.4.py

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
from MGM_ import MartingaleManager
import sys
import queue
# Carregar credenciais do arquivo
credentials_file = os.path.normpath(os.path.join(os.getcwd(), "credentials.txt"))
sys.setrecursionlimit(2000)
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

API = IQ_Option(email, password)
# Função para tratar mensagens recebidas
import json
import logging
message_queue = queue.Queue()

def on_message(message):
    try:
        # Validação inicial da mensagem
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Mensagem vazia ou inválida recebida.")
        if not (message.startswith("{") and message.endswith("}")):
            raise ValueError("Mensagem não é um JSON válido.")

        # Tentativa de decodificar a mensagem JSON
        decoded_message = json.loads(message)
        message_queue.put(decoded_message)  # Adiciona a mensagem à fila
        logging.info(f"Mensagem processada: {decoded_message}")
        return decoded_message

    except ValueError as ve:
        logging.error(f"Erro de validação da mensagem: {ve}")
    except json.JSONDecodeError as je:
        logging.error(f"Erro ao decodificar JSON: {je}")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")

def process_message(message):
    while not message_queue.empty():
        message = message_queue.get()
    try:
        decoded_message = on_message(message)  # Decodificação segura
        # Processa a mensagem (sem recursão)
    except Exception as e:
        logging.error(f"Erro ao processar a mensagem: {e}")


# Exemplo de uso da função on_message
on_message('{"key": "value"}')
on_message('')
on_message('not a json')


# Inicializar a API IQ Option
account_type = "REAL"  # Conta Real - ALTERADO PARA TESTE
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
    if iq is None or not iq.check_connect():
        log_message("API desconectada. Tentando reconectar...")
        connect_to_iq_option(email, password)
        if iq is None or not iq.check_connect():
            log_message("Falha na reconexão. Não é possível buscar ativos.")
            return []

    try:
        digital_data = iq.get_digital_underlying_list_data()
        if digital_data is None or "underlying" not in digital_data:
            log_message("Nenhum ativo digital disponível.")
            return []

        assets = iq.get_all_ACTIVES_OPCODE()
        if not assets:
            log_message("Nenhum ativo disponível para negociação.")
            return []

        raw_profitability = iq.get_all_profit()
        profitability = {asset: float(values.get('binary', 0.0)) for asset, values in raw_profitability.items() if isinstance(values, dict)}
        sorted_assets = sorted(assets.keys(), key=lambda asset: profitability.get(asset, 0.0), reverse=True)
        log_message(f"Ativos classificados: {sorted_assets}")
        return sorted_assets
    except Exception as e:
        log_message(f"Erro ao buscar e classificar ativos: {e}")
        return []





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
    
    candles = iq.get_candles(asset, duration * 60, candle_count, time.time())
    df = pd.DataFrame(candles)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["max"].astype(float)
    df["low"] = df["min"].astype(float)
    return df


 #Função para reconectar à API

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
            "bollinger_high": lambda: ta.bbands(data["close"])["BBU_20_2.4"],
            "bollinger_low": lambda: ta.bbands(data["close"])["BBL_20_2.4"],
            "cci": lambda: ta.cci(data["high"], data["low"], data["close"], length=20),
            "willr": lambda: ta.willr(data["high"], data["low"], data["close"], length=14),
            "roc": lambda: ta.roc(data["close"], length=12),
            "obv": lambda: ta.obv(data["close"], data["volume"]),
            "trix": lambda: ta.trix(data["close"], length=15),
            "vwma": lambda: ta.vwma(data["close"], data["volume"], length=20),
            "mfi": lambda: ta.mfi(data["high"], data["low"], data["close"], data["volume"], length=14),
            "dpo": lambda: ta.dpo(data["close"], length=14),
            "keltner_upper": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCUp_20_2.4"],
            "keltner_lower": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCLo_20_2.4"],
            "ultimate_oscillator": lambda: ta.uo(data["high"], data["low"], data["close"]),
            "tsi": lambda: ta.tsi(data["close"]),
            "aroon_up": lambda: ta.aroon(data["high"], data["low"], length=25)["AROONU_25"],
            "aroon_down": lambda: ta.aroon(data["high"], data["low"], length=25)["AROOND_25"],
        }

        for key, func in available_indicators.items():
            try:
                result = func()
                if result is not None and not result.empty:
                    indicators[key] = result.iloc[-1]
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


#Execução de trades

def execute_trade(asset, action):
    """
    Realiza uma negociação simples, sem utilizar a lógica do Martingale.
    """
    global session_profit
    reconnect
    try:
        # Defina um valor fixo para negociação
        trade_amount = 2  # Valor fixo ou outro valor desejado
        log_message(f"Executando trade: Ativo={asset}, Ação={action}, Valor={trade_amount}")

        success, trade_id = iq.buy(trade_amount, asset, action, 5)

        if success:
            log_message(f"Trade iniciado: ID={trade_id}")
            result = iq.check_win_v3(trade_id)
            

            if result:
                session_profit += result["amount"]
                log_message(f"Resultado do trade: {result}")
        else:
            log_message(f"Falha ao executar trade para {asset}.")
    except Exception as e:
        log_message(f"Erro ao executar trade para {asset}: {e}")

def reconnect_if_needed():
    global iq
    if iq is None or not iq.check_connect():
        log_message("API desconectada. Tentando reconectar...")
        connect_to_iq_option(email, password)
        if not iq or not iq.check_connect():
            log_message("Falha na reconexão. Pulando ciclo de negociações.")
            time.sleep(30)  # Evite sobrecarregar a API


def start_trading_loop():
    """
    Inicia o loop de negociações com integração ao MartingaleManager.
    """
    global running

    while running:
        assets = fetch_sorted_assets()
        if not assets:
            log_message("Nenhum ativo disponível. Aguardando...")
            time.sleep(30)  # Aguarde antes de tentar novamente
            continue
        for asset in assets:
            if asset not in ignore_assets(True):
                decision = analyze_indicators(asset)

                if decision == "buy":
                    execute_trade(asset, "call")
                elif decision == "sell":
                    execute_trade(asset, "put")
                else:
                    log_message(f"Nenhuma decisão para {asset}, pulando...")

            update_session_profit()
            time.sleep(5) # Intervalo entre negociações
            continue
        reconnect_if_needed()
            
# Threads iniciais
threading.Thread(target=start_trading_loop, daemon=True).start()
threading.Thread(target=MartingaleManager.monitor_trades, daemon=True).start()

# Atualização da função monitor_trade

def monitor_trade(trade_id, asset):
    global simultaneous_trades
    global session_profit
    global consecutive_losses
    global current_amount

    try:
        log_message(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        result = None
        update_session_profit()
        while result is None:
            try:
                result = status , resultado = API.check_win_digital_v2(id) if tipo == 'digital' else API.check_win_v4(id)
                if result is None:
                    log_message(f"Negociação {trade_id} ainda não concluída. Tentando novamente em 5 segundos...")
                    time.sleep(5)
            except Exception as e:
                log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")
                time.sleep(5)

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

threading.Thread(target=monitor_trade, daemon=True).start()
# Função para ignorar ativos específicos
def ignore_assets(check_flag):
    if check_flag:
        return ["YAHOO", "TWITTER"]
    return []

# # Função para zerar limite de negociações simultâneas e iniciar checagem de resultados
# def reset_simultaneous_trades():
#     global simultaneous_trades, current_amount, consecutive_losses
#     while True:
#         time.sleep(300)  # 5 minutos
#         logging.info("Zerando limite de negociações simultâneas e iniciando checagem de resultados...")
#         while simultaneous_trades > 0:
#             time.sleep(5)  # Aguarda até que todas as negociações sejam monitoradas
#         check_all_results()

# # Função para reduzir o número de negociações simultâneas após 5 minutos
# def decrease_simultaneous_trades():
#     global simultaneous_trades
#     while True:
#         time.sleep(180)  # 3 minutos
#         if simultaneous_trades > 0:
#             simultaneous_trades -= 1
#             logging.info(f"Reduzindo negociações simultâneas. Atual: {simultaneous_trades}")

# # Função para checar resultados de negociações

# def check_all_results():
#     global consecutive_losses, current_amount
#     try:
#         logging.info("Checando resultados de negociações...")
#         trades = iq.get_positions("closed")  # Atualizado para método correto
#         if not isinstance(trades, list):  # Verifica se trades é uma lista
#             logging.error("Formato inesperado de trades. Verifique a API.")
#             return

#         for trade in trades:
#             if not isinstance(trade, dict):  # Certifique-se de que cada item é um dicionário
#                 logging.error(f"Formato inesperado para trade: {trade}")
#                 continue

#             profit = trade.get('win', 0)  # Usa get para evitar exceções
#             if profit < 0:
#                 consecutive_losses += 1
#                 if consecutive_losses >= martingale_limit:
#                     current_amount = initial_amount
#                     consecutive_losses = 0
#                     logging.info("Limite do Martingale atingido. Reiniciando o valor para o inicial.")
#                 else:
#                     current_amount *= 2
#                     logging.info(f"Aplicando Martingale. Próximo valor: {current_amount}")
#             else:
#                 consecutive_losses = 0
#                 current_amount = initial_amount
#     except Exception as e:
#         logging.error(f"Erro ao checar resultados: {e}")


def update_session_profit():
    """
    Atualiza o lucro da sessão a cada 30 segundos.
    """
    global session_profit  # Certifique-se de que 'session_profit' está definido como global
    while True:
        try:
            # Aqui você pode implementar lógica adicional, se necessário
            profit_label.config(
                text=f"Lucro da Sessão Ativa: R${session_profit:.2f}",
                fg="green" if session_profit >= 0 else "red"
            )
            log_message(f"Lucro da sessão atualizado: ${session_profit:.2f}")
        except Exception as e:
            log_message(f"Erro ao atualizar lucro da sessão: {e}")
        time.sleep(60)
# # Inicializar threads
threading.Thread(target=reconnect, daemon=True).start()
# threading.Thread(target=reset_simultaneous_trades, daemon=True).start()
# threading.Thread(target=decrease_simultaneous_trades, daemon=True).start()

# Exemplo de teste da função on_message
on_message('{"key": "value"}')

# GUI Setup with dark theme
def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=start_trading_loop).start()

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
    profit_label.config(text=f"Session Profit: ${session_profit:.2f}", fg="green" if session_profit >= 0 else "red")

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
root.title("Capybara v2.4")
root.configure(bg="#082429")  # Set dark theme background

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#082429")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

start_button = tk.Button(root, text="Start", command=start_trading, bg="#4CAF50", fg="white", font=("Helvetica", 12))
start_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=2, padx=5, pady=5)

switch_account_button = tk.Button(root, text="Switch Account", command=switch_account_type, bg="#2196F3", fg="white", font=("Helvetica", 12))
switch_account_button.grid(row=0, column=3, padx=5, pady=5)

amount_label = tk.Label(root, text="Initial Amount:", bg="#082429", fg="white", font=("Helvetica", 12))
amount_label.grid(row=1, column=1, padx=5, pady=5)

amount_entry = tk.Entry(root, font=("Helvetica", 12))
amount_entry.insert(0, "2")
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#082429", fg="white")
log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Deus seja louvado!", font=("Helvetica", 16), bg="#082429", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Rodapé
footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - À∴G∴D∴G∴A∴D∴U∴",
    bg="#082429",
    fg="#A9A9A9",
    font=("Helvetica", 5)
)
footer_label.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")

update_log()
root.mainloop()
