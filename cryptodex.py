__version__ = "0.1.0"

import os
import sys
import logging
import argparse
import random

from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
from rich.traceback import install as install_rich_tracebacks

log = logging.getLogger(__name__)
install_rich_tracebacks()
console = Console()

GREETINGS = ["Hello", "Hi", "Howdy", "G'day", "Hola", "Hey", "Yo", "Ciao"]


def greet(name, repeat=1):
    log.info("Preparing to greet...")
    for i in range(0, repeat):
        print(f"{random.choice(GREETINGS)} {name}!")


def percentage_clamp(dataset, max_value, overflow=0):
    redistributed_dataset = {}
    redist_values = [value for value in dataset.values() if value < max_value]
    for coin, value in dataset.items():
        if value < max_value:
            weighted_overflow = overflow * value / sum(redist_values)
            redistributed_dataset[coin] = value + weighted_overflow
            # redistributed_dataset[coin] = value + overflow / len(redist_values)
        else:
            redistributed_dataset[coin] = value

    final_dataset = dict(redistributed_dataset)
    for coin, value in redistributed_dataset.items():
        if value > max_value:
            overflow = value - max_value
            final_dataset[coin] = max_value
            return percentage_clamp(final_dataset, max_value, overflow)
        else:
            final_dataset[coin] = value

    return final_dataset


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
    with console.status("[bold green]Working on tasks..."):
        data = cg.get_coins_markets("eur", per_page=20, price_change_percentage="24h,30d")
        total_market_cap = sum([coin["market_cap"] for coin in data])
        market_cap_percentages = {
            coin["name"]: round(100 * coin["market_cap"] / total_market_cap, 2)
            for coin in data
        }

        clamped_market_cap_percentages = percentage_clamp(market_cap_percentages, 20)
        table = Table()
        table.add_column("Crypto")
        table.add_column("Current Price")
        table.add_column("Change (24hr)")
        table.add_column("Change (30d)")
        table.add_column("Market Cap")
        table.add_column("%")
        table.add_column("Clamped %")
        for coin in data:
            day_change = round(coin["price_change_percentage_24h_in_currency"], 2)
            day_color = "red" if day_change < 0 else "green"
            month_change = round(coin["price_change_percentage_30d_in_currency"], 2)
            month_color = "red" if month_change < 0 else "green"
            table.add_row(
                coin["name"],
                str(coin["current_price"]),
                f"[{day_color}]{day_change}[/{day_color}]%",
                f"[{month_color}]{month_change}[/{month_color}]%",
                str(coin["market_cap"]),
                str(round(100 * coin["market_cap"] / total_market_cap, 2)),
                str(round(clamped_market_cap_percentages[coin["name"]], 2)),
            )
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
