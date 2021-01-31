__version__ = "0.1.0"

import os
import sys
import logging
import argparse
import random
import math

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler
from rich.traceback import install as install_rich_tracebacks

import krakenex

log = logging.getLogger(__name__)
install_rich_tracebacks()
console = Console()


def weighted_add(data, name, param, value):
    weighted_data = []
    for coin in data:
        if coin["name"] == name:
            weighted_data.append({**coin, param: coin[param] + value})
        else:
            weighted_overflow = value * coin[param] / (len(data) - 1)
            weighted_data.append({**coin, param: coin[param] - weighted_overflow})
    return weighted_data


def allocate_by_sqrt_market_cap(data):
    total_market_cap = sum([coin["market_cap"] for coin in data])
    total_sqrt_market_cap = sum([math.sqrt(coin["market_cap"]) for coin in data])
    for coin in data:
        coin["market_cap_percent"] = 100 * coin["market_cap"] / total_market_cap
        coin["allocation"] = 100 * math.sqrt(coin["market_cap"]) / total_sqrt_market_cap


def allocate_by_clamped_market_cap(data, max_value):
    total_market_cap = sum([coin["market_cap"] for coin in data])
    for coin in data:
        coin["market_cap_percent"] = 100 * coin["market_cap"] / total_market_cap
        coin["allocation"] = coin["market_cap_percent"]

    overflow = 0
    for i in range(0, len(data)):
        current_coin = data[i]
        if current_coin["allocation"] > max_value:
            overflow = current_coin["allocation"] - max_value
            data[i]["allocation"] = max_value
            redist_values = [
                other_coin["allocation"]
                for other_coin in data
                if other_coin["allocation"] < max_value
            ]
            for j in range(0, len(data)):
                other_coin = data[j]
                if other_coin["allocation"] < max_value:
                    weighted_overflow = (
                        overflow * other_coin["allocation"] / sum(redist_values)
                    )
                    data[j]["allocation"] = other_coin["allocation"] + weighted_overflow


# def translate_data(data):
#     SYMBOLS = {"btc": "xbt"}
#     return [
#         {**coin, "symbol": SYMBOLS.get(coin["symbol"], coin["symbol"])} for coin in data
#     ]


def main():
    # parse command line arguments
    argparser = argparse.ArgumentParser(
        description="Generate static websites from Notion.so pages"
    )
    # argparser.add_argument(
    #     "name",
    #     help="Name of the person to greet",
    # )
    argparser.add_argument(
        "--purchase-price",
        type=int,
        default=100,
        help="How many times to repeat the greeting",
    )
    argparser.add_argument(
        "--purchase-currency",
        default="usd",
        help="How many times to repeat the greeting",
    )
    argparser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="How many times to repeat the greeting",
    )
    argparser.add_argument(
        "-v", "--verbose", action="store_true", help="Increase output log verbosity"
    )
    args = argparser.parse_args()

    # configure logging for the application
    log = logging.getLogger()
    log.setLevel(logging.INFO if not args.verbose else logging.DEBUG)
    rich_handler = RichHandler()
    rich_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
    log.addHandler(rich_handler)
    log.propagate = False

    # start the application
    log.debug(f"Starting application with args {vars(args)}")

    from pycoingecko import CoinGeckoAPI

    cg = CoinGeckoAPI()
    with console.status("[bold green]Fetching required data..."):
        data = cg.get_coins_markets(args.purchase_currency, per_page=30, price_change_percentage="24h,30d")

        k = krakenex.API()
        exchange_data = k.query_public("AssetPairs")["result"]
        # console.print(exchange_data)

        SYMBOLS = {"btc": "xbt"}
        for coin in data:
            try:
                translated_symbol = SYMBOLS.get(coin["symbol"], coin["symbol"])
                exchange_coin = [
                    v
                    for k, v in exchange_data.items()
                    if v["altname"] == f"{translated_symbol}{args.purchase_currency}".upper()
                ][0]
                coin["minimum_order"] = exchange_coin["ordermin"]
                coin["fee"] = exchange_coin["fees"][0][-1]
            except:
                coin["minimum_order"] = -1
                coin["fee"] = -1

        # get market cap, market cap percentage and clamped market cap percentage
        # clamp_market_cap(data, 10)
        allocate_by_sqrt_market_cap(data)

        # calculate confidence and add weights to the clamped marked cap percent field
        # for i in range(0, len(data)):
        #     data = weighted_add(data, "Bitcoin", "allocation", 2);

        for coin in data:
            coin["purchase_price"] = args.purchase_price * (coin["allocation"] / 100)
            coin["purchase_units"] = coin["purchase_price"] / coin["current_price"]

        table = Table()
        table.add_column("Crypto")
        table.add_column("Current Price")
        # table.add_column("Change (24hr)")
        # table.add_column("Change (30d)")
        table.add_column("Market Cap %")
        table.add_column("Allocation %")
        table.add_column("Cost", style="magenta")
        table.add_column("Units", style="magenta")
        table.add_column("Min. Order")
        table.add_column("Fee")
        for coin in data:
            # day_change = round(coin["price_change_percentage_24h_in_currency"], 2)
            # day_color = "red" if day_change < 0 else "green"
            # month_change = round(coin["price_change_percentage_30d_in_currency"], 2)
            # month_color = "red" if month_change < 0 else "green"

            min_order_color = (
                "red"
                if float(coin["purchase_units"]) < float(coin["minimum_order"])
                else "green"
            )
            table.add_row(
                coin["name"] + f" [bold]({coin['symbol']})",
                str(coin["current_price"]),
                # f"[{day_color}]{day_change}[/{day_color}]%",
                # f"[{month_color}]{month_change}[/{month_color}]%",
                str(round(coin["market_cap_percent"], 2)),
                str(round(coin["allocation"], 2)),
                f"{round(coin['purchase_price'], 2)}",
                f"{round(coin['purchase_units'], 6)}",
                f"[{min_order_color}]{coin['minimum_order']}[/{min_order_color}]"
                if float(coin["fee"]) > 0
                else "?",
                f"{round((coin['purchase_price'] * coin['fee'])/100, 2) if float(coin['fee']) > 0 else '?'}",
            )
        console.print(f"Investing {args.purchase_price} {args.purchase_currency} into the following assets:")
        console.print(table)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.critical("Interrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
