import logging

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.style import Style

log = logging.getLogger(__name__)
console = Console()

CURRENCIES = {"eur": "€", "usd": "$", "gbp": "£"}


def format_currency(value, currency):
    return f"{round(value, 2)} {CURRENCIES.get(currency, '')}"


def display_portfolio_assets(assets, currency=None):
    table = Table()
    table.add_column("Asset")
    table.add_column("Value")
    table.add_column("Allocation %")
    table.add_column("Target %")
    table.add_column("Drift %")
    coins_to_display = [
        asset for asset in assets if not asset.get("stale", False) or asset["amount"] > 0
    ]
    for coin in coins_to_display:
        name = f"[bold]{coin['symbol'].upper()}[/bold] ({coin['name']})"
        amount = format_currency((coin["price"] * coin["amount"]), currency)
        allocation = f"{round(coin['allocation'], 2)}%"
        target = f"{round(coin['target'], 2)}%"
        drift = f"{round(coin['drift'], 2)}%"

        table.add_row(name, amount, allocation, target, drift)
    console.print(table)


def display_orders(orders):
    table = Table()
    table.add_column("Asset")
    table.add_column("Order Type")
    table.add_column(f"Units")
    table.add_column("Min. Order")
    # table.add_column("Fee")
    for order in orders:
        name = f"[bold]{order['symbol'].upper()}"
        buy_or_sell = order["buy_or_sell"].upper()
        buy_sell_units = str(round(order.get("units"), 5))
        min_order_color = (
            "red"
            if float(abs(order["units"])) < float(order["minimum_order"])
            else "green"
        )
        min_order = f"[{min_order_color}]{order['minimum_order']}[/{min_order_color}]"
        table.add_row(
            name,
            buy_or_sell,
            buy_sell_units,
            min_order,
            # fee
        )
    console.print(table)