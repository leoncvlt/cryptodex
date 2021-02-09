import logging
import math
import toml
from copy import deepcopy

from rich.console import Console
from rich.table import Table

from pycoingecko import CoinGeckoAPI

log = logging.getLogger(__name__)
console = Console()

# from dataclasses import dataclass

# @dataclass
# class Coin:
#     symbol: str
#     allocation: float


class Portfolio:
    def connect(self, exchange):
        cg = CoinGeckoAPI()
        market_data = cg.get_coins_markets(self.model["currency"])
        available_assets = exchange.get_available_assets(self.model["currency"])
        for coin in market_data:
            if len(self.data) >= self.model["assets"]:
                break
            symbol = exchange.get_symbol(coin["symbol"])
            if symbol in available_assets:
                self.data.append(
                    {
                        "symbol": symbol,
                        "name": coin["name"],
                        "market_cap": coin["market_cap"],
                    }
                )
            else:
                log.warning(
                    f"Coin {coin['name']} ({coin['symbol']}) not available for purchase with {self.model['currency']}"
                )
                continue
        self.allocate_by_sqrt_market_cap()

    def update(self, exchange):
        assets_list = [coin["symbol"] for coin in self.data]
        assets_data = exchange.get_assets_data(assets_list, self.model["currency"])
        owned_assets = exchange.get_owned_assets()
        for coin in self.data:
            for asset in assets_data:
                if asset["symbol"] == exchange.get_symbol(coin["symbol"]):
                    coin["price"] = float(asset["price"])
                    coin["fee"] = float(asset["fee"])
                    coin["minimum_order"] = asset["minimum_order"]
            if coin["symbol"] in owned_assets.keys():
                coin["amount"] = float(owned_assets[coin["symbol"]])
            else:
                coin["amount"] = 0
        self.calculate_owned_allocation()
        self.calculate_drift()

    def invest(self, amount=0, rebalance=True, prioritize_targets=False):
        orders = []
        portfolio = deepcopy(self.data)
        coins_above_target = [c for c in portfolio if c["drift"] > 0]
        coins_below_target = [c for c in portfolio if c["drift"] < 0]

        # get the total value of the current portfolio
        total_value = sum([coin["price"] * coin["amount"] for coin in portfolio])
        if rebalance:
            for coin in coins_above_target:
                # for each coin whose allocation is drifting above the target,
                # sell the amount required to put it back into target
                # and add the revenue of the sell order to the availabel fund
                coin_value = coin["price"] * coin["amount"]
                coin["currency_order"] = (coin["drift"] * coin_value) / 100
                amount += coin["currency_order"]

            # redistribution_total_allocation = sum(
            #     coin["target"] for coin in coins_below_target
            # )
            # for coin in coins_below_target:
            #     coin["currency_order"] = (
            #         -(coin["target"] * redistribution_funds)
            #         / redistribution_total_allocation
            #     )

            for coin in coins_below_target:
                # for each coin whose allocation is drifting below the target,
                # calculate the amount of funds needed to put it back into target
                # if enough funds to do so are available, set the buy order,
                # update the available fund and do the same for the next coin
                funds_needed_redist = abs(total_value * coin["drift"]) / 100
                if (amount - funds_needed_redist > 0):
                    # we use abs() above, and set a negative value here as
                    # buy orders are represented by a negative number
                    coin["currency_order"] = -funds_needed_redist;
                    amount -= funds_needed_redist;
                else:
                    log.warning("Not enough funds to rebalance all assets.")
                    break

        for coin in portfolio:
            # spread the available funds into buy orders for all assets,
            # proportionally to their target weighting
            coin["currency_order"] = (
                coin.get("currency_order", 0) - (coin["target"] * amount) / 100
            )
            coin["units_order"] = coin["currency_order"] / coin["price"]

            # create an order object to summarize the transaction for the asset,
            # and add it to the pending orders list
            orders.append(
                {
                    "symbol": coin["symbol"],
                    "units": abs(coin["units_order"]),
                    "buy_or_sell": "buy" if coin["units_order"] < 0 else "sell",
                    "currency": self.model["currency"],
                    "minimum_order": coin["minimum_order"],
                }
            )

        # return the portfolios pending order to execute this investment strategy
        return orders

    def get_predicted_portfolio(self, orders):
        portfolio = deepcopy(self.data)
        for order in orders:
            for coin in portfolio:
                if coin['symbol'] == order['symbol']:
                    sign = 1 if order["buy_or_sell"] == "buy" else -1
                    coin['amount'] += order['units'] * sign
        total_value = sum([coin["price"] * coin["amount"] for coin in portfolio])
        for coin in portfolio:
            coin["allocation"] = (100 * coin["price"] * coin["amount"]) / total_value
            coin["drift"] = coin["allocation"] - coin["target"]
        return portfolio


    def get_invalid_orders(self, orders):
        return [
            order
            for order in orders
            if float(abs(order["units"])) < float(order["minimum_order"])
        ]

    def process_orders(self, exchange, orders, mock=True):
        for order in [order for order in orders if order["units"]]:
            order_result = exchange.process_order(
                order["buy_or_sell"],
                order["symbol"],
                order["currency"],
                order["units"],
                mock=mock,
            )

    def allocate_by_sqrt_market_cap(self):
        total_sqrt_market_cap = sum([math.sqrt(coin["market_cap"]) for coin in self.data])
        for coin in self.data:
            coin["target"] = 100 * math.sqrt(coin["market_cap"]) / total_sqrt_market_cap

    def calculate_owned_allocation(self):
        total_value = sum([coin["price"] * coin["amount"] for coin in self.data])
        for coin in self.data:
            coin["allocation"] = (100 * coin["price"] * coin["amount"]) / total_value

    def calculate_drift(self):
        for coin in self.data:
            coin["drift"] = coin["allocation"] - coin["target"]

    def __init__(self, model):
        self.model = toml.load(model)
        self.data = []