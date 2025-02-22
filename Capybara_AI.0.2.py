#!/usr/bin/env python
# Arquivo: Capybara.7.7.py
# PECUNIA IMPROMPTA
# Código construido com Copilot e otimizado utilizando DeepSeek, o ChatGPT de flango.

import os
import sys
import time
import json
import logging
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import pandas as pd
import numpy as np
from iqoptionapi.stable_api import IQ_Option
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
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
from model_management import load_model, save_model
from Mach_Learning import preprocess_new_data, train_model

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define file paths
credentials_file = os.path.normpath(os.path.join(os.getcwd(), "credentials.txt"))
log_file = os.path.normpath(os.path.join(os.getcwd(), f"trade_log_{time.strftime('%Y-%m-%d')}.txt"))
model_file = "IA/capybara-ai-project/models/trained_model.pkl"

# Load credentials
def load_credentials():
    try:
        with open(credentials_file, "r") as file:
            lines = file.readlines()
            creds = {line.split('=')[0].strip(): line.split('=')[1].strip() for line in lines if '=' in line}
            return creds.get("email"), creds.get("password")
    except FileNotFoundError:
        raise Exception("Arquivo de credenciais não encontrado. Certifique-se de que 'credentials.txt' está no diretório de trabalho.")

email, password = load_credentials()

# Initialize global variables
running = False
initial_amount = 2
current_amount = initial_amount
max_simultaneous_trades = 3
simultaneous_trades = 0
consecutive_losses = 0
session_profit = 0
iq = None
trade_list = []
amount_doubled = False
smart_stop = False

# Connect to IQ Option API
def connect_to_iq_option(email, password):
    global iq
    log_message("Tentando conectar à API IQ Option...")
    iq = IQ_Option(email, password)
    try:
        check, reason = iq.connect()
        if check:
            iq.change_balance("PRACTICE")  # Alternar entre 'PRACTICE' e 'REAL'
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

# Log message function
def log_message(message):
    try:
        with open(log_file, "a") as file:
            file.write(message + "\n")
    except FileNotFoundError:
        with open(log_file, "w") as file:
            file.write(message + "\n")
    logging.info(message)
    print(message)  # Ensure message is printed to the redirected stdout

# Update balance function
def update_balance():
    if iq is not None:
        balance = iq.get_balance()
        balance_label.config(text=f"Balance: R${balance:.2f}")
        log_message(f"Balance updated: R${balance:.2f}")
    root.after(60000, update_balance)  # Schedule the function to run every minute

# Set initial amount function
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

# Start trading function
def start_trading():
    global running
    if not running:
        running = True
        icon_label.config(image=rotating_icon)
        log_message("Starting trading session...")
        threading.Thread(target=execute_trades).start()

# Stop trading function
def stop_trading():
    global running
    global smart_stop
    smart_stop = True
    running = False
    if 'static_icon' in globals():
        icon_label.config(image=static_icon)
    log_message("Smart Stop ativado. Parando execução após reset para valor inicial.")

# GUI Configuration
root = tk.Tk()
root.title(f"Capybara AI v0.2 - Conta: PRACTICE - {email}")
root.configure(bg="#000000")

static_icon = tk.PhotoImage(file="static_icon.png")
rotating_icon = tk.PhotoImage(file="working_capy.png")
icon_label = tk.Label(root, image=static_icon, bg="#000000")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

stop_button = tk.Button(root, text="Smart Stop", command=stop_trading, bg="#F44336", fg="white", font=("Helvetica", 12))
stop_button.grid(row=0, column=1, padx=5, pady=5)

balance_label = tk.Label(root, text="Balance: R$0.00", bg="#000000", fg="white", font=("Helvetica", 12))
balance_label.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

martingale_label = tk.Label(root, text="M", bg="#000000", fg="#000000", font=("Helvetica", 12))
martingale_label.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#000000", fg="white")
log_text.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

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

# Redirect stdout and stderr to the log_text widget
class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.insert(tk.END, str, (self.tag,))
        self.widget.see(tk.END)

    def flush(self):
        pass

sys.stdout = TextRedirector(log_text, "stdout")
sys.stderr = TextRedirector(log_text, "stderr")

# Ensure balance is fetched and initial amount is set at the start
connect_to_iq_option(email, password)
set_amount()
update_balance()  # Start the periodic balance update

root.mainloop()
