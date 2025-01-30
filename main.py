import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import PhotoImage
import SonicGF
import CapybaraGF
from trading_strategy import should_open_trade, should_abandon_trade, calculate_success_probability, should_enter_trade

# Define preset trade values
auto_initial_amount = 2
auto_initial_amount_s = 2

# Define trading schedules
def trading_loop_sonic():
    SonicGF.execute_trades_s()

def trading_loop_capybara():
    CapybaraGF.execute_trades()

def trading_regime():
    current_hour = datetime.now().hour
    if 2 <= current_hour < 4:
        print("INTERVALO - HORÁRIO RUIM PARA NEGOCIAÇÕES")
        return None
    elif (20 <= current_hour < 23) or (8 <= current_hour < 11):
        return SonicGF.execute_trades_s
    else:
        return CapybaraGF.execute_trades

def regime_checker():
    while True:
        execute_trade = trading_regime()
        if execute_trade:
            threading.Thread(target=execute_trade).start()
        time.sleep(3600)  # Check every hour

# Parâmetro de diferença mínima, perda máxima e probabilidade mínima
MIN_DIFFERENCE = 0.0005
MAX_LOSS = 0.0010
MIN_PROBABILITY = 0.6

# Exemplo de dados de operação e dados históricos
operations = [
    {"opening_price": 1.047635, "closing_price": 1.047435, "current_price": 1.046000, "Asset": "EUR/USD (OTC)", "Direction": "call"},
    {"opening_price": 18.358375, "closing_price": 18.362085, "current_price": 18.350000, "Asset": "USD/ZAR (OTC)", "Direction": "put"},
    # ...mais operações...
]

trade_data = [
    {"Asset": "EUR/USD (OTC)", "Direction": "call", "Net PnL": -13.76},
    {"Asset": "EUR/USD (OTC)", "Direction": "call", "Net PnL": 2.91},
    {"Asset": "EUR/USD (OTC)", "Direction": "put", "Net PnL": 11.34},
    # ...mais dados históricos...
]

for operation in operations:
    probability = calculate_success_probability(trade_data, operation["Asset"], operation["Direction"])
    if should_open_trade(operation["opening_price"], operation["closing_price"], MIN_DIFFERENCE) and should_enter_trade(probability, MIN_PROBABILITY):
        print(f"Abrir operação para preço de abertura {operation['opening_price']} e fechamento {operation['closing_price']}")
        if should_abandon_trade(operation["opening_price"], operation["current_price"], MAX_LOSS):
            print(f"Abandonar operação para preço de abertura {operation['opening_price']} e preço atual {operation['current_price']}")
        else:
            print(f"Manter operação para preço de abertura {operation['opening_price']} e preço atual {operation['current_price']}")
    else:
        print(f"Não abrir operação para preço de abertura {operation['opening_price']} e fechamento {operation['closing_price']}")

# GUI Configuration
def update_gui():
    current_hour = datetime.now().hour
    if 2 <= current_hour < 4:
        root.configure(bg="gray")
        interval_label.grid(row=0, column=0, columnspan=5, padx=10, pady=10)
        icon_label.grid_remove()
        start_button.grid_remove()
        smart_stop_button.grid_remove()
        amount_label.grid_remove()
        amount_entry.grid_remove()
        set_button.grid_remove()
        log_text.grid_remove()
        profit_label.grid_remove()
        amount_label_s.grid_remove()
        amount_entry_s.grid_remove()
        set_button_s.grid_remove()
    else:
        root.configure(bg="#010124" if (20 <= current_hour < 23) or (8 <= current_hour < 11) else "#001209")
        interval_label.grid_remove()
        icon_label.grid()
        start_button.grid()
        smart_stop_button.grid()
        amount_label.grid()
        amount_entry.grid()
        set_button.grid()
        log_text.grid()
        profit_label.grid()
        amount_label_s.grid()
        amount_entry_s.grid()
        set_button_s.grid()
    root.after(1000, update_gui)

root = tk.Tk()
root.title("Trading Bot Manager")
root.configure(bg="#010124")

static_icon = PhotoImage(file="static_icon.png")
rotating_icon = PhotoImage(file="working_sonic.png")
icon_label = tk.Label(root, image=static_icon, bg="#010124")
icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

start_button = tk.Button(root, text="Start", command=lambda: threading.Thread(target=trading_regime).start(), bg="#4CAF50", fg="white", font=("Helvetica", 12))
start_button.grid(row=0, column=1, padx=5, pady=5)

smart_stop_button = tk.Button(root, text="Smart Stop", command=lambda: threading.Thread(target=trading_regime).start(), bg="#F44336", fg="white", font=("Helvetica", 12))
smart_stop_button.grid(row=0, column=2, padx=5, pady=5)

amount_label = tk.Label(root, text="Marcha 1 Amount:", bg="#010124", fg="white", font=("Helvetica", 12))
amount_label.grid(row=1, column=1, padx=5, pady=5)

amount_entry = tk.Entry(root, font=("Helvetica", 12))
amount_entry.insert(0, str(auto_initial_amount_s))
amount_entry.grid(row=1, column=2, padx=5, pady=5)

set_button = tk.Button(root, text="Set Amount", command=lambda: SonicGF.set_amount(float(amount_entry.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button.grid(row=1, column=3, padx=5, pady=5)

amount_label_s = tk.Label(root, text="Marcha 2 Amount:", bg="#010124", fg="white", font=("Helvetica", 12))
amount_label_s.grid(row=2, column=1, padx=5, pady=5)

amount_entry_s = tk.Entry(root, font=("Helvetica", 12))
amount_entry_s.insert(0, str(auto_initial_amount))
amount_entry_s.grid(row=2, column=2, padx=5, pady=5)

set_button_s = tk.Button(root, text="Set Amount", command=lambda: CapybaraGF.set_amount(float(amount_entry_s.get())), bg="#FFC107", fg="black", font=("Helvetica", 12))
set_button_s.grid(row=2, column=3, padx=5, pady=5)

log_text = ScrolledText(root, height=10, font=("Courier", 10), bg="#010124", fg="white")
log_text.grid(row=3, column=0, columnspan=5, padx=10, pady=10)

profit_label = tk.Label(root, text="Lucro: R$0.00", font=("Helvetica", 16), bg="#010124", fg="white")
profit_label.grid(row=4, column=0, columnspan=5, padx=10, pady=10)

interval_label = tk.Label(root, text="INTERVALO", font=("Helvetica", 16), bg="gray", fg="red")

footer_label = tk.Label(
    root,
    text="@oedlopes - 2025  - Deus Seja Louvado - Sola Scriptura - Sola Fide - Solus Christus - Sola Gratia - Soli Deo Gloria",
    bg="#010124",
    fg="#A9A9A9",
    font=("Helvetica", 7)
)
footer_label.grid(row=6, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")

root.after(1000, update_gui)
root.mainloop()

# Start the regime checker thread
threading.Thread(target=regime_checker, daemon=True).start()

def main():
    for trade in trades:
        opening_price = trade['Opening price']
        closing_price = trade['Closing price']
        
        if should_enter_trade(opening_price, closing_price):
            # Execute trade
            pass
        else:
            # Skip trade
            pass
