__version__ = "0.1.0"

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_tracebacks

from portfolio import Portfolio
from exchanges.exchange import Exchange
from exchanges.kraken import KrakenExchange
from utils import display_portfolio_assets, write_portfolio_assets, display_orders

log = logging.getLogger(__name__)
install_rich_tracebacks()
console = Console()

import toml
import click
from click_shell import shell

from dataclasses import dataclass

EXCHANGES = {"kraken": KrakenExchange}


def validate_strategy(strategy):
    for field in ["currency", "portfolio", "exchange"]:
        if not field in strategy:
            log.critical(f"{field} not defined in strategy file")
            return False

    for field in ["platform", "key", "secret"]:
        if not field in strategy["exchange"]:
            log.critical(f"{field} not defined for the exchange")
            return False

    if not strategy["exchange"]["platform"] in EXCHANGES:
        log.error(f"Exchange platform not supported")
        sys.exit()

    return True


@dataclass
class State:
    portfolio: Portfolio
    exchange: Exchange
    currency: str


@shell(prompt="cryptodex $ ", hist_file=Path(".temp") / ".history")
@click.pass_context
@click.argument("strategy", type=click.File("r"))
@click.option("-v", "--verbose", is_flag=True, help="Increase output verbosity.")
def app(ctx, strategy, verbose):
    """
    Automate and mantain a cryptocurrency-based portfolio tracking the market index.

    STRATEGY: path to the .toml strategy file - see README for more info

    Run the script without any commands to start an interactive shell.
    """

    # configure logging for the application
    log = logging.getLogger()
    log.setLevel(logging.INFO if not verbose else logging.DEBUG)
    rich_handler = RichHandler()
    rich_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
    log.addHandler(rich_handler)
    log.propagate = False

    # initialise application
    data = toml.load(strategy)
    if not validate_strategy(data):
        sys.exit()

    currency = data["currency"]
    portfolio = Portfolio(data["portfolio"], currency)
    exchange_platform = data["exchange"]["platform"]
    exchange = EXCHANGES[exchange_platform](
        data["exchange"]["key"], data["exchange"]["secret"]
    )
    with console.status("[bold green]Connecting to exchange..."):
        portfolio.connect(exchange)
    ctx.obj = State(portfolio, exchange, currency)


@app.command(help="Re-fetch current assets prices / allocations")
@click.pass_obj
def refresh(state):
    state.portfolio.connect(state.exchange)


@app.command(help="Display your current portfolio balance")
@click.pass_obj
@click.option(
    "--log", is_flag=True, help="Log the current portfolio balance to a .csv file",
)
def balance(state, log):
    display_portfolio_assets(state.portfolio.holdings, state.currency)
    if log:
        now = datetime.now()
        filename = Path(".balances") / f"{now.strftime('%Y%m%d')}.csv"
        if not filename.is_file():
            filename.parent.mkdir(parents=True, exist_ok=True)
        console.print(f"Writing balance to {str(filename)}")
        write_portfolio_assets(filename, state.portfolio.holdings, state.currency)


def invest(portfolio, exchange, currency, amount, rebalance, estimate, mock=True):
    with console.status("[bold green]Calculating investments..."):
        raw_orders = portfolio.invest(amount=amount, rebalance=rebalance)
        orders = sorted(raw_orders, key=lambda order: order.buy_or_sell, reverse=True)

    console.print("[bold]The following orders will be sent to the exchange:")
    display_orders(orders)

    invalid_orders = [
        order for order in orders if float(abs(order.units)) < float(order.minimum_order)
    ]
    if invalid_orders:
        console.print(
            f"[red]{len(invalid_orders)} orders do not meet the minimum order criteria"
        )

    if estimate:
        console.print(f"\n[bold]Estimated portfolio after orders are processed:")
        display_portfolio_assets(portfolio.get_predicted_portfolio(orders), currency)
        console.print(
            "[yellow]This estimate is based on market prices at script execution time. "
            "Actual order numbers might differ slightly."
        )

    if mock:
        console.print(
            "[yellow]Script is running with the --mock flag, "
            "orders will be validated but not executed."
        )
    else:
        console.print(
            "[yellow][bold]Script is running with the --no-mock flag, "
            "[bol]ALL ORDERS WILL BE SENT TO THE EXCHANGE AND PROCESSED WITH REAL MONEY!"
        )

    if click.confirm("Do you want to continue?"):
        for order in [order for order in orders if order.units]:
            (success, info) = exchange.process_order(order, mock=mock)
            if success:
                log.info("The order executed successfully: " + str(info))
            else:
                log.warning("There was a problem with the order: " + str(info))


@app.command(help="Invest a lump sum into the portfolio")
@click.pass_obj
@click.argument("amount", default=0)
@click.option(
    "--estimate",
    is_flag=True,
    help="Estimate and display the portfolio balance after the sale",
)
@click.option(
    "--rebalance/--no-rebalance",
    default=True,
    help="Rebalance the portfolio towards its planned allocation during the purchase",
)
@click.option(
    "--mock/--no-mock",
    default=True,
    help="Only validate orders, do not send them to the exchange",
)
def buy(state, amount, rebalance, estimate, mock):
    invest(
        state.portfolio,
        state.exchange,
        state.currency,
        amount,
        rebalance,
        estimate,
        mock=mock,
    )


@app.command(help="Sell the equivalent of a lump sum from your portfolio")
@click.pass_obj
@click.argument("amount", default=0)
@click.option(
    "--estimate",
    is_flag=True,
    help="Estimate and display the portfolio balance after the sale",
)
@click.option(
    "--rebalance/--no-rebalance",
    default=True,
    help="Rebalance the portfolio towards its planned allocation during the sale",
)
@click.option(
    "--mock/--no-mock",
    default=True,
    help="Only validate orders, do not send them to the exchange",
)
def sell(state, amount, rebalance, estimate, mock):
    invest(
        state.portfolio,
        state.exchange,
        state.currency,
        -amount,
        rebalance,
        estimate,
        mock=mock,
    )


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        log.critical("Interrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
