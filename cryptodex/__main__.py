__version__ = "0.1.0"

import os
import sys
import logging
import argparse

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_tracebacks

from portfolio import Portfolio
from exchanges.kraken import KrakenExchange
from utils import ask
from drawing import display_portfolio_assets, display_orders, format_currency

log = logging.getLogger(__name__)
install_rich_tracebacks()
console = Console()


def main():
    argparser = argparse.ArgumentParser(
        description="Automates creation and management of a cryptocurrency index fund"
    )
    argparser.add_argument(
        "--portfolio",
        type=argparse.FileType("r"),
        help="Path to the .toml portfolio model file",
    )
    argparser.add_argument(
        "--private-key",
        type=argparse.FileType("r"),
        help="Path to the exchange private API key",
    )
    argparser.add_argument(
        "--invest",
        type=int,
        default=0,
        help="Deposit this amount into the portfolio as a lump sum",
    )
    argparser.add_argument(
        "--rebalance",
        action="store_true",
        default=True,
        help="Rebalance the portfolio to re-align the weightings of the assets",
    ),
    argparser.add_argument(
        "--estimate",
        action="store_true",
        help="Display an estimate of the resulting portfolio before orders are executed",
    ),
    argparser.add_argument(
        "--currency",
        choices=["eur", "usd", "gbp"],
        help="The fiat currency to trade with for all buy / sell orders",
    )
    argparser.add_argument(
        "--confirm",
        action="store_true",
        help="Do submit orders to the exchange, rather than just validating them. ",
    )
    argparser.add_argument(
        "-v", "--verbose", action="store_true", help="Increase output log verbosity"
    )
    args = argparser.parse_args()

    if not args.currency:
        argparser.error("Please provide a currency")

    # configure logging for the application
    log = logging.getLogger()
    log.setLevel(logging.INFO if not args.verbose else logging.DEBUG)
    rich_handler = RichHandler()
    rich_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
    log.addHandler(rich_handler)
    log.propagate = False

    # start the application
    portfolio = Portfolio(args.portfolio, args.currency)
    exchange = KrakenExchange(args.private_key)
    with console.status("[bold green]Connecting to exchange..."):
        portfolio.connect(exchange)

    console.print("[bold] Your current portfolio:")
    display_portfolio_assets(portfolio.holdings, args.currency)

    if args.invest:
        console.print(
            f"[✔] {format_currency(args.invest, args.currency)} is being invested in the portfolio"
        )
    if args.rebalance:
        console.print("[✔] Portfolio is being rebalanced")

    with console.status("[bold green]Calculating investments..."):
        orders = portfolio.invest(amount=args.invest)

    console.print(f"\n[bold]The following orders will be processed:")
    display_orders(orders)

    if args.estimate:
        console.print(f"\n[bold]Estimated portfolio after orders are processed:")
        display_portfolio_assets(portfolio.get_predicted_portfolio(orders), args.currency)
        console.print(
            "[yellow]This estimate is based on market prices at script execution time. "
            "Actual order numbers might differ slightly."
        )

    invalid_orders = portfolio.get_invalid_orders(orders)
    if invalid_orders:
        console.print(
            f"[red]{len(invalid_orders)} orders do not meet the minimum order criteria"
        )

    if not args.confirm:
        console.print(
            "[yellow]Script is running without the --confirm flag, "
            "orders will be validated but not executed"
        )
    else:
        console.print(
            "[yellow][bold]Script is running with the --confirm flag, "
            "ALL ORDERS WILL BE SENT TO THE EXCHANGE"
        )
    confirmation = ask("[bold]Would you like to continue", console=console)
    if confirmation:
        mock = not args.confirm
        portfolio.process_orders(exchange, orders, mock=mock)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.critical("Interrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
