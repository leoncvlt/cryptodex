import logging
import math
import toml
from copy import deepcopy

from rich.console import Console


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
        market_data = cg.get_coins_markets(self.currency)
        owned_assets = exchange.get_owned_assets()
        available_assets = exchange.get_available_assets(self.currency)
        excluded_assets = [asset.lower() for asset in self.model["exclude"]]

        # create a copy of the owned assets dict for us to modify later
        # in order to keep track of owned assets we add to the portfolio
        parsed_owned_assets = deepcopy(owned_assets)

        # iterate throught the data of every asset in the market as provided by the
        # coingecko api, starting from the ones with the highest market cap
        for coin in market_data:
            # if we reached the max amount of holdings to have in the portfolio
            # and there are no more owned assets to parse, stop iterating
            is_over_max_holdings = (
                len(self.data) >= self.model["assets"] + self.model["max_stale"]
            )
            if is_over_max_holdings and not len(parsed_owned_assets):
                break

            # get the symbol of the asset as specified in the exchange
            symbol = exchange.get_symbol(coin["symbol"])

            # if the assets is in the exclusion list
            # (using the coingecko naming convention),
            # just skip over it, but remove it from the list of owned assets if present
            if coin["symbol"].lower() in excluded_assets:
                # log.info(f"{coin['symbol']} in exclusion list, skipped")
                if symbol in parsed_owned_assets.keys():
                    del parsed_owned_assets[symbol]
                continue

            # if the asset is available on this exchange for trading
            # with the provided currency
            if symbol in available_assets:
                data = {
                    "symbol": symbol,
                    "name": coin["name"],
                    "market_cap": coin["market_cap"],
                }
                # if we reached the max amount of holdings to have in the portfolio,
                # mark this asset as stale (won't be bought or sold)
                if len(self.data) >= self.model["assets"]:
                    data["stale"] = True

                # if we don't own the asset, add it to the portfolio only if we are
                # under the max amount of holdings to have, and set its amount to zero
                if not symbol in parsed_owned_assets.keys():
                    data["amount"] = 0
                    if not is_over_max_holdings:
                        self.data.append(data)
                # otherwise, we own the asset already, parse the number of units we own
                # remove it to the list of owned assets to parse
                # and add it to the portfolio regardless of the max amount of holdings
                # (owned assets that are added after that amount is reached will
                # be marked as stale anyway and won't be bought or sold)
                else:
                    data["amount"] = float(parsed_owned_assets[symbol])
                    del parsed_owned_assets[symbol]
                    self.data.append(data)
            # else:
            #     log.warning(
            #         f"Coin {coin['name']} ({coin['symbol']}) not available for purchase with {self.currency}"
            #     )

        # calculate the target allocation of each asset in the portfolio
        # based on the square root of its market cap
        self.allocate_by_sqrt_market_cap()

        # create a list of all the symbols of the assets we hold in the portfolio,
        # and pass that to the get_assets_data() method on the exchange to get
        # the exchange data for each asset
        assets_list = [asset["symbol"] for asset in self.data]
        assets_data = exchange.get_assets_data(assets_list, self.currency)

        # go through each asset in our portfolio and, finding its corresponding asset
        # in the exchange's data list, fill up its price / fee / minimum order fields
        for asset in self.data:
            exchange_symbol = exchange.get_symbol(asset["symbol"])
            exchange_asset = next(
                (a for a in assets_data if a["symbol"] == exchange_symbol), None
            )
            if exchange_asset:
                asset["price"] = float(exchange_asset["price"])
                asset["fee"] = float(exchange_asset["fee"])
                asset["minimum_order"] = exchange_asset["minimum_order"]
                asset["exchange_data"] = exchange_asset["exchange_data"]
            else:
                console.warning(
                    f"Unable to fetch data for asset {exchange_symbol} "
                    "Even though it was originally marked as available in the exchange... "
                    "Something went really wrong!"
                )

        # given that we have the values of each asset in the portfolio,
        # calculate the current allocation of all assets and how much
        # they are drifting from their target allocation
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
                if amount - funds_needed_redist > 0:
                    # we use abs() above, and set a negative value here as
                    # buy orders are represented by a negative number
                    coin["currency_order"] = -funds_needed_redist
                    amount -= funds_needed_redist
                else:
                    log.warning("Not enough funds to rebalance all assets.")
                    break

        for coin in portfolio:
            if coin.get("stale", False):
                continue
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
                    "currency": self.currency,
                    "minimum_order": coin["minimum_order"],
                    "exchange_data": coin.get("exchange_data", {}),
                }
            )

        # return the portfolios pending order to execute this investment strategy
        return orders

    def get_predicted_portfolio(self, orders):
        portfolio = deepcopy(self.data)
        for order in orders:
            for coin in portfolio:
                if coin["symbol"] == order["symbol"]:
                    sign = 1 if order["buy_or_sell"] == "buy" else -1
                    coin["amount"] += order["units"] * sign
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
            (success, info) = exchange.process_order(
                order["buy_or_sell"],
                order["symbol"],
                order["currency"],
                order["units"],
                exchange_data=order["exchange_data"],
                mock=mock,
            )
            if success:
                log.info("The order executed successfully: " + str(info))
            else:
                log.warning("There was a problem with the order: " + str(info))

    def allocate_by_sqrt_market_cap(self):
        #TODO: Exclude stale assets
        total_sqrt_market_cap = sum([math.sqrt(coin["market_cap"]) for coin in self.data])
        for coin in self.data:
            if not coin.get("stale", False):
                coin["target"] = (
                    100 * math.sqrt(coin["market_cap"]) / total_sqrt_market_cap
                )
            else:
                coin["target"] = 0

    def calculate_owned_allocation(self):
        #TODO: Exclude stale assets
        total_value = sum([coin["price"] * coin["amount"] for coin in self.data])
        for coin in self.data:
            if total_value:
                coin["allocation"] = (100 * coin["price"] * coin["amount"]) / total_value
            else:
                coin["allocation"] = 0

    def calculate_drift(self):
        for coin in self.data:
            coin["drift"] = coin["allocation"] - coin["target"]

    def __init__(self, model, currency):
        self.model = toml.load(model)
        self.currency = currency
        self.data = []