from iqoptionapi.stable_api import IQ_Option
import time

# Login to IQ Option
iq = IQ_Option("edlopesdev@gmail.com", "EadMaher777$YHVH")
check, reason = iq.connect()
if not check:
    print(f"Failed to connect: {reason}")
    exit()

# Parameters for monitoring
instrument_type = "forex"  # Change as needed: forex, crypto, stocks, etc.
asset = "EURUSD"           # Asset name
interval = 60              # Candle interval in seconds
count = 100                # Number of candles to fetch

# Fetch historical data
candles = iq.get_candles(asset, interval, count, time.time())

# Calculate moving average of volumes
volumes = [candle['volume'] for candle in candles]
average_volume = sum(volumes) / len(volumes)
low_volume_threshold = 0.5 * average_volume  # Set threshold as 50% of average volume

# Detect low volume periods
low_volume_periods = [
    candle for candle in candles if candle['volume'] < low_volume_threshold
]
print(f"Low volume periods: {low_volume_periods}")

# Monitor live data for low volume
try:
    while True:
        candles = iq.get_candles(asset, interval, count, time.time())
        for candle in candles:
            if candle['volume'] < low_volume_threshold:
                print(f"Low volume detected: {candle}")
        time.sleep(interval)
except KeyboardInterrupt:
    print("Monitoring stopped.")
except Exception as e:
    print(f"Error: {e}")