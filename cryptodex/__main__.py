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

from portfolio import Portfolio
from exchange_adapter import ExchangeAdapter

log = logging.getLogger(__name__)
install_rich_tracebacks()
console = Console()

def main():
    argparser = argparse.ArgumentParser(
        description="Generate static websites from Notion.so pages"
    )
    argparser.add_argument(
        "--portfolio",
        type=argparse.FileType("r"),
        help="Portfolio model"
    )
    argparser.add_argument(
        "--purchase-amount",
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
    portfolio = Portfolio(args.portfolio)
    exchange = ExchangeAdapter(portfolio, args.purchase_currency, args.purchase_amount)
    console.print(portfolio.data)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.critical("Interrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
