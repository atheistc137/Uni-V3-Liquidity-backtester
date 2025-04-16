# liquidity_manager.py
import math
from datetime import timezone
from pool_web3 import Web3Operations
from fee_calculator import FeeCalculator  # Import FeeCalculator for fee computations

class LiquidityManager:
    def __init__(
        self, 
        blockchain_name, 
        pool_address, 
        initial_capital, 
        base_asset, 
        quote_asset, 
        fee_tier, 
        price_data, 
        config,
        slippage_factor=0.001,  # 0.1% slippage by default
        web3_ops=None
    ):
        self.blockchain_name = blockchain_name
        self.pool_address = pool_address
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.base_asset = base_asset
        self.quote_asset = quote_asset
        self.fee_tier = fee_tier
        self.price_data = price_data
        self.config = config
        self.position = None  
        # Use the provided shared Web3Operations instance if given.
        self.web3_ops = web3_ops if web3_ops is not None else Web3Operations(self.pool_address, self.blockchain_name)
        self.slippage_factor = slippage_factor

    def _compute_liquidity_for_capital(self, capital, p, p_a, p_b):
        if p <= 0:
            raise ValueError("Current price must be positive.")
        if p_a >= p_b:
            raise ValueError("Lower bound must be less than upper bound.")

        # Compute factors based on Uniswap v3 formulas:
        x_human = (1.0 / math.sqrt(p)) - (1.0 / math.sqrt(p_b))
        y_human = math.sqrt(p) - math.sqrt(p_a)
        denom_human = x_human * p + y_human

        if denom_human == 0:
            raise ValueError("Liquidity denominator computed as zero. Check price parameters.")
    
        human_liquidity = capital / denom_human
        return human_liquidity

    def _get_position_value(self, p):
        if not self.position:
            return 0.0  # No active position => no value.

        L_human = self.position["L_human"]
        p_a = self.position["p_a"]
        p_b = self.position["p_b"]

        if p <= p_a:
            base_tokens = L_human * ((1.0 / math.sqrt(p_a)) - (1.0 / math.sqrt(p_b)))
            return base_tokens * p
        elif p >= p_b:
            quote_tokens = L_human * (math.sqrt(p_b) - math.sqrt(p_a))
            return quote_tokens
        else:
            base_tokens = L_human * ((1.0 / math.sqrt(p)) - (1.0 / math.sqrt(p_b)))
            quote_tokens = L_human * (math.sqrt(p) - math.sqrt(p_a))
            return base_tokens * p + quote_tokens

    def open_position(self, current_price, current_timestamp):
        lower_bound_factor = self.config.LIQUIDITY_RANGE['lower_bound_factor']
        upper_bound_factor = self.config.LIQUIDITY_RANGE['upper_bound_factor']
        p_a = current_price * lower_bound_factor
        p_b = current_price * upper_bound_factor

        if p_a >= p_b:
            raise ValueError("Invalid bounds: lower bound must be < upper bound.")

        p0 = max(min(current_price, p_b), p_a)  # Clamp p0 to [p_a, p_b]
        L_human = self._compute_liquidity_for_capital(self.current_capital, p0, p_a, p_b)

        # Ensure timestamp is timezone-aware in UTC.
        if current_timestamp.tzinfo is None:
            current_timestamp = current_timestamp.replace(tzinfo=timezone.utc)

        self.position = {
            "open_price": current_price,
            "p_a": p_a,
            "p_b": p_b,
            "open_timestamp": current_timestamp,
            "capital_deployed": self.current_capital,
            "L_human": L_human
        }

        print(f"Opened position at {current_timestamp} (price={current_price:.4f}), "
              f"range=({p_a:.4f},{p_b:.4f}), minted L_human={L_human:.6f}, capital={self.current_capital:.2f}")
        return self.position

    def close_position(self, current_price, current_timestamp):
        """
        Closes the current liquidity position by:
          1. Computing the mark-to-market (MTM) value of the position.
          2. Applying slippage on conversion to the quote token.
          3. Calculating fees via FeeCalculator using the position open and close timestamps,
             along with the current capital.
          4. Updating the current capital with both the conversion result and accrued fees.
        """
        if not self.position:
            print("No active position to close.")
            return self.current_capital

        if current_timestamp.tzinfo is None:
            current_timestamp = current_timestamp.replace(tzinfo=timezone.utc)

        # 1. Compute mark-to-market (before slippage).
        position_value_before_slippage = self._get_position_value(current_price)
        
        # 2. Apply slippage.
        net_quote = position_value_before_slippage * (1.0 - self.slippage_factor)
        
        print(f"Closing position at {current_timestamp}, price={current_price:.4f}. "
              f"Value before slippage={position_value_before_slippage:.2f}, "
              f"after slippage={net_quote:.2f}, slippage_factor={self.slippage_factor}")

        # 3. Calculate fees using FeeCalculator (pass the shared web3_ops).
        fee_calc = FeeCalculator(
            start_time=self.position["open_timestamp"],
            end_time=current_timestamp,
            capital_usd=self.current_capital,
            web3_ops=self.web3_ops
        )
        fees_result = fee_calc.calculate_fees(fixed_price_for_snapshot1=current_price)
        fees = fees_result.get("total_fees_usd", 0)
        print(f"Calculated fees for the period: {fees:.2f} USD")

        # 4. Update current capital.
        total_value = net_quote + fees
        self.current_capital = total_value
        self.position = None
        return self.current_capital

    def rebalance_position(self, current_price, current_timestamp):
        """
        Rebalances the current position by closing it (with fee calculations)
        and then opening a new one with the updated capital.
        """
        self.close_position(current_price, current_timestamp)
        new_position = self.open_position(current_price, current_timestamp)
        return new_position, self.current_capital

    def get_position_value(self, current_price):
        return self._get_position_value(current_price)
