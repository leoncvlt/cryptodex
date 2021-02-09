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
        "--portfolio", type=argparse.FileType("r"), help="Portfolio model"
    )
    argparser.add_argument(
        "--private-key", type=argparse.FileType("r"), help="private-key"
    )
    argparser.add_argument(
        "--invest",
        type=int,
        default=0,
        help="How many times to repeat the greeting",
    )
    argparser.add_argument(
        "--purchase-currency",
        default="eur",
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
    exchange = ExchangeAdapter(args.private_key)
    portfolio.connect(exchange)
    portfolio.update(exchange)
    orders = portfolio.invest(exchange, deposit=args.invest)
    invalid_orders = portfolio.get_invalid_orders(orders)
    console.print(portfolio.to_table())
    console.print(portfolio.format_orders(orders))
    if invalid_orders:
        log.warning(
            f"{len(invalid_orders)} orders do not meet the minimum order criteria"
        )
    portfolio.process_orders(exchange, orders)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.critical("Interrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
