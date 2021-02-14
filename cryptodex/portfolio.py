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
    stale: bool = False
    target: float = 0.0
    allocation: float = 0.0
    drift: float = 0.0
    minimum_order: float = 0
    exchange_data: dict = field(default_factory=dict)
    order_data: dict = field(default_factory=dict)


@dataclass
class Order:
    symbol: str
    units: float
    currency: str
    buy_or_sell: str = field(init=False)
    minimum_order: float = 0.0
    exchange_data: dict = field(default_factory=dict)

    # on order initialization, set its type (buy or sell) based on the amount of units
    # being traded (negating units means purchase order, positive means sell order)
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

        # iterate throught the data of every asset in the market as provided by the
        # coingecko api, starting from the ones with the highest market cap
        for coin in market_data:
            # if we reached the max amount of holdings to have in the portfolio
            # and there are no more owned assets to parse, stop iterating
            is_over_max_holdings = (
                len(self.holdings) >= self.model["assets"] + self.model["max_stale"]
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
                holding = Holding(symbol, coin["name"], coin["market_cap"])
                # if we reached the max amount of holdings to have in the portfolio,
                # mark this asset as stale (won't be bought or sold)
                if len(self.holdings) >= self.model["assets"]:
                    holding.stale = True

                # if we don't own the asset, add it to the portfolio only if we are
                # under the max amount of holdings to have, and its amount stays zero
                if not symbol in parsed_owned_assets.keys():
                    if not is_over_max_holdings:
                        self.holdings.append(holding)
                # otherwise, we own the asset already, parse the number of units we own
                # and remove it from the list of owned assets to parse
                # add it to the portfolio regardless of the max amount of holdings
                # (owned assets that are added after the max amount of holdings is reached
                # will be marked as stale anyway and won't be bought or sold)
                else:
                    holding.amount = float(parsed_owned_assets[symbol])
                    del parsed_owned_assets[symbol]
                    self.holdings.append(holding)
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
        # calculate the current allocation of all assets and how much
        # they are drifting from their target allocation
        self.calculate_owned_allocation()
        self.calculate_drift()

    def invest(self, amount=0, rebalance=True):
        orders = []
        funds = amount
        holdings = deepcopy(self.holdings)
        holdings_above_target = [h for h in holdings if h.drift > 0]
        holdings_below_target = [h for h in holdings if h.drift < 0]

        # get the total value of the current portfolio
        total_value = sum([holding.price * holding.amount for holding in holdings])
        if rebalance:
            for holding in holdings_above_target:
                # for each coin whose allocation is drifting above the target,
                # sell the amount required to put it back into target
                # and add the revenue of the sell order to the availabel fund
                holding_value = holding.price * holding.amount
                holding.order_data["currency"] = (holding.drift * holding_value) / 100
                funds += holding.order_data["currency"]

            for holding in holdings_below_target:
                # for each coin whose allocation is drifting below the target,
                # calculate the amount of funds needed to put it back into target
                # if enough funds to do so are available, set the buy order,
                # update the available fund and do the same for the next coin
                funds_needed_redist = abs(total_value * holding.drift) / 100
                if funds - funds_needed_redist > 0:
                    # we use abs() above, and set a negative value here as
                    # buy orders are represented by a negative number
                    holding.order_data["currency"] = -funds_needed_redist
                    funds -= funds_needed_redist
                else:
                    log.warning("Not enough funds to rebalance all assets.")
                    break

        for holding in holdings:
            if holding.stale:
                continue
            # spread the available funds into buy orders for all assets,
            # proportionally to their target weighting
            holding.order_data["currency"] = (
                holding.order_data.get("currency", 0) - (holding.target * funds) / 100
            )
            holding.order_data["units"] = holding.order_data["currency"] / holding.price

            # create an order object to summarize the transaction for the asset,
            # and add it to the pending orders list
            if holding.order_data.get("units", None):
                order = Order(
                    holding.symbol,
                    holding.order_data["units"],
                    self.currency,
                    holding.minimum_order,
                    holding.exchange_data,
                )
                orders.append(order)

        # return the portfolios pending order to execute this investment strategy
        return orders

    def get_predicted_portfolio(self, orders):
        estimated_holdings = deepcopy(self.holdings)
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
            holding.drift = holding.allocation - holding.target

        return estimated_holdings

    def get_invalid_orders(self, orders):
        return [
            order
            for order in orders
            if float(abs(order.units)) < float(order.minimum_order)
        ]

    def process_orders(self, exchange, orders, mock=True):
        for order in [order for order in orders if order.units]:
            (success, info) = exchange.process_order(order, mock=mock)
            if success:
                log.info("The order executed successfully: " + str(info))
            else:
                log.warning("There was a problem with the order: " + str(info))

    def allocate_by_sqrt_market_cap(self):
        # TODO: Exclude stale assets
        total_sqrt_market_cap = sum(
            [math.sqrt(holding.market_cap) for holding in self.holdings]
        )
        for holding in self.holdings:
            if not holding.stale:
                holding.target = (
                    100 * math.sqrt(holding.market_cap) / total_sqrt_market_cap
                )
            else:
                holding.target = 0

    def calculate_owned_allocation(self):
        # TODO: Exclude stale assets
        total_value = sum([holding.price * holding.amount for holding in self.holdings])
        for holding in self.holdings:
            if total_value:
                holding.allocation = (100 * holding.price * holding.amount) / total_value
            else:
                holding.allocation = 0

    def calculate_drift(self):
        for holding in self.holdings:
            holding.drift = holding.allocation - holding.target

    def __init__(self, model, currency):
        self.model = model
        self.currency = currency
        self.holdings = []