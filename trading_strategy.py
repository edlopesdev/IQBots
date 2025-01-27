# ...existing code...

def should_open_trade(opening_price, closing_price, min_difference):
    """
    Verifica se a diferença entre os preços de abertura e fechamento é maior que a diferença mínima permitida.
    
    :param opening_price: Preço de abertura
    :param closing_price: Preço de fechamento
    :param min_difference: Diferença mínima permitida
    :return: True se a diferença for maior que a mínima, caso contrário False
    """
    return abs(opening_price - closing_price) > min_difference

def should_abandon_trade(opening_price, current_price, max_loss):
    """
    Verifica se a diferença entre o preço de abertura e o preço atual excede a perda máxima permitida.
    
    :param opening_price: Preço de abertura
    :param current_price: Preço atual
    :param max_loss: Perda máxima permitida
    :return: True se a perda for maior que a máxima, caso contrário False
    """
    return abs(opening_price - current_price) > max_loss

def calculate_success_probability(asset, direction):
    """
    Calculate the probability of success based on technical indicators.
    """
    data = fetch_historical_data(asset, 1, 100)  # Fetch last 100 candles of 1 minute each

    if data is None or data.empty:
        log_message(f"Sem dados suficientes para {asset}. Pulando ativo.")
        return 0.0

    # Ensure all columns are cast to compatible dtypes
    data["close"] = data["close"].astype(float)
    data["open"] = data["open"].astype(float)
    data["high"] = data["high"].astype(float)
    data["low"] = data["low"].astype(float)
    if "volume" in data.columns:
        data["volume"] = data["volume"].astype(float)

    # Calculate technical indicators
    volume = data["volume"].iloc[-1]
    candle_strength = (data["close"].iloc[-1] - data["open"].iloc[-1]) / (data["high"].iloc[-1] - data["low"].iloc[-1])
    speed = (data["close"].iloc[-1] - data["close"].iloc[-2]) / data["close"].iloc[-2]
    popularity = volume / data["volume"].mean()

    # Combine indicators to calculate probability
    probability = 0.25 * volume + 0.25 * candle_strength + 0.25 * speed + 0.25 * popularity

    log_message(f"Probabilidade calculada para {asset}: {probability:.2f}")
    return probability

def should_enter_trade(asset, direction, min_probability):
    """
    Determine if a trade should be entered based on the calculated success probability.
    
    :param asset: The asset to be traded
    :param direction: The direction of the trade ('call' or 'put')
    :param min_probability: The minimum probability threshold for entering a trade
    :return: True if the probability is greater than or equal to the minimum, otherwise False
    """
    probability = calculate_success_probability(asset, direction)
    return probability >= min_probability

# Exemplo de uso
opening_price = 1.047635
current_price = 1.046000
max_loss = 0.0010

if should_abandon_trade(opening_price, current_price, max_loss):
    print("Abandonar operação")
else:
    print("Manter operação")

# Exemplo de uso
trade_data = [
    {"Asset": "EUR/USD (OTC)", "Direction": "call", "Net PnL": -13.76},
    {"Asset": "EUR/USD (OTC)", "Direction": "call", "Net PnL": 2.91},
    {"Asset": "EUR/USD (OTC)", "Direction": "put", "Net PnL": 11.34},
    # ...mais dados históricos...
]

asset = "EUR/USD (OTC)"
direction = "call"
min_probability = 0.6

