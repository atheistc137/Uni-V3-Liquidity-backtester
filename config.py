from pathlib import Path
from datetime import datetime, timedelta

# Data storage folder
DATA_DIR = Path("./data")

# Pool and token settings
# Pool configuration (new items)
POOL_ADDRESS = "0x6c561b446416e1a00e8e93e221854d6ea4171372"  # Example pool address for WETH/USDC
POOL_NAME = "WETH/USDC"  # Pool name in the format "TOKEN/QUOTE"; used to derive the token symbol (e.g. "WETH" -> "ETH")
BLOCKCHAIN = "base"  # Blockchain identifier (e.g., "ethereum")

SUPPORTED_TOKENS = ["ETH", "SOL", "DOGE", "XRP", "BTC", "BNB"]

# Binance API & pricing settings
BINANCE_SYMBOLS = {
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "DOGE": "DOGEUSDT",
    "XRP": "XRPUSDT",
    "BTC": "BTCUSDT",
    "BNB": "BNBUSDT"
}
BINANCE_API_URL = "https://api.binance.com"
BINANCE_KLINES_ENDPOINT = "/api/v3/klines"
BINANCE_API_MAX_RETRIES = 3
BINANCE_API_RETRY_DELAY = 1  # seconds

# Current date (for calculating lookback period)
current_date = datetime.now()
# Default to 1 year lookback
one_year_ago = current_date - timedelta(days=240)

# Default start and end dates
DEFAULT_START_DATE = one_year_ago
DEFAULT_END_DATE = current_date
# Liquidity simulation settings
LIQUIDITY_RANGE = {
    'lower_bound_factor': 0.85,
    'upper_bound_factor': 1.15
}

# configuration block for simulation settings
SIMULATION_SETTINGS = {
    'initial_capital': 10000,       # Starting capital for simulation
    'buffer_pct': 0.01,             # 1% buffer for reduced rebalances
    'wick_threshold': 0.08,         # 8% price change triggering the wick event
    'wick_lookback_hours': 12,      # Look back period of 12 hours for wick detection
    'wick_cooldown_hours': 4,       # 4-hour cooldown period post wick detection
    # Other simulation settings can be added here.
}

# Options pricing settings (Black-Scholes)
BACKTEST_SETTINGS = {
    'risk_free_rate': 0.01
}
OPTIONS_SETTINGS = {
    'expiration_days': 30
}

# Blockchain configuration for on-chain data

CHAIN_CONFIG = {
    "ethereum": {
        "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/{}",
        "multicall_address": "0x5BA1e12693Dc8F9c48aAD8770482F4739bEeD696",
        "block_time": 13
    },
    "base": {
        "rpc_url": "https://base-mainnet.g.alchemy.com/v2/{}",
        "multicall_address": "0x138ce40d675f9a23e4d6127a8600308cf7a93381",
        "block_time": 2
    },
    "arbitrum": {
        "rpc_url": "https://arb-mainnet.g.alchemy.com/v2/{}",
        "multicall_address": "0x11DEE30E710B8d4a8630392781Cc3c0046365d4c",
        "block_time": 0.5
    },
    # Add additional chains here if needed
}