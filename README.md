# Liquidity Manager 4

A sophisticated automated liquidity management system for decentralized exchanges (DEX) that optimizes liquidity provision and rebalancing strategies.

## Overview

This project implements an automated liquidity management system that:

- Monitors and manages liquidity positions on DEX pools
- Implements intelligent rebalancing strategies with wick detection
- Provides historical data analysis and simulation capabilities
- Supports multiple blockchain networks (Ethereum, Base, Arbitrum)

## Features

- **Automated Liquidity Management**: Dynamic position management with configurable parameters
- **Wick Detection**: Identifies significant price movements and implements cooldown periods
- **Multi-Chain Support**: Compatible with Ethereum, Base, and Arbitrum networks
- **Historical Data Analysis**: Backtesting and simulation capabilities
- **Configurable Parameters**: Flexible settings for different trading strategies
- **Position Recording**: Tracks and visualizes position performance

## Project Structure

```
.
├── config.py              # Configuration settings and parameters
├── data_fetcher.py        # Data fetching and processing
├── liquidity_manager.py   # Core liquidity management logic
├── main.py               # Main execution script
├── pool_web3.py          # Web3 interactions and blockchain operations
├── fee_calculator.py     # Fee calculation and analysis
├── position_recorder.py  # Position tracking and visualization
├── block_search.py       # Blockchain data retrieval
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables (not tracked in git)
```

## Prerequisites

- Python 3.8+
- Web3.py and related blockchain libraries
- Access to blockchain RPC nodes (Alchemy recommended)
- Binance API access for price data

## Installation

1. Clone the repository:

```bash
git clone [repository-url]
cd liquidity-manager-4
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure your environment:

- Copy `.env.example` to `.env`
- Add your API keys and configuration

## Configuration

The system can be configured through `config.py`:

- Pool settings (address, token pairs)
- Simulation parameters
- Blockchain network settings
- Data fetching configurations

Key configuration options include:

- Initial capital
- Buffer percentages
- Wick detection thresholds
- Cooldown periods
- Supported tokens and networks

## Usage

Run the main script:

```bash
python main.py [--clear-cache]
```

Optional arguments:

- `--clear-cache`: Clears historical data cache before running

## Features in Detail

### Liquidity Management

- Automated position opening and rebalancing
- Dynamic range adjustment based on market conditions
- Fee optimization and analysis

### Wick Detection

- Monitors price movements over configurable timeframes
- Implements cooldown periods after significant price changes
- Reduces unnecessary rebalancing during volatile periods

### Data Analysis

- Historical price data fetching from Binance
- Position performance tracking
- Visualization of position value over time

## Supported Networks

- Ethereum Mainnet
- Base Network
- Arbitrum One

## Dependencies

- web3==6.20.2
- eth-account==0.11.1
- pandas==1.5.3
- numpy==1.23.5
- matplotlib==3.10.1
- And other dependencies listed in requirements.txt

## Security Considerations

- Never commit your `.env` file
- Use secure RPC endpoints
- Keep API keys private
- Regularly rotate credentials

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For any questions or inquiries, please contact:

- Email: suryanshchandak13@gmail.com
