from iqoptionapi.stable_api import IQ_Option
import threading
import time
import os
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import PhotoImage
import pandas as pd
import pandas_ta as ta
import json  # Adicionando a importação do módulo json
import logging  # Adicionando módulo de logging

# Configuração básica de logging
logging.basicConfig(level=logging.DEBUG)

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

# Definir o caminho do arquivo de log
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
        # Verifica se a mensagem não está vazia
        if not message:
            logging.warning("Mensagem vazia recebida.")
            return

        # Tenta decodificar a mensagem JSON
        message_json = json.loads(str(message))
        logging.debug(f"Mensagem JSON recebida: {message_json}")

        # Aqui você pode processar a mensagem JSON conforme necessário
        # ...

    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar JSON: {e}")
        logging.error(f"Mensagem recebida: {message}")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")

# Exemplo de uso da função on_message
on_message('{"key": "value"}')  # Mensagem JSON válida
on_message('')  # Mensagem vazia
on_message('not a json')  # Mensagem não JSON

# Inicializar a API IQ Option
account_type = "PRACTICE"  # Conta de demonstração por padrão
instrument_types = ["binary", "crypto", "digital", "otc"]  # Tipos de instrumentos suportados
max_simultaneous_trades = 3
martingale_limit = 5
trade_duration = 5  # Duração padrão do trade em minutos

# Definir variáveis globais
running = False
icon_label = None
initial_amount = 10
current_amount = 10  # Acompanhar o valor atual da negociação para estratégia Martingale
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

def analyze_indicators(asset):
    log_message(f"Analisando indicadores para {asset}...")
    try:
        start_time = time.time()
        data = fetch_historical_data(asset, 1, 100)  # Buscar últimos 100 candles de 1 minuto

        if data.empty:
            log_message(f"Sem dados disponíveis para o ativo {asset}. Pulando análise.")
            return None

        indicators = {}

        # Dicionário de indicadores disponíveis
        available_indicators = {
            "rsi": lambda: ta.rsi(data["close"], length=14),
            "macd": lambda: ta.macd(data["close"])["MACD_12_26_9"],
            "ema": lambda: ta.ema(data["close"], length=9),
            "sma": lambda: ta.sma(data["close"], length=20),
            "stochastic": lambda: ta.stoch(data["high"], data["low"], data["close"])["STOCHk_14_3_3"],
            "atr": lambda: ta.atr(data["high"], data["low"], data["close"], length=14),
            "adx": lambda: ta.adx(data["high"], data["low"], data["close"], length=14),
            "bollinger_high": lambda: ta.bbands(data["close"], length=20, std=2.0)["BBU_20_2.0"],
            "bollinger_low": lambda: ta.bbands(data["close"], length=20, std=2.0)["BBL_20_2.0"],
        }

        # Calcular cada indicador e tratar erros individualmente
        for key, func in available_indicators.items():
            try:
                indicators[key] = func()
            except Exception as e:
                log_message(f"Erro ao calcular {key.upper()} para {asset}: {e}")
                indicators[key] = None

        decisions = []

        # Estratégia baseada nos indicadores calculados
        if indicators.get("rsi") is not None and indicators["rsi"].iloc[-1] < 30:
            decisions.append("buy")
        elif indicators.get("rsi") is not None and indicators["rsi"].iloc[-1] > 70:
            decisions.append("sell")

        if indicators.get("macd") is not None and indicators["macd"].iloc[-1] > 0:
            decisions.append("buy")
        elif indicators.get("macd") is not None and indicators["macd"].iloc[-1] < 0:
            decisions.append("sell")

        if indicators.get("ema") is not None and data["close"].iloc[-1] > indicators["ema"].iloc[-1]:
            decisions.append("buy")
        elif indicators.get("ema") is not None:
            decisions.append("sell")

        if indicators.get("sma") is not None and data["close"].iloc[-1] > indicators["sma"].iloc[-1]:
            decisions.append("buy")
        elif indicators.get("sma") is not None:
            decisions.append("sell")

        if indicators.get("stochastic") is not None and indicators["stochastic"].iloc[-1] < 20:
            decisions.append("buy")
        elif indicators.get("stochastic") is not None and indicators["stochastic"].iloc[-1] > 80:
            decisions.append("sell")

        buy_votes = decisions.count("buy")
        sell_votes = decisions.count("sell")
        total_indicators = len([v for v in indicators.values() if v is not None])

        log_message(f"Votação de indicadores para {asset}: BUY={buy_votes}, SELL={sell_votes}")

        if time.time() - start_time > 10:
            log_message(f"A análise para {asset} excedeu o limite de tempo. Pulando ativo.")
            return None

        if total_indicators == 0:
            log_message(f"Sem indicadores válidos para {asset}. Pulando ativo.")
            return None

        if buy_votes >= 3:
            return "buy"
        elif sell_votes >= 3:
            return "sell"
        else:
            log_message("Consenso insuficiente entre os indicadores. Pulando ativo.")
            return None

    except Exception as e:
        log_message(f"Erro ao analisar indicadores para {asset}: {e}")
        return None

