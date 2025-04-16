#!/usr/bin/env python3
import math
from datetime import datetime
from scipy.stats import norm

import config
from pool_web3 import Web3Operations  # External module handling all web3 interactions
from block_search import get_block_by_timestamp  # Utility to convert timestamp to block number

class FeeCalculator:
    """
    FeeCalculator is responsible for on-chain fee calculations.
    It calculates fee growth, simulated liquidity, and APR between two given block times.
    """
    def __init__(self, start_time: datetime, end_time: datetime, capital_usd: float, web3_ops=None):
        self.start_time = start_time
        self.end_time = end_time
        self.capital_usd = capital_usd
        # Use the provided shared Web3Operations instance if given; otherwise, create a new instance.
        self.web3_ops = web3_ops if web3_ops is not None else Web3Operations(pool_address=config.POOL_ADDRESS, blockchain=config.BLOCKCHAIN)
    
    @staticmethod
    def price_to_tick(price: float) -> int:
        """
        Converts a given price to its corresponding tick value based on the Uniswap
        constant tick spacing of 0.01% increments (i.e., a multiplier of 1.0001).
        """
        return math.floor(math.log(price) / math.log(1.0001))
    
    def get_fee_growth_snapshot(self, block_identifier, fixed_price: float = None) -> dict:
        """
        Takes a block identifier and returns a snapshot of fee growth information.
        """
        web3 = self.web3_ops.get_web3_instance()
        pool_contract = self.web3_ops.get_pool_contract(web3)
        
        token0_address = pool_contract.functions.token0().call()
        token1_address = pool_contract.functions.token1().call()
        token0_decimals, token1_decimals = self.web3_ops.get_token_decimals(web3, pool_contract)
        
        slot0 = pool_contract.functions.slot0().call(block_identifier=block_identifier)
        if fixed_price is None:
            sqrt_price_x96 = slot0[0]
            current_price_raw = (sqrt_price_x96 ** 2) / (2 ** 192)
        else:
            current_price_raw = fixed_price
        
        if current_price_raw == 0:
            raise ValueError("Invalid price reading (zero).")
        
        # Compute a human-readable mid price using token decimal adjustments.
        human_price = (1.0 / current_price_raw) * (10 ** (token1_decimals - token0_decimals))
        mid_price = human_price  # Convention: mid_price is expressed as token1 per token0
        
        lower_target_price = mid_price * config.LIQUIDITY_RANGE['lower_bound_factor']
        upper_target_price = mid_price * config.LIQUIDITY_RANGE['upper_bound_factor']
        lower_tick = self.price_to_tick(lower_target_price)
        upper_tick = self.price_to_tick(upper_target_price)
        
        fee_growth_global0 = pool_contract.functions.feeGrowthGlobal0X128().call(block_identifier=block_identifier)
        fee_growth_global1 = pool_contract.functions.feeGrowthGlobal1X128().call(block_identifier=block_identifier)
        lower_tick_data = pool_contract.functions.ticks(lower_tick).call(block_identifier=block_identifier)
        upper_tick_data = pool_contract.functions.ticks(upper_tick).call(block_identifier=block_identifier)
        
        block = web3.eth.get_block(block_identifier) if block_identifier != 'latest' else web3.eth.get_block('latest')
        block_timestamp = block['timestamp']
        block_number = block['number']
        
        return {
            'fee_growth_global0': fee_growth_global0,
            'fee_growth_global1': fee_growth_global1,
            'lower_tick_data': lower_tick_data,
            'upper_tick_data': upper_tick_data,
            'lower_tick': lower_tick,
            'upper_tick': upper_tick,
            'token0_decimals': token0_decimals,
            'token1_decimals': token1_decimals,
            'current_price_raw': current_price_raw,
            'mid_price': mid_price,
            'block_timestamp': block_timestamp,
            'block_number': block_number
        }
    
    def compute_fee_growth_delta(self, snapshot0: dict, snapshot1: dict) -> tuple:
        inside0_t0 = snapshot0['fee_growth_global0'] - snapshot0['lower_tick_data'][2] - snapshot0['upper_tick_data'][2]
        inside0_t1 = snapshot1['fee_growth_global0'] - snapshot1['lower_tick_data'][2] - snapshot1['upper_tick_data'][2]
        delta_fee_growth0 = inside0_t1 - inside0_t0
        
        inside1_t0 = snapshot0['fee_growth_global1'] - snapshot0['lower_tick_data'][3] - snapshot0['upper_tick_data'][3]
        inside1_t1 = snapshot1['fee_growth_global1'] - snapshot1['lower_tick_data'][3] - snapshot1['upper_tick_data'][3]
        delta_fee_growth1 = inside1_t1 - inside1_t0
        
        return delta_fee_growth0, delta_fee_growth1
    
    def simulate_liquidity(self, mid_price: float, token0_decimals: int, token1_decimals: int, human_price: float) -> float:
        lower_target_price = mid_price * config.LIQUIDITY_RANGE['lower_bound_factor']
        upper_target_price = mid_price * config.LIQUIDITY_RANGE['upper_bound_factor']
        
        sqrtP = math.sqrt(mid_price)
        sqrtPa = math.sqrt(lower_target_price)
        sqrtPb = math.sqrt(upper_target_price)
        
        token0_cost_factor = ((sqrtPb - sqrtP) / (sqrtP * sqrtPb)) / (10 ** token0_decimals)
        token1_cost_factor = ((sqrtP - sqrtPa) * human_price / (10 ** token1_decimals))
        denom = token0_cost_factor + token1_cost_factor
        if denom == 0:
            raise ValueError("Liquidity denominator computed as zero. Check price parameters.")
        L = self.capital_usd / denom
        return L
    
    def compute_fees_and_apr(self, snapshot0: dict, snapshot1: dict, override_liquidity_snapshot: dict = None) -> dict:
        delta_fee_growth0, delta_fee_growth1 = self.compute_fee_growth_delta(snapshot0, snapshot1)
        
        if override_liquidity_snapshot is not None:
            mid_price = override_liquidity_snapshot['current_price_raw']
            human_price = override_liquidity_snapshot['mid_price']
        else:
            mid_price = snapshot1['current_price_raw']
            human_price = snapshot1['mid_price']
   
        token0_decimals = snapshot1['token0_decimals']
        token1_decimals = snapshot1['token1_decimals']
        
        L = self.simulate_liquidity(mid_price, token0_decimals, token1_decimals, human_price)
        
        scaling_factor = 2 ** 128
        fee_growth_per_unit0 = delta_fee_growth0 / scaling_factor
        fee_growth_per_unit1 = delta_fee_growth1 / scaling_factor
        
        fees_token0_raw = fee_growth_per_unit0 * L
        fees_token1_raw = fee_growth_per_unit1 * L
        
        fees_usd_token0 = fees_token0_raw / (10 ** token0_decimals)
        fees_usd_token1 = (fees_token1_raw / (10 ** token1_decimals)) * human_price
        total_fees_usd = fees_usd_token0 + fees_usd_token1
        
        period_seconds = snapshot1['block_timestamp'] - snapshot0['block_timestamp']
        if period_seconds <= 0:
            raise ValueError("Invalid snapshot time period; period_seconds must be positive.")
        seconds_per_year = 365 * 24 * 3600
        annualization_factor = seconds_per_year / period_seconds
        apr_percent = (total_fees_usd / self.capital_usd) * annualization_factor * 100
        
        return {
            'fees_token0_raw': fees_token0_raw,
            'fees_token1_raw': fees_token1_raw,
            'total_fees_usd': total_fees_usd,
            'simulated_liquidity': L,
            'period_seconds': period_seconds,
            'apr_percent': apr_percent
        }
    
    def calculate_fees(self, fixed_price_for_snapshot1: float = None, override_liquidity_snapshot: dict = None) -> dict:
        web3 = self.web3_ops.get_web3_instance()
        start_block_number = get_block_by_timestamp(web3, self.start_time)
        end_block_number = get_block_by_timestamp(web3, self.end_time)
        
        snapshot0 = self.get_fee_growth_snapshot(start_block_number)
        
        if fixed_price_for_snapshot1 is None:
            fixed_price_for_snapshot1 = snapshot0['current_price_raw']
        if override_liquidity_snapshot is None:
            override_liquidity_snapshot = snapshot0
        
        snapshot1 = self.get_fee_growth_snapshot(end_block_number, fixed_price=fixed_price_for_snapshot1)
        
        fees_result = self.compute_fees_and_apr(snapshot0, snapshot1, override_liquidity_snapshot=override_liquidity_snapshot)
        return fees_result

if __name__ == "__main__":
    from datetime import timedelta, timezone

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)
    
    capital_usd = 10000  # e.g., 10,000 USD
    
    fee_calculator = FeeCalculator(start_time, end_time, capital_usd)
    fee_result = fee_calculator.calculate_fees()
    
    print("Fee Calculation Result:")
    for key, value in fee_result.items():
        print(f"{key}: {value}")
