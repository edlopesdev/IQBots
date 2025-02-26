from iqoptionapi.stable_api import IQ_Option
import threading
import time
import os
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import PhotoImage
import pandas as pd
import pandas_ta as ta

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
log_file = os.path.normpath(os.path.join(os.getcwd(), "sonic_log.txt"))

def log_message(message):
    try:
        with open(log_file, "a") as file:
            file.write(message + "\n")
    except FileNotFoundError:
        with open(log_file, "w") as file:
            file.write(message + "\n")
    print(message)

# Initialize IQ Option API
account_type = "PRACTICE"  # Default to demo account
instrument_types = ["binary", "crypto", "digital", "otc"]  # Supported instruments

# Define global variables
# Define global variables
running = False
icon_label = None
initial_amount = 2
current_amount = 2  # Track the current trade amount for Martingale strategy
max_simultaneous_trades = 3
simultaneous_trades = 0  # Initialize simultaneous trades counter
martingale_limit = 5  # Limit the number of consecutive Martingale steps
consecutive_losses = 0
session_profit = 0
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

def is_asset_available(asset):
    try:
        available_assets = iq.get_all_ACTIVES_OPCODE()
        if asset in available_assets:
            return True
    except Exception as e:
        log_message(f"Error checking availability for {asset}: {e}")
    return False

# Analyze indicators
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
    log_message(f"Analyzing indicators for {asset}...")
    try:
        start_time = time.time()
        data = fetch_historical_data(asset, 1, 100)  # Fetch last 100 1-minute candles

        indicators = {}

        # Attempt to calculate all indicators
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
        }

        for key, func in available_indicators.items():
            try:
                indicators[key] = func()
            except Exception as e:
                log_message(f"{key.upper()} calculation error for {asset}: {e}")
                indicators[key] = None

        decisions = []

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

        log_message(f"Indicator votes for {asset}: BUY={buy_votes}, SELL={sell_votes}")

        if time.time() - start_time > 10:
            log_message(f"Analysis for {asset} exceeded time limit. Skipping asset.")
            return None

        if total_indicators == 0:
            log_message(f"No valid indicators for {asset}. Skipping asset.")
            return None

        if buy_votes >= 3:
            return "buy"
        elif sell_votes >= 3:
            return "sell"
        else:
            log_message("Insufficient consensus among indicators. Skipping asset.")
            return None

    except Exception as e:
        log_message(f"Error analyzing indicators for {asset}: {e}")
        return None

# Fetch assets and filter top ones
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


# Execute trades continuously
def execute_trades():
    global running
    global current_amount
    global consecutive_losses
    global session_profit
    global simultaneous_trades

    while running:
        log_message("Executing trades...")
        assets = fetch_top_assets()

        if not assets:
            log_message("No assets found. Stopping execution.")
            break

        for asset in assets:
            if simultaneous_trades >= max_simultaneous_trades:
                log_message("Maximum simultaneous trades reached. Waiting...")
                time.sleep(1)
                continue

            decision = analyze_indicators(asset)
            if decision == "buy":
                action = "call"
            elif decision == "sell":
                action = "put"
            else:
                log_message(f"Skipping trade for {asset}. No consensus.")
                continue

            log_message(f"Attempting trade: Asset={asset}, Action={action}, Amount=${current_amount}")

            try:
                success, trade_id = iq.buy(current_amount, asset, action, 1)
                if success:
                    simultaneous_trades += 1
                    log_message(f"Trade placed successfully for {asset}. Trade ID={trade_id}")
                    threading.Thread(target=monitor_trade, args=(trade_id, asset)).start()
                else:
                    log_message(f"Failed to place trade for {asset}.")
            except Exception as e:
                log_message(f"Error during trade execution for {asset}: {e}")

def monitor_trade(trade_id, asset):
    global simultaneous_trades
    global session_profit
    global consecutive_losses
    global current_amount

    try:
        # Aguarda até que a operação seja concluída
        log_message(f"Monitoring trade {trade_id} for asset {asset}...")
        result = None
        while result is None:
            try:
                result = iq.check_win_v3(trade_id)  # Verifica o resultado da operação
                if result is None:
                    log_message(f"Trade {trade_id} not completed yet. Retrying in 1 minute...")
                    time.sleep(60)  # Aguarda 1 minuto antes de tentar novamente
            except Exception as e:
                log_message(f"Error checking status for trade {trade_id}: {e}")
                time.sleep(60)  # Aguarda antes de tentar novamente

        session_profit += result
        log_message(f"Trade result for {asset}: {'Win' if result > 0 else 'Loss'}, Profit={result}")

        update_session_profit()  # Atualiza o lucro no GUI

        if result < 0:
            consecutive_losses += 1
            if consecutive_losses >= martingale_limit:
                current_amount = initial_amount
                consecutive_losses = 0
                log_message("Martingale limit reached. Resetting amount to initial value.")
            else:
                current_amount *= 2
                log_message(f"Doubling trade amount. Next trade amount: ${current_amount}")
        else:
            consecutive_losses = 0
            current_amount = initial_amount

    finally:
        simultaneous_trades -= 1



def trade_logic(asset):
    global current_amount
    global consecutive_losses
    global initial_amount
    global session_profit

    if not is_asset_available(asset):
        log_message(f"Asset {asset} is not available for trading. Skipping.")
        return

    decision = analyze_indicators(asset)
    if not decision:
        return

    if not iq.check_connect():
        reconnect_if_needed()
        if not iq.check_connect():
            log_message(f"Cannot place trade for {asset}: API is disconnected.")
            return

    action = "call" if decision == "buy" else "put"
    log_message(f"Attempting to place trade: Asset={asset}, Action={action}, Amount={current_amount}, Duration=1")

    try:
        success, trade_id = iq.buy(current_amount, asset, action, 1)
        if success:
            log_message(f"Trade executed for {asset}: {decision.upper()} with trade ID {trade_id}")
            time.sleep(300)  # Wait for trade to complete
            result = iq.check_win_v3(trade_id)
            log_message(f"Trade result for {trade_id}: {result}")

            session_profit += result
            update_session_profit()

            if result < 0:
                consecutive_losses += 1
                log_message(f"Trade for {asset} lost. Consecutive losses: {consecutive_losses}")
                if consecutive_losses >= martingale_limit:
                    log_message("Martingale limit reached. Resetting amount to initial value.")
                    current_amount = initial_amount
                    consecutive_losses = 0
                else:
                    current_amount *= 2
                    log_message(f"Doubling the amount for the next trade: {current_amount}")
            else:
                consecutive_losses = 0
                current_amount = initial_amount
                log_message(f"Trade for {asset} won. Resetting to initial amount.")
        else:
            log_message(f"Trade placement failed for {asset}. Skipping.")
    except Exception as e:
        log_message(f"Error placing trade for {asset}: {e}")


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

# GUI Configuration
root = tk.Tk()
root.title("Sonic")
root.configure(bg="#2E2E2E")  # Set dark theme background

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_sonic.png")
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
amount_entry.insert(0, "2")
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#1C1C1C", fg="white")
log_text.grid(row=2, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#2E2E2E", fg="white")
profit_label.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

update_log()
root.mainloop()
