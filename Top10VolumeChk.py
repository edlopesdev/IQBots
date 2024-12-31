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
interval = 60              # Candle interval in seconds
count = 100                # Number of candles to fetch

# Fetch the list of assets
assets = iq.get_all_open_time()[instrument_type]
available_assets = [asset for asset, details in assets.items() if details['open']]

# Dictionary to store volume averages
asset_volumes = {}

# Calculate the average volume for each asset
for asset in available_assets:
    print(f"Processing asset: {asset}")
    try:
        candles = iq.get_candles(asset, interval, count, time.time())
        volumes = [candle['volume'] for candle in candles]
        average_volume = sum(volumes) / len(volumes) if volumes else 0
        asset_volumes[asset] = average_volume
    except Exception as e:
        print(f"Error processing {asset}: {e}")

# Sort assets by average volume and get the top 10
sorted_assets = sorted(asset_volumes.items(), key=lambda x: x[1], reverse=True)
top_10_assets = sorted_assets[:10]

# Display the top 10 assets with the highest average volumes
print("\nTop 10 assets with highest average volumes:")
for rank, (asset, avg_volume) in enumerate(top_10_assets, start=1):
    print(f"{rank}. {asset}: {avg_volume}")