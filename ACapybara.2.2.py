# Arquivo: ACapybara.2.2.py
from iqoptionapi.stable_api import IQ_Option
import threading
import time
import os
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import PhotoImage
from tkinter import *
import pandas as pd
import pandas_ta as ta
import json
import logging
from martingalemanager import MartingaleManager
# Carregar credenciais do arquivo
credentials_file = os.path.normpath(os.path.join(os.getcwd(), "credentials.txt"))
# No início do código principal, após as importações
martingale_manager = MartingaleManager(initial_amount=2, martingale_limit=5)
class ThreadManager:
    def __init__(self):
        self.assets = ["EURUSD", "USDJPY"]  # Exemplo de lista de ativos
        self.actions = ["buy", "sell"]

    def start_ignore_assets_thread(self):
        for asset in self.assets:
            threading.Thread(target=ignore_assets, args=(asset,), daemon=True).start()

    def start_analyze_indicators_thread(self):
        for asset in self.assets:
            threading.Thread(target=analyze_indicators, args=(asset,), daemon=True).start()

    def start_execute_trade_thread(self):
        for asset in self.assets:
            for action in self.actions:
                threading.Thread(target=execute_trade, args=(asset, action), daemon=True).start()

def update_timer():
    if running:
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(int(elapsed_time), 60)
        timer_label.config(text=f"{minutes:02}:{seconds:02}")
        root.after(1000, update_timer)

def log_message(message):
    try:
        with open(log_file, "a") as file:
            file.write(message + "\n")
    except FileNotFoundError:
        with open(log_file, "w") as file:
            file.write(message + "\n")
    print(message)

def process_message(message):
    try:
        if not message.strip():  # Verifica se a mensagem é vazia
            logging.warning("Mensagem vazia recebida.")
            return None
        data = json.loads(message)  # Tenta decodificar o JSON
        return data
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar JSON: {e}")
        logging.error(f"Mensagem recebida: {message}")
        return None

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



# Função para tratar mensagens recebidas
def on_message(message):
    try:
        if not message:
            logging.warning("Mensagem vazia recebida.")
            return

        message_json = json.loads(str(message))
        logging.debug(f"Mensagem JSON recebida: {message_json}")

    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar JSON: {e}")
        logging.error(f"Mensagem recebida: {message}")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")

# Exemplo de uso da função on_message
on_message('{"key": "value"}')
on_message('')
on_message('not a json')


# Inicializar a API IQ Option
account_type = "REAL"  # Alterado para conta REAL
instrument_types = ["binary", "crypto", "digital", "otc"]  # Tipos de instrumentos suportados

# Definir variáveis globais
running = False
icon_label = None
initial_amount = 2
current_amount = 2  # Acompanhar o valor atual da negociação para estratégia Martingale
max_simultaneous_trades = 3
simultaneous_trades = 0
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
    log_message("Buscando e classificando ativos por volume e lucratividade...")
    reconnect_if_needed()
    
    if iq is None:
        log_message("API desconectada. Não é possível buscar ativos.")
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
            "bollinger_high": lambda: ta.bbands(data["close"])["BBU_20_2.0"],
            "bollinger_low": lambda: ta.bbands(data["close"])["BBL_20_2.0"],
            "cci": lambda: ta.cci(data["high"], data["low"], data["close"], length=20),
            "willr": lambda: ta.willr(data["high"], data["low"], data["close"], length=14),
            "roc": lambda: ta.roc(data["close"], length=12),
            "obv": lambda: ta.obv(data["close"], data["volume"]),
            "trix": lambda: ta.trix(data["close"], length=15),
            "vwma": lambda: ta.vwma(data["close"], data["volume"], length=20),
            "mfi": lambda: ta.mfi(data["high"], data["low"], data["close"], data["volume"], length=14),
            "dpo": lambda: ta.dpo(data["close"], length=14),
            "keltner_upper": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCUp_20_2.0"],
            "keltner_lower": lambda: ta.kc(data["high"], data["low"], data["close"], length=20)["KCLo_20_2.0"],
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

def execute_trade_with_retry(api, asset, action, value, retries=2):
    """
    Tenta realizar uma negociação com número especificado de tentativas em caso de falha.
    
    :param api: Instância da API para realizar o trade.
    :param asset: Ativo no qual realizar a negociação.
    :param action: Tipo de ação (call/put).
    :param value: Valor a ser negociado.
    :param retries: Número de tentativas em caso de falha.
    """
    for attempt in range(retries):
        try:
            trade_result = api.trade(asset, action, value)
            if trade_result:
                print(f"Trade realizado com sucesso no ativo {asset} ({action}) com valor ${value}.")
                return trade_result
            else:
                raise Exception("Trade falhou sem razão especificada pela API.")
        except Exception as e:
            print(f"Tentativa {attempt + 1} de negociação falhou: {e}")
            if attempt < retries - 1:
                print("Tentando novamente...")
            else:
                print(f"Falha final ao realizar negociação no ativo {asset} após {retries} tentativas.")
    return None

