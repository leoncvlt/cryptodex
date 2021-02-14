__version__ = "0.1.0"

import os
import sys
import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_tracebacks

from portfolio import Portfolio
from exchanges.exchange import Exchange
from exchanges.kraken import KrakenExchange
from drawing import display_portfolio_assets, display_orders, format_currency

log = logging.getLogger(__name__)
install_rich_tracebacks()
console = Console()

import toml
import click
from click_shell import shell

from dataclasses import dataclass


@dataclass
class State:
    portfolio: Portfolio
    exchange: Exchange
    currency: str


@shell(prompt="cryptodex $ ")
@click.pass_context
@click.argument("strategy", type=click.File("r"))
@click.option("-v", "--verbose", is_flag=True)
def app(ctx, strategy, verbose):
    # configure logging for the application
    log = logging.getLogger()
    log.setLevel(logging.INFO if not verbose else logging.DEBUG)
    rich_handler = RichHandler()
    rich_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
    log.addHandler(rich_handler)
    log.propagate = False

    # initialise application
    data = toml.load(strategy)
    currency = data["currency"]
    portfolio = Portfolio(data["portfolio"], currency)
    exchange = KrakenExchange(data["exchange"]["key"], data["exchange"]["secret"])
    with console.status("[bold green]Connecting to exchange..."):
        portfolio.connect(exchange)
    ctx.obj = State(portfolio, exchange, currency)


@app.command()
@click.pass_obj
def refresh(state):
    state.portfolio.connect(state.exchange)


@app.command()
@click.pass_obj
def balance(state):
    display_portfolio_assets(state.portfolio.holdings, state.currency)


def invest(portfolio, exchange, currency, amount, rebalance, estimate, mock=True):
    with console.status("[bold green]Calculating investments..."):
        orders = portfolio.invest(amount=amount, rebalance=rebalance)
    display_orders(orders)

    if estimate:
        console.print(f"\n[bold]Estimated portfolio after orders are processed:")
        display_portfolio_assets(portfolio.get_predicted_portfolio(orders), currency)
        console.print(
            "[yellow]This estimate is based on market prices at script execution time. "
            "Actual order numbers might differ slightly."
        )

    invalid_orders = portfolio.get_invalid_orders(orders)
    if invalid_orders:
        console.print(
            f"[red]{len(invalid_orders)} orders do not meet the minimum order criteria"
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
        portfolio.process_orders(exchange, orders, mock=mock)


@app.command()
@click.pass_obj
@click.option("--amount", default=0)
@click.option("--estimate", is_flag=True)
@click.option("--rebalance/--no-rebalance", default=True)
@click.option("--mock/--no-mock", default=True)
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


@app.command()
@click.pass_obj
@click.option("--amount", default=0)
@click.option("--estimate", is_flag=True)
@click.option("--rebalance/--no-rebalance", default=True)
@click.option("--mock/--no-mock", default=True)
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
