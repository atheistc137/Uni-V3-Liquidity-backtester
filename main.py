# main.py
import argparse
from data_fetcher import DataFetcher
from liquidity_manager import LiquidityManager
from position_recorder import PositionRecorder
import config
from pool_web3 import Web3Operations
from datetime import timedelta

def main(clear_cache=False):
    # -------------------------------
    # Data Fetching and Configuration
    # -------------------------------
    try:
        # Fetch historical price data with cache clearing option
        price_data = DataFetcher(clear_cache=clear_cache).fetch_price_data()
        # Parse base and quote assets (expected format: "BASE/QUOTE")
        base_asset, quote_asset = config.POOL_NAME.split('/')
    except Exception as e:
        print("Error during data fetching or config parsing:", e)
        return

    # -------------------------------
    # Initialize Liquidity Manager and Web3 Operations
    # -------------------------------
    web3_ops = Web3Operations(config.POOL_ADDRESS, config.BLOCKCHAIN)
    lm = LiquidityManager(
        config.BLOCKCHAIN,
        config.POOL_ADDRESS,
        config.SIMULATION_SETTINGS['initial_capital'],
        base_asset,
        quote_asset,
        fee_tier=0.003,
        price_data=price_data,
        config=config,
        slippage_factor=0.001,
        web3_ops=web3_ops
    )
    
    recorder = PositionRecorder()
    rebalance_count = 0
    cooldown_until = None  # State for wick-based cooldown

    # -------------------------------
    # Main Loop: Process each hourly price data point
    # -------------------------------
    for timestamp, row in price_data.iterrows():
        # Extract the close price; warn if not found
        close_cols = [c for c in row.index if 'close' in c.lower()]
        if not close_cols:
            print(f"Warning: No close price in {timestamp}")
            continue
        current_price = row[close_cols[0]]
        
        # Open a new position if none exists
        if lm.position is None:
            lm.open_position(current_price, timestamp)
        
        # -------------------------------
        # Wick-Based Cooldown Logic
        # -------------------------------
        # Look back a set number of hours (as per config) for wick detection.
        lookback_time = timestamp - timedelta(hours=config.SIMULATION_SETTINGS.get('wick_lookback_hours', 12))
        past_data = price_data[price_data.index <= lookback_time]
        if not past_data.empty:
            past_price = past_data.iloc[-1][close_cols[0]]
            price_change_pct = abs(current_price - past_price) / past_price
            # If the change exceeds the wick threshold, trigger a cooldown period.
            if price_change_pct >= config.SIMULATION_SETTINGS.get('wick_threshold', 0.08) and (cooldown_until is None or timestamp >= cooldown_until):
                cooldown_until = timestamp + timedelta(hours=config.SIMULATION_SETTINGS.get('wick_cooldown_hours', 4))
                print(f"Price wick at {timestamp}: {price_change_pct*100:.2f}% change. Cooldown until {cooldown_until}.")
        
        # -------------------------------
        # Buffered Rebalancing Logic
        # -------------------------------
        # Retrieve the liquidity position's bounds.
        p_a, p_b = lm.position["p_a"], lm.position["p_b"]
        # Directly use config variables to compute the buffered boundaries.
        if current_price < p_a * (1 - config.SIMULATION_SETTINGS.get('buffer_pct', 0.01)) or current_price > p_b * (1 + config.SIMULATION_SETTINGS.get('buffer_pct', 0.01)):
            if cooldown_until and timestamp < cooldown_until:
                print(f"Rebalance condition met at {timestamp} (price: {current_price:.4f}) but in cooldown until {cooldown_until}.")
            else:
                print(f"Price {current_price:.4f} at {timestamp} is outside the buffered range. Rebalancing...")
                lm.rebalance_position(current_price, timestamp)
                rebalance_count += 1
                recorder.record_rebalance(timestamp, lm.get_position_value(current_price), current_price)
        
        # -------------------------------
        # Record the current position and portfolio value
        # -------------------------------
        recorder.record_position(timestamp, lm.get_position_value(current_price), current_price)

    # -------------------------------
    # Final Reporting and Plotting
    # -------------------------------
    recorder.plot_position()
    print(f"Final Portfolio Value: {lm.get_position_value(current_price):.2f}")
    print(f"Total number of rebalances: {rebalance_count}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run liquidity management simulation')
    parser.add_argument('--clear-cache', action='store_true', 
                      help='Clear historical data cache before running')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run main with clear_cache option
    main(clear_cache=args.clear_cache)