def update_martingale_logic(api, asset, action, base_value, max_attempts=3):
    """
    Implementa a estratégia de Martingale em caso de operações perdedoras.
    
    :param api: Instância da API para realizar o trade.
    :param asset: Ativo no qual realizar a negociação.
    :param action: Tipo de ação (call/put).
    :param base_value: Valor base para o primeiro trade.
    :param max_attempts: Máximo de tentativas de Martingale.
    """
    value = base_value
    for attempt in range(max_attempts):
        result = execute_trade_with_retry(api, asset, action, value)
        if result and result["status"] == "win":
            print(f"Martingale concluído com sucesso no ativo {asset} após {attempt + 1} tentativa(s).")
            break
        elif result and result["status"] == "lose":
            value *= 2  # Dobra o valor para Martingale
            print(f"Negociação perdida no ativo {asset}. Tentando Martingale com novo valor ${value}.")
        else:
            print("Erro desconhecido ou resultado inválido. Encerrando Martingale.")
            break
    else:
        print(f"Martingale falhou após {max_attempts} tentativas para o ativo {asset}.")


#Execução de trades

def execute_trade(self, asset, action):
    
    global running
    global current_amount
    global consecutive_losses
    global session_profit
    global simultaneous_trades
    
    global session_profit, current_amount, consecutive_losses

    try:
        # Obter o valor atual do MartingaleManager
        trade_amount = martingale_manager.get_current_amount()
        log_message(f"Executando trade: Ativo={asset}, Ação={action}, Valor={trade_amount}")

        # Executar a negociação
        success, trade_id = iq.place_trade(asset, action, trade_amount, duration=5)

        if success:
            # Verificar o resultado da negociação
            result = iq.check_trade_result(trade_id)
            if result:
                session_profit += result["amount"]
                # Atualizar o MartingaleManager com o resultado
                martingale_manager.update_on_result(result)
            return result
        else:
            log_message("Falha ao executar trade.")
            return None

    except Exception as e:
        log_message(f"Erro durante a negociação para {asset}: {e}")
        return None



# Atualização da função monitor_trade

