from iqoptionapi.stable_api import IQ_Option
import threading
import time
import os
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import PhotoImage
from MGM_ import MartingaleManager

# Load credentials from file
credentials_file = os.path.normpath(os.path.join(os.getcwd(), "credentials.txt"))

def load_credentials():
    try:
        with open(credentials_file, "r") as file:
            lines = file.readlines()
            creds = {line.split('=')[0].strip(): line.split('=')[1].strip() for line in lines if '=' in line}
            return creds.get("email"), creds.get("password")
    except FileNotFoundError:
        raise Exception("Credentials file not found. Please ensure 'credentials.txt' is in the working directory.")

# Load credentials
email, password = load_credentials()

# Define log file path
log_file = os.path.normpath(os.path.join(os.getcwd(), "trade_log.txt"))

def log_message(message):
    try:
        with open(log_file, "a") as file:
            file.write(message + "\n")
    except FileNotFoundError:
        with open(log_file, "w") as file:
            file.write(message + "\n")
    print(message)

# Initialize IQ Option API
account_type = "REAL"  # Default to demo account
instrument_types = ["binary", "crypto", "digital", "otc"]  # Supported instruments

# Define global variables
running = False
icon_label = None
initial_amount = 2
current_amount = 2  # Track the current trade amount for Martingale strategy
max_simultaneous_trades = 3  # Allow up to 3 trades simultaneously
martingale_limit = 5  # Limit the number of consecutive Martingale steps
consecutive_losses = 0
session_profit = 0
profit_label = 0

iq = None  # Placeholder for the IQ Option API instance

# Connect to IQ Option API
def connect_to_iq_option(email, password):
    global iq
    log_message("Attempting to connect to IQ Option API...")
    iq = IQ_Option(email, password)
    check, reason = iq.connect()
    if check:
        iq.change_balance(account_type)  # Switch between 'PRACTICE' and 'REAL'
        log_message("Successfully connected to IQ Option API.")
    else:
        log_message(f"Failed to connect to IQ Option API: {reason}")
        iq = None  # Ensure iq is None if the connection fails
    return check, reason




def reconnect_if_needed():
    log_message("Checking IQ Option API connection status...")
    if iq is None or not iq.check_connect():
        log_message("Reconnecting to IQ Option API...")
        connect_to_iq_option(email, password)

def buy_on_iq_option(amount, asset, action, duration):
    log_message(f"Placing trade: Asset={asset}, Action={action}, Amount={amount}, Duration={duration}")
    for _ in range(3):  # Retry logic
        try:
            success, trade_id = iq.buy(amount, asset, action, duration)
            if success:
                return success, trade_id
            log_message(f"Trade attempt failed for {asset}. Retrying...")
        except Exception as e:
            log_message(f"Error during trade attempt for {asset}: {e}")
        time.sleep(2)  # Small delay before retry
    return False, None

def check_win_v3(trade_id):
    log_message(f"Checking trade result for Trade ID: {trade_id}")
    return iq.check_win_v3(trade_id)
    

# Analyze indicators manually

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
            "bollinger_high": lambda: ta.bbands(data["close"])["BBU_20_2.5"],
            "bollinger_low": lambda: ta.bbands(data["close"])["BBL_20_2.5"],
            "cci": lambda: ta.cci(data["high"], data["low"], data["close"], length=20),
            "willr": lambda: ta.willr(data["high"], data["low"], data["close"], length=14),
            "roc": lambda: ta.roc(data["close"], length=12),
            "obv": lambda: ta.obv(data["close"], data["volume"]),
            "trix": lambda: ta.trix(data["close"], length=15),
            "vwma": lambda: ta.vwma(data["close"], data["volume"], length=20),
            "mfi": lambda: ta.mfi(data["high"].astype(float), data["low"].astype(float), data["close"].astype(float), data["volume"].fillna(0).astype(float), length=14),
            "dpo": lambda: ta.dpo(data["close"], length=14),
            "keltner_upper": lambda: ta.kc(data["high"].astype(float), data["low"].astype(float), data["close"].astype(float), length=20)["KCUp_20_2.5"],
            "keltner_lower": lambda: ta.kc(data["high"].astype(float), data["low"].astype(float), data["close"].astype(float), length=20)["KCLo_20_2.5"],
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


# Fetch the most profitable asset
def fetch_top_asset():
    log_message("Fetching the most profitable asset...")
    reconnect_if_needed()
    if iq is None:
        log_message("IQ Option API is not connected. Cannot fetch assets.")
        return None

    all_assets = {}
    try:
        valid_assets = iq.get_all_ACTIVES_OPCODE()
        log_message(f"Valid assets: {valid_assets}")

        for instrument in instrument_types:
            try:
                assets = iq.get_all_open_time()[instrument]
                log_message(f"Assets for {instrument}: {assets}")
                if assets:
                    for asset, details in assets.items():
                        if details.get("open") and asset in valid_assets:
                            all_assets[asset] = details.get("volume", 0)
            except Exception as e:
                log_message(f"Error fetching assets for {instrument}: {e}")
                continue
    except Exception as e:
        log_message(f"Error fetching assets: {e}")
        return None

    if not all_assets:
        log_message("No available assets for trading.")
        running = False
        return None

    top_asset = max(all_assets.items(), key=lambda x: float(x[1]) if x[1] else 0)
    log_message(f"Top asset: {top_asset}")
    return top_asset

