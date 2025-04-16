#!/usr/bin/env python3
import os
from web3 import Web3
import config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Web3Operations:
    """
    Web3Operations handles all web3-related functionality:
      - Creating a Web3 instance using Alchemy.
      - Retrieving the pool's contract instance.
      - Fetching token decimals using the ERC-20 ABI.
    """
    def __init__(self, pool_address, blockchain):
        self.pool_address = pool_address
        self.blockchain = blockchain

    def get_web3_instance(self):
        api_key = os.getenv("ALCHEMY_API_KEY")
        if not api_key:
            raise EnvironmentError("Alchemy API key not found in environment variables. Please set ALCHEMY_API_KEY.")
        
        if self.blockchain not in config.CHAIN_CONFIG:
            raise ValueError(
                f"Unsupported blockchain: {self.blockchain}. Supported options are: {list(config.CHAIN_CONFIG.keys())}"
            )
        rpc_url = config.CHAIN_CONFIG[self.blockchain]["rpc_url"].format(api_key)
        web3_instance = Web3(Web3.HTTPProvider(rpc_url))
        if not web3_instance.is_connected():
            raise ConnectionError(f"Failed to connect to {rpc_url}. Check API key and network connectivity.")
        return web3_instance

    def get_pool_contract(self, web3_instance):
        pool_abi = [
            {
                "name": "feeGrowthGlobal0X128",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "inputs": [],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "name": "feeGrowthGlobal1X128",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "inputs": [],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "name": "ticks",
                "inputs": [{"internalType": "int24", "name": "tick", "type": "int24"}],
                "outputs": [
                    {"internalType": "uint128", "name": "liquidityGross", "type": "uint128"},
                    {"internalType": "int128", "name": "liquidityNet", "type": "int128"},
                    {"internalType": "uint256", "name": "feeGrowthOutside0X128", "type": "uint256"},
                    {"internalType": "uint256", "name": "feeGrowthOutside1X128", "type": "uint256"},
                    {"internalType": "int56", "name": "tickCumulativeOutside", "type": "int56"},
                    {"internalType": "uint160", "name": "secondsPerLiquidityOutsideX128", "type": "uint160"},
                    {"internalType": "uint32", "name": "secondsOutside", "type": "uint32"},
                    {"internalType": "bool", "name": "initialized", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "name": "slot0",
                "outputs": [
                    {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                    {"internalType": "int24", "name": "tick", "type": "int24"}
                ],
                "inputs": [],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "name": "token0",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "inputs": [],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "name": "token1",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "inputs": [],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        return web3_instance.eth.contract(address=Web3.to_checksum_address(self.pool_address), abi=pool_abi)

    def get_token_decimals(self, web3_instance, pool_contract):
        # Retrieve token addresses from pool contract
        token0_address = pool_contract.functions.token0().call()
        token1_address = pool_contract.functions.token1().call()
        
        # Use a basic ERC20 ABI fragment to get the decimals
        erc20_abi = [{
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function"
        }]
        token0_contract = web3_instance.eth.contract(address=Web3.to_checksum_address(token0_address), abi=erc20_abi)
        token1_contract = web3_instance.eth.contract(address=Web3.to_checksum_address(token1_address), abi=erc20_abi)
        token0_decimals = token0_contract.functions.decimals().call()
        token1_decimals = token1_contract.functions.decimals().call()
        return token0_decimals, token1_decimals