def monitor_trade(trade_id, asset):
    """
    Monitora o resultado de uma negociação e ajusta os valores globais de acordo.
    """
    global session_profit
    global consecutive_losses
    global current_amount

    try:
        log_message(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        result = None
        while result is None:
            try:
                result = iq.check_win_v3(trade_id)
                if result is None:
                    log_message(f"Negociação {trade_id} ainda não concluída. Tentando novamente em 5 segundos...")
                    time.sleep(5)
            except Exception as e:
                log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")
                time.sleep(5)

        # Atualizar lucro e lógica de Martingale
        session_profit += result
        log_message(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")

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
        log_message(f"Monitoramento da negociação {trade_id} concluído para o ativo {asset}.")


def ignore_assets(asset):
    """
    Verifica se o ativo deve ser ignorado com base na lista de ativos proibidos.

    :param asset: Nome do ativo (string) a ser verificado.
    :return: Booleano indicando se o ativo deve ser ignorado.
    """
    assets_to_ignore = ["YAHOO", "TWITTER"]  # Lista de ativos a ignorar
    if asset.upper() in assets_to_ignore:
        log_message(f"Ativo ignorado: {asset}")
        return True
    else:
        log_message(f"Ativo permitido: {asset}")
        return False



# Função para zerar limite de negociações simultâneas e iniciar checagem de resultados
# def reset_simultaneous_trades():
#     global simultaneous_trades, current_amount, consecutive_losses
#     while True:
#         time.sleep(60)  # 1 minuto
#         logging.info("Zerando limite de negociações simultâneas e iniciando checagem de resultados...")
#         while simultaneous_trades > 0:
#             time.sleep(5)  # Aguarda até que todas as negociações sejam monitoradas
#         check_all_results()

# # Função para reduzir o número de negociações simultâneas após 5 minutos
# def decrease_simultaneous_trades():
#     global simultaneous_trades
#     while True:
#         time.sleep(90)  # 1.5 minuto
#         if simultaneous_trades > 0:
#             simultaneous_trades -= 1
#             logging.info(f"Reduzindo negociações simultâneas. Atual: {simultaneous_trades}")

# Função para checar resultados de negociações
def check_all_results():
    global consecutive_losses, current_amount
    trades = iq.get_closed_positions()
    for trade in trades:
        profit = trade['win']  # Supondo que 'win' contenha o lucro da negociação
        threading.Thread(target=update_session_profit, daemon=True).start()
        if profit < 0:
            current_amount *= 2
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

class TradingLogic:
    def __init__(self, api):
        self.api = api
        self.current_amount = 2  # Valor inicial
        self.session_profit = 0
        self.consecutive_losses = 0

    def execute_trade(self, asset, action):
        """
        Executa uma negociacao para um ativo especifico.

        :param asset: Nome do ativo (string) a ser negociado.
        :param action: Tipo de acao ("buy" ou "sell").
        """
        try:
            trade_amount = self.current_amount
            log_message(f"Executando trade: Ativo={asset}, Ação={action}, Valor={trade_amount}")
            success, trade_id = self.api.place_trade(asset, action, trade_amount, duration=5)

            if success:
                result = self.api.check_trade_result(trade_id)
                if result:
                    self.session_profit += result["amount"]
                    update_martingale_logic(result)
                return result
            else:
                log_message("Falha ao executar trade.")
                return None

        except Exception as e:
            log_message(f"Erro durante a negociacao para {asset}: {e}")
            return None
        
def start_ignore_assets():
    asset = ignore_assets()  # Função que determina o ativo
    threading.Thread(target=ignore_assets, args=(asset,), daemon=True).start()

def start_analyze_indicators():
    asset = fetch_sorted_assets()  # Função que determina o ativo
    threading.Thread(target=analyze_indicators, args=(asset,), daemon=True).start()

def start_execute_trade():
    asset, action = TradingLogic()  # Função que retorna ativo e ação
    threading.Thread(target=execute_trade, args=(asset, action), daemon=True).start()

# Iniciar a thread de reconexão
threading.Thread(target=execute_trade, daemon=True).start()
threading.Thread(target=reconnect, daemon=True).start()
threading.Thread(target=ignore_assets, daemon=True).start()
threading.Thread(target=analyze_indicators, daemon=True).start()

manager = ThreadManager()
manager.start_ignore_assets_thread()
manager.start_analyze_indicators_thread()
manager.start_execute_trade_thread()

# martingale_manager.py

import logging
import threading

class MartingaleManager:
    """
    Gerencia a lógica do Martingale, monitorando negociações em paralelo.
    """
    def __init__(self, initial_amount, martingale_limit=5):
        self.initial_amount = initial_amount
        self.current_amount = initial_amount
        self.martingale_limit = martingale_limit
        self.consecutive_losses = 0
        self.lock = threading.Lock()  # Garantir thread safety

    def update_on_result(self, result):
        """
        Atualiza os valores com base no resultado da negociação.
        :param result: Dicionário com status ("win" ou "loss") e amount do resultado.
        """
        with self.lock:
            if result.get("status") == "win":
                logging.info(f"Vitória! Restaurando valor inicial: {self.initial_amount}")
                self.current_amount = self.initial_amount
                self.consecutive_losses = 0
            elif result.get("status") == "loss":
                self.consecutive_losses += 1
                if self.consecutive_losses <= self.martingale_limit:
                    self.current_amount *= 2
                    logging.warning(f"Derrota. Aplicando Martingale. Novo valor: {self.current_amount}")
                else:
                    logging.error("Limite de Martingale atingido. Resetando valores.")
                    self.current_amount = self.initial_amount
                    self.consecutive_losses = 0

    def get_current_amount(self):
        """
        Retorna o valor atual de negociação.
        """
        with self.lock:
            return self.current_amount

def start_trading_loop():
    """
    Função que será executada a cada 10 minutos para monitorar trades e executar o módulo de martingale.
    """
    while True:
        try:
            log_message("Iniciando monitoramento e execução de trades...")

            # Exemplo de chamada às funções de trading
            trading_logic = TradingLogic(iq)  # iq é a instância da API já conectada
            sorted_assets = fetch_sorted_assets()

            for asset in sorted_assets:
                if not ignore_assets(asset):
                    decision = analyze_indicators(asset)
                    if decision:
                        trading_logic.execute_trade(asset, decision)

            log_message("Ciclo de monitoramento concluído.")
        except Exception as e:
            log_message(f"Erro no loop de monitoramento: {e}")

        # Espera 10 minutos antes de reiniciar o loop
        time.sleep(600)

# Inicializa a thread
trading_thread = threading.Thread(target=start_trading_loop, daemon=True)
trading_thread.start()

log_message("Thread de monitoramento iniciada.")


# threading.Thread(target=reset_simultaneous_trades, daemon=True).start()
# threading.Thread(target=decrease_simultaneous_trades, daemon=True).start()


# GUI Setup with dark theme
def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=execute_trade).start()

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
root.title("Capybara v2.2")
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

profit_label = tk.Label(root, text="Session Profit: $0.00", font=("Helvetica", 16), bg="#082429", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Rodapé
footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - À∴G∴D∴G∴A∴D∴U∴",
    bg="#082429",
    fg="#A9A9A9",
    font=("Helvetica", 8)
)
footer_label.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")

update_log()
root.mainloop()