# Execute trades continuously for the most profitable asset
def execute_trades():
    global current_amount
    global running
    global consecutive_losses

    while running:
        log_message("Executing trades...")
        top_asset = fetch_top_asset()
        if not top_asset:
            log_message("No top asset found. Stopping execution.")
            break

        asset, _ = top_asset
        threading.Thread(target=MartingaleManager.update_on_result, args=(asset, current_amount)).start()

        time.sleep(2)

def monitor_and_analyze_trade(asset, amount):
    global current_amount
    global initial_amount
    global running
    global consecutive_losses

    decision = analyze_indicators(asset)
    action = "call" if decision == "buy" else "put"
    log_message(f"Attempting to place trade: Asset={asset}, Action={action}, Amount={amount}, Duration=5")

    try:
        success, trade_id = buy_on_iq_option(amount, asset, action, 5)
        if success:
            log_message(f"Trade executed for {asset}: {decision.upper()} with trade ID {trade_id}")
            time.sleep(300)  # Wait for trade to complete
            result = check_win_v3(trade_id)
            log_message(f"Trade result for {trade_id}: {result}")

            if result < 0:
                consecutive_losses += 1
                log_message(f"Trade for {asset} lost. Consecutive losses: {consecutive_losses}")
                if consecutive_losses >= martingale_limit:
                    log_message("Martingale limit reached. Resetting amount to initial value.")
                    current_amount = initial_amount
                    consecutive_losses = 0
                else:
                    log_message(f"Doubling the amount for the next trade: {current_amount * 2}")
                    current_amount *= 2
            else:
                log_message(f"Trade for {asset} won. Resetting to initial amount.")
                current_amount = initial_amount
                consecutive_losses = 0
        else:
            log_message(f"Trade placement failed for {asset}. Verify asset availability, amount, or connection.")
    except KeyError:
        log_message(f"Asset {asset} is not supported by the API. Skipping...")
    except Exception as e:
        log_message(f"Unexpected error monitoring trade for {asset}: {e}")


# GUI Setup
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
    global session_profit
    profit_label.config(text=f"Session Profit: R${session_profit:.2f}", fg="green" if session_profit >= 0 else "red")
threading.Thread(target=update_session_profit, args=(profit_label,)).start()


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


# def start_trading():
#     global running
#     global icon_label
#     if not running:
#         running = True
#         log_message("Starting trading session...")
#         icon_label.config(image=rotating_icon)
#         threading.Thread(target=execute_trades).start()

# def stop_trading():
#     global running
#     running = False
#     log_message("Trading stopped.")
#     icon_label.config(image=static_icon)

# def update_log():
#     try:
#         with open(log_file, "r") as file:
#             lines = file.readlines()
#             log_text.delete(1.0, tk.END)
#             log_text.insert(tk.END, "".join(lines[-10:]))  # Show last 10 lines
#     except FileNotFoundError:
#         log_text.delete(1.0, tk.END)
#         log_text.insert(tk.END, "Log file not found. Waiting for new entries...\n")
#     if running:
#         root.after(1000, update_log)

# def switch_account_type():
#     global account_type
#     reconnect_if_needed()
#     if iq is None:
#         log_message("Unable to switch account. IQ Option API is not connected.")
#         return

#     previous_account = account_type
#     account_type = "REAL" if account_type == "PRACTICE" else "PRACTICE"
#     success = iq.change_balance(account_type)
#     if success:
#         log_message(f"Successfully switched to {'Demo' if account_type == 'PRACTICE' else 'Real'} account")
#     else:
#         log_message(f"Failed to switch account type. Current type remains as {'Demo' if previous_account == 'PRACTICE' else 'Real'}")

# root = tk.Tk()
# root.title("Trading Bot")

# static_icon = PhotoImage(file="static_icon.png")
# rotating_icon = PhotoImage(file="rotating_icon.gif")
# icon_label = tk.Label(root, image=static_icon)
# icon_label.pack()

# start_button = tk.Button(root, text="Start", command=start_trading)
# start_button.pack()

# stop_button = tk.Button(root, text="Stop", command=stop_trading)
# stop_button.pack()

# amount_label = tk.Label(root, text="Initial Amount:")
# amount_label.pack()

# amount_entry = tk.Entry(root)
# amount_entry.insert(0, "10")
# amount_entry.pack()

# def set_initial_amount():
#     global initial_amount
#     global current_amount
#     initial_amount = float(amount_entry.get())
#     current_amount = initial_amount

# set_button = tk.Button(root, text="Set Amount", command=set_initial_amount)
# set_button.pack()

# log_text = ScrolledText(root, height=10)
# log_text.pack()
#Gui config
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
