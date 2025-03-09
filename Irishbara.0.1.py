#!/usr/bin/env python
# Arquivo: Capybara.8.4.py
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
import numpy as np
import json
import logging
from xgboost import XGBClassifier
from sklearn.metrics import f1_score
import joblib
import sys
from pyti.relative_strength_index import relative_strength_index as pyti_rsi
from pyti.moving_average_convergence_divergence import moving_average_convergence_divergence as pyti_macd
from pyti.simple_moving_average import simple_moving_average as pyti_sma
from pyti.exponential_moving_average import exponential_moving_average as pyti_ema
from pyti.bollinger_bands import percent_b as pyti_bollinger
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier
import random



def predict_trade_direction(asset):
    decision = 'buy' if random.random() < 0.5 else 'sell'
    log_message(f"Decisão aleatória para {asset}: {decision}")
    return decision

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
credentials_file = os.path.normpath(os.path.join(os.getcwd(), "credentials3.txt"))

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
max_simultaneous_trades = 1

# Define preset trade value
auto_initial_amount = 2
smart_stop = False

def update_balance():
    if iq is not None:
        balance = iq.get_balance()
        balance_label.config(text=f"Balance: R${balance:.2f}")
        log_message(f"Balance updated: R${balance:.2f}")
    root.after(60000, update_balance)  # Schedule the function to run every minute
    
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
    logging.info("Buscando e classificando ativos por lucratividade e volume para negociações de 5 minutos...")
    reconnect_if_needed()

    if iq is None:
        logging.info("API desconectada. Não é possível buscar ativos.")
        return []

    try:
        assets = iq.get_all_ACTIVES_OPCODE()
        raw_profitability = iq.get_all_profit()
        

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
        )[:30]  # Return top 10 assets

        log_message(f"Ativos classificados por lucratividade e volume para negociações de 5 minutos: {sorted_assets[:100]}")
        return sorted_assets[:30]  # Return top 10 assets
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




# Função de contagem regressiva
def countdown(seconds):
    while seconds > 0:
        log_message(f"Aguardando {seconds} segundos...")
        time.sleep(1)
        seconds -= 1


# Função principal de execução de trades
def execute_trades():
    global running, current_amount, consecutive_losses, session_profit, simultaneous_trades, saldo_entrada
    while running:
        reconnect_if_needed()
        if iq is None or not iq.check_connect():
            log_message("Erro: API desconectada. Tentando reconectar em 10 segundos...")
            time.sleep(10)
            continue

        # Se já houve perdas consecutivas (modo martingale), busca os melhores ativos para o trade
        if consecutive_losses > 0:
            best_assets = fetch_sorted_assets()
            if best_assets:
                asset_list = [best_assets[0]]
                log_message(f"Modo martingale: selecionado o melhor ativo {best_assets[0]}")
            else:
                log_message("Nenhum ativo classificado disponível para martingale. Aguardando...")
                time.sleep(10)
                continue
        else:
            asset_list = list(iq.get_all_ACTIVES_OPCODE().keys())
            if not asset_list:
                log_message("Nenhum ativo encontrado. Tentando novamente em 10 segundos...")
                time.sleep(10)
                continue

        for asset in asset_list:
            if not running:
                log_message("Execução de negociações interrompida.")
                break

            # Limita a execução a uma única transação simultânea
            if simultaneous_trades >= max_simultaneous_trades:
                log_message("Uma transação já está em andamento. Aguardando a finalização da transação atual...")
                time.sleep(1)
                continue

            reconnect_if_needed()
            if iq is None or not iq.check_connect():
                log_message("API desconectada. Pulando ativo.")
                continue

            decision = predict_trade_direction(asset)
            if not decision:
                log_message(f"Pulando negociação para {asset}. Sem decisão clara.")
                continue

            action = "call" if decision == "buy" else "put"

            if iq is None or not iq.check_connect():
                log_message("API desconectada antes de abrir a negociação. Tentando reconectar...")
                reconnect_if_needed()
                if iq is None or not iq.check_connect():
                    log_message("Falha na reconexão. Pulando ativo.")
                    continue

            saldo_entrada = iq.get_balance()
            log_message(f"Saldo antes da negociação: R${saldo_entrada}")
            available_assets = iq.get_all_ACTIVES_OPCODE()
            if asset not in available_assets:
                log_message(f"Ativo {asset} não encontrado na plataforma. Pulando ativo.")
                continue

            try:
                # Duração do trade definida para 1 minuto
                success, trade_id = iq.buy(current_amount, asset, action, 5)
                if success:
                    simultaneous_trades += 1
                    trade_list.append(trade_id)
                    log_message(f"Negociação realizada com sucesso para {asset}. ID da negociação={trade_id}")
                    log_message(f"Saldo após abertura da negociação: R${iq.get_balance()}")
                    threading.Thread(target=monitor_trade, args=(trade_id, asset)).start()
                else:
                    log_message(f"Falha ao realizar negociação para {asset}. Motivo: {trade_id}")
            except Exception as e:
                log_message(f"Erro durante a execução da negociação para {asset}: {e}")
                reconnect_if_needed()
                if iq is None or not iq.check_connect():
                    log_message("Falha na reconexão. Parando operações.")
                    running = False
                    break

        log_message("Todos os ativos processados. Buscando nova lista de ativos...")
       
        update_balance()
        time.sleep(5)

    