# Adicionado código exemplo para evitar erro de variável não definida
message = "{}"  # Inicializando a variável message como uma string vazia
data = pd.DataFrame()  # Inicializando a variável data como DataFrame vazio
asset = "undefined"  # Inicializando asset como uma string padrão



def execute_trades():
    global running
    global current_amount
    global consecutive_losses
    global session_profit
    global simultaneous_trades

    while running:
        log_message("Executando negociações...")
        assets = fetch_top_assets()

        if not assets:
            log_message("Nenhum ativo encontrado. Parando execução.")
            break

        for asset in assets:
            if simultaneous_trades >= max_simultaneous_trades:
                log_message("Limite máximo de negociações simultâneas atingido. Aguardando...")
                time.sleep(1)
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
                    log_message(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
                    threading.Thread(target=monitor_trade, args=(trade_id, asset)).start()
                else:
                    log_message(f"Falha ao realizar negociação para {asset}.")
            except Exception as e:
                log_message(f"Erro durante a execução da negociação para {asset}: {e}")

# Monitorar execução da negociação e atualizar o status
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
                # Verificar status da negociação
                result = iq.check_win_v3(trade_id)
                if result is None:
                    log_message(f"Negociação {trade_id} ainda não concluída. Verificando novamente em 5 segundos...")
                    time.sleep(5)  # Verificar novamente em 5 segundos
            except Exception as e:
                log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")
                time.sleep(5)

        # Atualizar lucros/perdas
        session_profit += result
        log_message(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")
        update_session_profit()

        # Ajustar lógica Martingale
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
        # Reduzir o contador de negociações simultâneas
        simultaneous_trades -= 1


# Função para obter ativos disponíveis

def fetch_top_assets():
    log_message("Fetching all available assets...")
    reconnect_if_needed()
    if iq is None:
        log_message("IQ Option API is not connected. Cannot fetch assets.")
        return []

    # Lista de ativos a serem ignorados
    ignored_assets = {"yahoo", "twitter"}

    try:
        valid_assets = iq.get_all_ACTIVES_OPCODE()
        log_message(f"Available assets: {valid_assets}")

        # Filtrar ativos válidos, excluindo os indesejados
        filtered_assets = [asset for asset in valid_assets.keys() if asset.lower() not in ignored_assets]
        log_message(f"Filtered assets: {filtered_assets}")
        return filtered_assets
    except Exception as e:
        log_message(f"Error fetching assets: {e}")
        return []

# Verificar minuto a minuto o status das negociações pendentes
def check_pending_trades():
    global simultaneous_trades
    global session_profit
    global consecutive_losses
    global current_amount

    pending_trades = iq.get_pending_orders()

    if pending_trades:
        log_message("Verificando negociações pendentes...")

        for trade_id, trade_data in pending_trades.items():
            try:
                result = iq.check_win_v3(trade_id)

                if result is not None:
                    session_profit += result
                    log_message(f"Resultado da negociação {trade_id}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")

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

                    # Reduzir o contador de negociações simultâneas
                    simultaneous_trades -= 1

            except Exception as e:
                log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")

    else:
        log_message("Não há negociações pendentes.")

    # Continuar verificando trades pendentes a cada 5 segundos
    if running:
        root.after(5000, check_pending_trades)

# Modificar a função de inicialização para incluir a verificação automática das negociações pendentes

def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=execute_trades).start()
        check_pending_trades()  # Iniciar a verificação de negociações pendentes

# Incluir a função para obter negociações pendentes no IQ Option

def fetch_pending_trades():
    log_message("Buscando negociações pendentes...")
    reconnect_if_needed()
    if iq is None:
        log_message("API IQ Option não conectada. Não é possível buscar negociações pendentes.")
        return {}

    try:
        pending_trades = iq.get_pending_orders()
        log_message(f"Negociações pendentes: {pending_trades}")
        return pending_trades
    except Exception as e:
        log_message(f"Erro ao buscar negociações pendentes: {e}")
        return {}


# Adicionar tratamento de exceção ao WebSocket
try:
    message = json.loads(str(message))
except json.JSONDecodeError as e:
    log_message(f"Erro ao decodificar mensagem do WebSocket: {e}. Mensagem recebida: {message}")
    

# Garantir dados antes de prosseguir com os indicadores
if data.empty:
    log_message(f"Sem dados disponíveis para o ativo {asset}. Pulando análise.")
    
def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=execute_trades).start()
        check_pending_trades()  # Iniciar verificação de negociações pendentes


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
        log_message(f"Failed to switch account type. Current type remains as {'Demo' if previous_account == 'PRACTICE' else 'Real'}")


