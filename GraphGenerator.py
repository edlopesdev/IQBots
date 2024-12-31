from iqoptionapi.stable_api import IQ_Option
from time import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Conexão com a API
api = IQ_Option("edlopesdev@gmail.com", "EadMaher777$YHVH")
api.connect()

start = time()

# Obtendo os candles
candles = api.get_candles('EURUSD', 1, 10, time())  # Obtém 10 candles de 1 minuto

end = time()

# Preparando os dados para o gráfico
dates = [datetime.fromtimestamp(candle['from']) for candle in candles]
opens = [candle['open'] for candle in candles]
closes = [candle['close'] for candle in candles]
highs = [candle['max'] for candle in candles]
lows = [candle['min'] for candle in candles]

# Plotando os candles
fig, ax = plt.subplots(figsize=(10, 6))
for i in range(len(candles)):
    color = 'green' if closes[i] > opens[i] else 'red'
    # Corpo do candle
    ax.plot([dates[i], dates[i]], [opens[i], closes[i]], color=color, linewidth=5)
    # Sombras
    ax.plot([dates[i], dates[i]], [lows[i], highs[i]], color=color, linewidth=1)

# Formatação do gráfico
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
plt.title('Candlesticks (EURUSD)')
plt.xlabel('Horário')
plt.ylabel('Preço')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

# Exibindo o gráfico
plt.show()

print(f"\nTempo total: {round(end-start, 5)} segundos")