# Monitora uma negociação e aplica a estratégia de Martingale
def monitor_trade(trade_id, asset):
    global simultaneous_trades, session_profit, consecutive_losses, current_amount, saldo_saida, initial_amount, trade_list
    try:
        log_message(f"Monitorando negociação {trade_id} para o ativo {asset}...")
        countdown(60)  # Aguarda o tempo da negociação (60 segundos)
        result = None
        while result is None:
            try:
                result = iq.check_win_v4(trade_id)
                if result is None:
                    log_message(f"Negociação {trade_id} ainda não concluída. Tentando novamente em 1 segundo...")
                    time.sleep(1)
            except Exception as e:
                log_message(f"Erro ao verificar status da negociação {trade_id}: {e}")
                time.sleep(1)

        if isinstance(result, tuple):
            result = result[0]
        if isinstance(result, str):
            if result.lower() == "win":
                result = 1.0
            elif result.lower() == "loose":
                result = -1.0
            else:
                try:
                    result = float(result)
                except ValueError:
                    log_message(f"Erro ao converter resultado para float: {result}")
                    result = 0.0

        session_profit += result
        saldo_saida = iq.get_balance()
        update_balance()
        log_message(f"Resultado da negociação para {asset}: {'Vitória' if result > 0 else 'Perda'}, Lucro={result}")

        # Lógica do Martingale:
        if result <= 0:
            consecutive_losses += 1
            if consecutive_losses >= martingale_limit:
                log_message("Limite de martingale atingido. Resetando para o valor inicial e aguardando 5 minutos.")
                consecutive_losses = 0
                current_amount = initial_amount
                time.sleep(300)
            else:
                current_amount *= 2.1
                log_message(f"Perda consecutiva #{consecutive_losses}. Novo valor da aposta: R${current_amount}")
        else:
            log_message("Negociação bem-sucedida. Resetando valor de negociação para o inicial.")
            consecutive_losses = 0
            current_amount = initial_amount
    finally:
        simultaneous_trades -= 1
        if trade_id in trade_list:
            trade_list.remove(trade_id)
        log_message(f"Saldo após fechamento da negociação: R${iq.get_balance():.2f}")


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

# Define o valor inicial do trade com base no saldo
def set_amount():
    global initial_amount, current_amount
    balance = iq.get_balance()
    initial_amount = balance * 0.02  # 2% do saldo; ajuste conforme necessário
    current_amount = initial_amount
    log_message(f"Valor inicial definido: R${initial_amount:.2f}")

# Function to update the Martingale label
def update_martingale_label():
    if current_amount > initial_amount:
        martingale_label.config(text="M", fg="red")
    else:
        martingale_label.config(text="M", fg="#084d18")  # Same color as the background

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
root.title(f"IrishBara v0.1 - Full Aleatório - Conta: {account_type} - {email}")
root.configure(bg="#084d18")

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#084d18")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

stop_button = tk.Button(root, text="Smart Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=1, padx=5, pady=5)

balance_label = tk.Label(root, text="Balance: R$0.00", bg="#084d18", fg="white", font=("Helvetica", 12))
balance_label.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

# Add Martingale label
martingale_label = tk.Label(root, text="M", bg="#084d18", fg="#084d18", font=("Helvetica", 12))
martingale_label.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#084d18", fg="white")
log_text.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Redirect stdout and stderr to the log_text widget
sys.stdout = TextRedirector(log_text, "stdout")
sys.stderr = TextRedirector(log_text, "stderr")

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#084d18", fg="white")
profit_label.grid(row=4, column=0, columnspan=5, padx=10, pady=10)

footer_label = tk.Label(
    root,
     text="@oedlopes - 2025  - Deus Seja Louvado - Sola Scriptura - Sola Fide - Solus Christus - Sola Gratia - Soli Deo Gloria",
    bg="#084d18",
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
        if consecutive_losses < martingale_limit and not amount_doubled:
            current_amount *= 2  # Dobrar apenas uma vez
            amount_doubled = True
        else:
            log_message("Martingale limit reached or amount already doubled. Resetting to initial amount.")
            consecutive_losses = 0
            current_amount = initial_amount
            amount_doubled = False



# Configuração da GUI
root = tk.Tk()
root.title("Capybara v7.7")
root.configure(bg="#084d18")


static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#084d18")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

start_button = tk.Button(root, text="Start", command=start_trading, bg="#4CAF50", fg="white", font=("Helvetica", 12))
start_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=2, padx=5, pady=5)

amount_label = tk.Label(root, text="Initial Amount:", bg="#084d18", fg="white", font=("Helvetica", 12))
amount_label.grid(row=1, column=1, padx=5, pady=5)

amount_entry = tk.Entry(root, font=("Helvetica", 12))
amount_entry.insert(0, "2")
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#084d18", fg="white")
log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#084d18", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

# Rodapé
footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - Deus seja louvado",
    bg="#084d18",
    fg="#A9A9A9",
    font=("Helvetica", 8)
)
footer_label.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")

update_log()

invalid_credentials = False

if invalid_credentials:
    log_text.insert(tk.END, "Invalid credentials. Please check the credentials.txt file.\n")

root.mainloop()

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



# Ensure balance is fetched and initial amount is set at the start
connect_to_iq_option(email, password)
set_amount()
update_balance()  # Start the periodic balance update








