# Adicionar controle de tempo
restart_interval = 5 * 60  # 5 minutos em segundos
def periodic_restart():
    global running
    if running:
        stop_trading()  # Para a negociação
        log_message("Trading pausado para reinício periódico.")
        time.sleep(10)  # Pausa de 10 segundos (ou ajuste conforme necessário)
        start_trading()  # Reinicia a negociação
    threading.Timer(restart_interval, periodic_restart).start()  # Reagendar o reinício periódico


# Funções de controle de trading
def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Iniciando sessão de negociação...")
        threading.Thread(target=execute_trades).start()
        check_pending_trades()  # Iniciar verificação de negociações pendentes
        
# GUI Configuration
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Capybara")
    root.configure(bg="#2E2E2E")  # Set dark theme background

    static_icon = PhotoImage(file="static_icon.png")
    rotating_icon = PhotoImage(file="working_capy.png")
    icon_label = tk.Label(root, image=static_icon, bg="#2E2E2E")
    icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

    start_button = tk.Button(root, text="Start", command=start_trading, bg="#4CAF50", fg="white", font=("Helvetica", 12))
    start_button.grid(row=0, column=1, padx=5, pady=5)

    stop_button = tk.Button(root, text="Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
    stop_button.grid(row=0, column=2, padx=5, pady=5)

    switch_account_button = tk.Button(root, text="Switch Account", command=switch_account_type, bg="#2196F3", fg="white", font=("Helvetica", 12))
    switch_account_button.grid(row=0, column=3, padx=5, pady=5)

    amount_label = tk.Label(root, text="Initial Amount:", bg="#2E2E2E", fg="white", font=("Helvetica", 12))
    amount_label.grid(row=1, column=1, padx=5, pady=5)

    amount_entry = tk.Entry(root, font=("Helvetica", 12))
    amount_entry.insert(0, "10")
    amount_entry.grid(row=1, column=2, padx=5, pady=5)

    set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
    set_button.grid(row=1, column=3, padx=5, pady=5)

    log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#1C1C1C", fg="white")
    log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

    profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#2E2E2E", fg="white")
    profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

    update_log()
    root.mainloop()
