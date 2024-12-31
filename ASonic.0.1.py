from iqoptionapi.stable_api import IQ_Option
import threading
import time
import os
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import PhotoImage

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
account_type = "PRACTICE"  # Default to demo account

# Define global variables
running = False
icon_label = None
initial_amount = 10
current_amount = 10  # Track the current trade amount
consecutive_losses = 0
martingale_limit = 5

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
        iq = None
    return check, reason

def reconnect_if_needed():
    log_message("Checking IQ Option API connection status...")
    if iq is None or not iq.check_connect():
        log_message("Reconnecting to IQ Option API...")
        connect_to_iq_option(email, password)

def buy_on_iq_option(amount, asset, action, duration):
    log_message(f"Placing trade: Asset={asset}, Action={action}, Amount={amount}, Duration={duration}")
    try:
        success, trade_id = iq.buy(amount, asset, action, duration)
        return success, trade_id
    except Exception as e:
        log_message(f"Error during trade attempt for {asset}: {e}")
    return False, None

def check_win_v3(trade_id):
    log_message(f"Checking trade result for Trade ID: {trade_id}")
    return iq.check_win_v3(trade_id)

# Evaluate indicators
def evaluate_indicators(asset):
    log_message(f"Evaluating indicators for {asset}...")
    try:
        indicators = iq.get_technical_indicators(asset)
        agreement_count = sum(1 for indicator in indicators if indicator.get("signal") in ["buy", "sell"])
        log_message(f"Indicators agreement count for {asset}: {agreement_count}")
        return agreement_count
    except Exception as e:
        log_message(f"Error evaluating indicators for {asset}: {e}")
        return 0

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

        for asset, details in iq.get_all_open_time()["binary"].items():
            if details.get("open") and asset in valid_assets:
                all_assets[asset] = details.get("volume", 0)
    except Exception as e:
        log_message(f"Error fetching assets: {e}")
        return None

    if not all_assets:
        log_message("No available assets for trading.")
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
        indicators_agreement = evaluate_indicators(asset)

        if indicators_agreement < 5:
            log_message(f"Not enough indicator agreement for {asset} (agreement: {indicators_agreement}). Skipping.")
            time.sleep(2)
            continue

        action = "call" if consecutive_losses % 2 == 0 else "put"  # Alternate actions for simplicity

        success, trade_id = buy_on_iq_option(current_amount, asset, action, 1)  # 1-minute trades
        if success:
            log_message(f"Trade executed for {asset}: {action.upper()} with trade ID {trade_id}")
            time.sleep(60)  # Wait for trade to complete
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

        time.sleep(2)

# GUI Setup
def start_trading():
    global running
    global icon_label
    if not running:
        running = True
        log_message("Starting trading session...")
        icon_label.config(image=rotating_icon)
        threading.Thread(target=execute_trades).start()

def stop_trading():
    global running
    running = False
    log_message("Trading stopped.")
    icon_label.config(image=static_icon)

def update_log():
    try:
        with open(log_file, "r") as file:
            lines = file.readlines()
            log_text.delete(1.0, tk.END)
            log_text.insert(tk.END, "".join(lines[-10:]))  # Show last 10 lines
    except FileNotFoundError:
        log_text.delete(1.0, tk.END)
        log_text.insert(tk.END, "Log file not found. Waiting for new entries...\n")
    if running:
        root.after(1000, update_log)

root = tk.Tk()
root.title("Trading Bot")

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_sonic.png")
icon_label = tk.Label(root, image=static_icon)
icon_label.pack()

start_button = tk.Button(root, text="Start", command=start_trading)
start_button.pack()

stop_button = tk.Button(root, text="Stop", command=stop_trading)
stop_button.pack()

amount_label = tk.Label(root, text="Initial Amount:")
amount_label.pack()

amount_entry = tk.Entry(root)
amount_entry.insert(0, "10")
amount_entry.pack()

def set_initial_amount():
    global initial_amount
    global current_amount
    initial_amount = float(amount_entry.get())
    current_amount = initial_amount

set_button = tk.Button(root, text="Set Amount", command=set_initial_amount)
set_button.pack()

log_text = ScrolledText(root, height=10)
log_text.pack()

update_log()
root.mainloop()
