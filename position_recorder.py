# position_recorder.py
import matplotlib.pyplot as plt

class PositionRecorder:
    def __init__(self):
        # We'll store each record as a dictionary with timestamp, portfolio value, and price.
        self.records = []    # List of portfolio value records along with token price.
        self.rebalances = [] # List to store rebalance events (with price as well).

    def record_position(self, timestamp, position_value, price):
        """
        Records the portfolio value and token price at a given timestamp.
        """
        self.records.append({
            "timestamp": timestamp, 
            "position_value": position_value,
            "price": price
        })

    def record_rebalance(self, timestamp, position_value, price):
        """
        Records a rebalance event at a given timestamp along with portfolio value and token price.
        """
        self.rebalances.append({
            "timestamp": timestamp, 
            "position_value": position_value,
            "price": price
        })

    def plot_position(self):
        """
        Plots portfolio value (left y-axis) and token price (right y-axis) over time as smooth lines.
        Red dots represent rebalance events, and are overlaid on the portfolio value curve.
        """
        if not self.records:
            print("No position records to plot.")
            return

        # Ensure records are sorted by timestamp.
        self.records.sort(key=lambda x: x["timestamp"])
        timestamps = [record["timestamp"] for record in self.records]
        portfolio_values = [record["position_value"] for record in self.records]
        prices = [record["price"] for record in self.records]

        # Create the base figure and primary axis.
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Plot Portfolio Value on the left y-axis as a smooth line.
        color_portfolio = 'tab:blue'
        ax1.set_xlabel("Timestamp")
        ax1.set_ylabel("Portfolio Value (in Quote)", color=color_portfolio)
        ax1.plot(timestamps, portfolio_values, label="Portfolio Value", color=color_portfolio, linestyle="-")
        ax1.tick_params(axis='y', labelcolor=color_portfolio)

        # Mark the rebalance events on the primary axis as red dots.
        for event in self.rebalances:
            ax1.plot(event["timestamp"], event["position_value"], 'ro', markersize=8)

        # Create a twin y-axis to plot Token Price as a smooth line.
        ax2 = ax1.twinx()
        color_price = 'tab:green'
        ax2.set_ylabel("Token Price", color=color_price)
        ax2.plot(timestamps, prices, label="Token Price", color=color_price, linestyle="--")
        ax2.tick_params(axis='y', labelcolor=color_price)

        plt.title("Portfolio Value and Token Price Over Time")
        plt.xticks(rotation=45)
        fig.tight_layout()
        plt.show()
