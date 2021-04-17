import logging
import math
import toml
from copy import deepcopy

from rich.console import Console


from pycoingecko import CoinGeckoAPI

log = logging.getLogger(__name__)
console = Console()

from dataclasses import dataclass, field


@dataclass
class Holding:
    symbol: str
    name: str
    market_cap: float
    price: float = 0.0
    fee: float = 0.0
    amount: str = 0
    frozen: bool = False
    stale: bool = False
    target: float = 0.0
    allocation: float = 0.0
    minimum_order: float = 0
    exchange_data: dict = field(default_factory=dict)
    order_data: dict = field(default_factory=dict)


@dataclass
class Order:
    symbol: str
    currency: str
    units: float
    cost: float
    buy_or_sell: str = field(init=False)
    minimum_order: float = 0.0
    exchange_data: dict = field(default_factory=dict)

    # on order initialization, set its type (buy or sell) based on the amount of units
    # being traded (negative units means purchase order, positive means sell order)
    # and set its units (order volume) to an absolute value afterwards
    def __post_init__(self):
        self.buy_or_sell = "buy" if self.units < 0 else "sell"
        self.units = abs(self.units)


class Portfolio:
    def connect(self, exchange):
        self.holdings = []
        cg = CoinGeckoAPI()
        market_data = cg.get_coins_markets(self.currency)
        owned_assets = exchange.get_owned_assets()
        available_assets = exchange.get_available_assets(self.currency)
        excluded_assets = [asset.lower() for asset in self.model["exclude"]]

        # create a copy of the owned assets dict for us to modify later
        # in order to keep track of owned assets we add to the portfolio
        parsed_owned_assets = deepcopy(owned_assets)

        total_holdings = self.model["assets"] + self.model["frozen"]

        # iterate throught the data of every asset in the market as provided by the
        # coingecko api, starting from the ones with the highest market cap
        for coin in market_data:
            # if we reached the max amount of holdings to have in the portfolio
            # and there are no more owned assets to parse, stop iterating
            current_holdings = len(([h for h in self.holdings if not h.stale]))
            is_over_max_holdings = current_holdings >= total_holdings
            if is_over_max_holdings and not len(parsed_owned_assets):
                break

            # get the symbol of the asset as specified in the exchange
            coingecko_symbol = coin["symbol"].lower()
            symbol = exchange.get_symbol(coingecko_symbol)

            # if the asset is available on this exchange for trading
            # with the provided currency
            if symbol in available_assets:
                holding = Holding(symbol, coin["name"], coin["market_cap"])
                # if we reached the max amount of holdings to have in the portfolio,
                # mark this asset as frozen (won't be bought or sold)
                if current_holdings > self.model["assets"]:
                    if current_holdings <= total_holdings:
                        holding.frozen = True
                    else:
                        holding.stale = True

                # if we don't own the asset and it does not appear under the list of
                # excluded assets, add it to the portfolio only if we are
                # under the max amount of holdings to have, and its amount stays zero
                if not symbol in parsed_owned_assets.keys():
                    if (
                        not is_over_max_holdings
                        and not coingecko_symbol in excluded_assets
                    ):
                        self.holdings.append(holding)
                # otherwise, we own the asset already, parse the number of units we own
                # and remove it from the list of owned assets to parse
                # add it to the portfolio regardless of the max amount of holdings
                # (owned assets that are added after the max amount of holdings is reached
                # will be marked as frozen anyway and won't be bought or sold)
                else:
                    holding.amount = float(parsed_owned_assets[symbol])
                    del parsed_owned_assets[symbol]
                    self.holdings.append(holding)
                    # if one of the owned asset is excluded in the strategy,
                    # mark it as stale so it's sold during rebalancing
                    if coingecko_symbol in excluded_assets or is_over_max_holdings:
                        holding.stale = True

        # calculate the target allocation of each asset in the portfolio
        # based on the square root of its market cap
        self.allocate_by_sqrt_market_cap()

        # create a list of all the symbols of the assets we hold in the portfolio,
        # and pass that to the get_assets_data() method on the exchange to get
        # the exchange data for each asset
        assets_list = [holding.symbol for holding in self.holdings]
        assets_data = exchange.get_assets_data(assets_list, self.currency)

        # go through each asset in our portfolio and, finding its corresponding asset
        # in the exchange's data list, fill up its price / fee / minimum order fields
        for holding in self.holdings:
            exchange_symbol = exchange.get_symbol(holding.symbol)
            exchange_asset = next(
                (a for a in assets_data if a["symbol"] == exchange_symbol), None
            )
            if exchange_asset:
                holding.price = float(exchange_asset["price"])
                holding.fee = float(exchange_asset["fee"])
                holding.minimum_order = exchange_asset["minimum_order"]
                holding.exchange_data = exchange_asset["exchange_data"]
            else:
                console.warning(
                    f"Unable to fetch data for asset {exchange_symbol} "
                    "Even though it was originally marked as available in the exchange... "
                    "Something went really wrong!"
                )

        # given that we have the values of each asset in the portfolio,
        # calculate the current allocation of all assets
        self.calculate_owned_allocation()

    def invest(self, amount=0, rebalance=True):
        orders = []
        funds = amount
        holdings = deepcopy([holding for holding in self.holdings if not holding.frozen])
        total_value = sum([holding.price * holding.amount for holding in holdings])

        if rebalance:
            for holding in holdings:
                # calculate the rebalanced order value for the holding as the
                # difference between the current amount and the amount needed
                # to direct its allocation back towards the target value
                holding_value = holding.price * holding.amount
                target_value = (total_value / 100) * holding.target
                rebalanced_order_value = holding_value - target_value
                if rebalanced_order_value > 0:  # sell order
                    # if the rebalanced order value is positive, it means we are
                    # over its target value and will result in a buy order -
                    # add the revenue from the sale to the available funds
                    holding.order_data["currency"] = rebalanced_order_value
                    funds += rebalanced_order_value
                else:
                    # if the rebalanced order value is negative, it means we are
                    # below its target value and will result in a sell order -
                    # set it if enough funds to process it are available
                    if funds - abs(rebalanced_order_value) > 0:
                        holding.order_data["currency"] = rebalanced_order_value
                        funds -= abs(rebalanced_order_value)
                    else:
                        log.warning("Not enough funds to rebalance all assets.")
                        break

        for holding in holdings:
            if holding.frozen:
                continue
            # create an empty currency order field if none is present
            holding.order_data["currency"] = holding.order_data.get("currency", 0)

            # spread the available funds into currency orders for all assets,
            # proportionally to their target weighting
            holding.order_data["currency"] -= (holding.target * funds) / 100

            # convert the currency orders into unit orders based on the holding price
            holding.order_data["units"] = holding.order_data["currency"] / holding.price

            # create an order object to summarize the transaction for the asset,
            # and add it to the pending orders list
            if holding.order_data.get("units", None):
                order = Order(
                    holding.symbol,
                    self.currency,
                    holding.order_data["units"],
                    holding.order_data["currency"],
                    holding.minimum_order,
                    holding.exchange_data,
                )
                orders.append(order)

        # return the portfolios pending order to execute this investment strategy
        return orders

    def get_predicted_portfolio(self, orders):
        estimated_holdings = deepcopy([h for h in self.holdings if not h.frozen])
        for order in orders:
            for holding in estimated_holdings:
                if holding.symbol == order.symbol:
                    sign = 1 if order.buy_or_sell == "buy" else -1
                    holding.amount += order.units * sign
        total_value = sum(
            [holding.price * holding.amount for holding in estimated_holdings]
        )
        for holding in estimated_holdings:
            holding.allocation = (100 * holding.price * holding.amount) / total_value

        return estimated_holdings

    def allocate_by_sqrt_market_cap(self):
        non_frozen_holdings = [h for h in self.holdings if not h.frozen and not h.stale]
        total_sqrt_market_cap = sum(
            [math.sqrt(h.market_cap) for h in non_frozen_holdings]
        )
        for holding in self.holdings:
            if not holding.frozen and not holding.stale:
                holding.target = (
                    100 * math.sqrt(holding.market_cap) / total_sqrt_market_cap
                )
            else:
                holding.target = 0

    def calculate_owned_allocation(self):
        non_frozen_holdings = [h for h in self.holdings if not h.frozen]
        total_value = sum([h.price * h.amount for h in non_frozen_holdings])
        for holding in self.holdings:
            if total_value and not holding.frozen:
                holding.allocation = (100 * holding.price * holding.amount) / total_value
            else:
                holding.allocation = 0

    def __init__(self, model, currency):
        self.model = model
        self.currency = currency
        self.holdings = []