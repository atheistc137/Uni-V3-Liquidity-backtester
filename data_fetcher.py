import os
import time
import math
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime as dt
from scipy.stats import norm
from pathlib import Path
import config


def clean_token(pool_name):
    """
    Extract and clean the token symbol from a pool name.
    For example, both "WETH/USDC" and "USDC/WETH" return "ETH" (if supported).
    """
    tokens = pool_name.split('/')
    cleaned_tokens = []
    for token in tokens:
        cleaned_token = token[1:] if token.startswith('W') else token
        cleaned_tokens.append(cleaned_token.upper())

    for token in cleaned_tokens:
        if token in config.SUPPORTED_TOKENS:
            return token
    return cleaned_tokens[0]


class DataFetcher:
    """
    Handles fetching historical price data from Binance and generating synthetic options pricing.
    """

    def __init__(self, start_date=None, end_date=None, clear_cache=False, clear_all_intervals=False):
        self.start_date = start_date or config.DEFAULT_START_DATE
        self.end_date = end_date or config.DEFAULT_END_DATE
        self.interval = "1h"  # Fixed as per requirements
        self.clear_cache_flag = clear_cache
        self.clear_all_intervals = clear_all_intervals

        if isinstance(self.start_date, str):
            self.start_datetime = dt.strptime(self.start_date, "%Y-%m-%d")
        else:
            self.start_datetime = self.start_date
        if isinstance(self.end_date, str):
            self.end_datetime = dt.strptime(self.end_date, "%Y-%m-%d")
        else:
            self.end_datetime = self.end_date

        self.data_dir = config.DATA_DIR
        self.data_dir.mkdir(exist_ok=True)

        print(f"DEBUG: Data directory absolute path: {self.data_dir.absolute()}")
        print(f"DEBUG: Data directory exists: {self.data_dir.exists()}")
        print(f"DEBUG: Data directory is writable: {os.access(self.data_dir, os.W_OK)}")

        self.pool_address = config.POOL_ADDRESS
        self.pool_name = config.POOL_NAME
        self.blockchain = config.BLOCKCHAIN

    def fetch_price_data(self, force_refresh=False):
        """
        Fetch historical price data using Binance klines.
        """
        price_data_path = self.data_dir / "historical_prices_1h.csv"

        # If clear_cache is True, delete the existing file
        if self.clear_cache_flag:
            if price_data_path.exists():
                try:
                    price_data_path.unlink()
                    print("Cleared cached price data as requested")
                except Exception as e:
                    print(f"Error clearing cache: {e}")

        # Only load from cache if file exists and we're not forcing refresh
        if price_data_path.exists() and not force_refresh and not self.clear_cache_flag:
            print("Loading cached price data (1h interval)...")
            try:
                price_data = pd.read_csv(price_data_path, index_col=0, parse_dates=True)
                return price_data
            except Exception as e:
                print(f"Error loading cached price data: {e}")
                print("Will fetch fresh data instead.")

        print("Fetching historical price data using Binance API (1h interval)...")
        token_symbol = clean_token(self.pool_name)
        binance_symbol = config.BINANCE_SYMBOLS.get(token_symbol)
        if not binance_symbol:
            raise ValueError(f"Binance symbol not found for token '{token_symbol}'. Please update config.BINANCE_SYMBOLS.")

        candles = self._fetch_binance_candles(binance_symbol)
        if not candles:
            raise ValueError(f"No price data returned from Binance for {binance_symbol}")

        columns = [
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
        ]
        price_df = pd.DataFrame(candles, columns=columns)
        price_df["timestamp"] = pd.to_datetime(price_df["timestamp"], unit="ms")
        price_df.set_index("timestamp", inplace=True)
        for col in ["open", "high", "low", "close", "volume"]:
            price_df[col] = price_df[col].astype(float)
        price_df = price_df.sort_index()
        price_data = price_df.resample("1h").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        })
        price_data = price_data.ffill().bfill()
        start_timestamp = self.start_datetime
        end_timestamp = self.end_datetime
        if end_timestamp.hour == 0 and end_timestamp.minute == 0 and end_timestamp.second == 0:
            end_timestamp = end_timestamp.replace(hour=23, minute=59, second=59)
        price_data = price_data.loc[start_timestamp:end_timestamp]
        price_data.columns = [f"{col}_{token_symbol}_USD" for col in price_data.columns]

        try:
            print(f"DEBUG: Saving price data to {price_data_path.absolute()}")
            price_data.to_csv(price_data_path)
        except Exception as e:
            print(f"ERROR: Failed to save price data: {e}")

        return price_data

    def _fetch_binance_candles(self, symbol):
        """
        Helper to fetch candlestick data from Binance.
        """
        start_time = int(self.start_datetime.timestamp() * 1000)
        end_time = int(self.end_datetime.timestamp() * 1000)
        interval = self.interval
        all_candles = []

        for retry in range(config.BINANCE_API_MAX_RETRIES):
            try:
                current_start_time = start_time
                while current_start_time < end_time:
                    params = {
                        "symbol": symbol,
                        "interval": interval,
                        "startTime": current_start_time,
                        "endTime": end_time,
                        "limit": 1000
                    }
                    print("DEBUG: Fetching Binance {} candles from {} to {}".format(
                        interval,
                        dt.fromtimestamp(current_start_time/1000).strftime('%Y-%m-%d %H:%M'),
                        dt.fromtimestamp(end_time/1000).strftime('%Y-%m-%d %H:%M')
                    ))
                    response = requests.get(config.BINANCE_API_URL + config.BINANCE_KLINES_ENDPOINT, params=params)
                    response.raise_for_status()
                    candles = response.json()
                    if not candles:
                        break
                    all_candles.extend(candles)
                    current_start_time = candles[-1][0] + 1
                    if len(candles) < 1000:
                        break
                    time.sleep(config.BINANCE_API_RETRY_DELAY)
                return all_candles
            except requests.exceptions.RequestException as e:
                if retry < config.BINANCE_API_MAX_RETRIES - 1:
                    print(f"Binance API request failed. Retrying in {config.BINANCE_API_RETRY_DELAY} seconds... (Attempt {retry+1}/{config.BINANCE_API_MAX_RETRIES})")
                    time.sleep(config.BINANCE_API_RETRY_DELAY * 2)
                else:
                    raise ValueError(f"Failed to fetch Binance data after {config.BINANCE_API_MAX_RETRIES} attempts: {e}")
        return []

    def fetch_options_data(self, force_refresh=False):
        """
        Generate synthetic options pricing data using the Black–Scholes model.
        """
        options_data_path = self.data_dir / "options_data.csv"
        if options_data_path.exists() and not force_refresh:
            print("Loading cached options data...")
            try:
                options_data = pd.read_csv(options_data_path, index_col=0, parse_dates=True)
                return options_data
            except Exception as e:
                print(f"Error loading cached options data: {e}")
                print("Generating synthetic options data instead.")

        print("Generating synthetic options pricing data using Black–Scholes model...")
        price_data = self.fetch_price_data(force_refresh=force_refresh)
        options_data = self._generate_options_data(price_data)
        try:
            print(f"DEBUG: Saving options data to {options_data_path.absolute()}")
            options_data.to_csv(options_data_path)
        except Exception as e:
            print(f"ERROR: Failed to save options data: {e}")
        return options_data

    def _calculate_black_scholes(self, S, K, T, r, sigma, option_type='put'):
        d1 = (np.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option_type == 'put':
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            raise ValueError("option_type must be 'call' or 'put'")
        return price

    def _generate_options_data(self, price_data):
        date_range = price_data.index
        options_data = pd.DataFrame(index=date_range)
        risk_free_rate = config.BACKTEST_SETTINGS['risk_free_rate']
        expiration_days = config.OPTIONS_SETTINGS['expiration_days']

        token_symbol = clean_token(self.pool_name)
        price_col = f"close_{token_symbol}_USD"
        if price_col not in price_data.columns:
            alt_cols = [col for col in price_data.columns if 'close' in col.lower() and token_symbol in col]
            if alt_cols:
                price_col = alt_cols[0]
            else:
                raise ValueError(f"Price data for {token_symbol} not found. Available columns: {price_data.columns.tolist()}")

        price_data = price_data.sort_index()
        returns = np.log(price_data[price_col] / price_data[price_col].shift(1))
        volatility_window = min(20, len(returns) - 1)
        volatility_window = volatility_window if volatility_window >= 2 else 2
        volatility = returns.rolling(window=volatility_window).std() * np.sqrt(252)
        volatility = volatility.fillna(0.8)

        for strike_pct in [0.9, 0.95, 1.0, 1.05, 1.1]:
            strike_prices = price_data[price_col] * strike_pct
            put_prices = pd.Series(index=date_range, dtype=float)
            for i, date in enumerate(date_range):
                S = price_data[price_col].iloc[i]
                K = strike_prices.iloc[i]
                T = expiration_days / 365.0
                r = risk_free_rate
                sigma = volatility.iloc[i]
                put_prices.iloc[i] = self._calculate_black_scholes(S, K, T, r, sigma, 'put')
            options_data[f"put_{token_symbol}_strike_{strike_pct:.2f}"] = put_prices
            options_data[f"strike_{token_symbol}_{strike_pct:.2f}"] = strike_prices

        options_data[f"volatility_{token_symbol}_USD"] = volatility.fillna(0.8)
        return options_data

    def clear_cache(self):
        """
        Deletes cached CSV files for price and options data.
        """
        price_file = self.data_dir / "historical_prices_1h.csv"
        files_to_remove = [
            price_file,
            self.data_dir / "options_data.csv"
        ]
        for file_path in files_to_remove:
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"Deleted cached file: {file_path}")
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")
        if self.clear_all_intervals:
            for file_path in self.data_dir.glob("historical_prices_*.csv"):
                if file_path != price_file and file_path.exists():
                    try:
                        file_path.unlink()
                        print(f"Deleted cached file: {file_path}")
                    except Exception as e:
                        print(f"Failed to delete {file_path}: {e}")
