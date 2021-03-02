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
    # coins_to_display = [
    #     holding for holding in assets if not holding.frozen or holding.amount > 0
    # ]
    for holding in assets:
        name = f"[bold]{holding.symbol.upper()}[/bold] ({holding.name})"
        amount = format_currency((holding.price * holding.amount), currency)
        allocation = f"{holding.allocation:.2f}%" if not holding.frozen else "[dim]-"
        target = f"{holding.target:.2f}%" if not holding.frozen else "[dim]-"
        drift = (
            f"{(holding.allocation - holding.target):.2f}%"
            if not holding.frozen
            else "[dim]-"
        )

        table.add_row(
            name,
            amount,
            allocation,
            target,
            drift,
            end_section=(holding == assets[-1]),
        )
    total_portfolio_value = sum([h.price * h.amount for h in assets])
    table.add_row("[bold]Total", format_currency(total_portfolio_value, currency))
    console.print(table)


def display_orders(orders):
    table = Table()
    table.add_column("Asset")
    table.add_column("Order Type")
    table.add_column("Units")
    table.add_column("Balance")
    table.add_column("Min. Order")
    # table.add_column("Fee")
    for order in orders:
        name = f"[bold]{order.symbol.upper()}"
        buy_or_sell = order.buy_or_sell.upper()
        buy_sell_units = f"{order.units:.5f}"
        buy_sell_currency = format_currency(order.cost, order.currency)
        min_order_color = (
            "red" if float(abs(order.units)) < float(order.minimum_order) else "green"
        )
        min_order = f"[{min_order_color}]{order.minimum_order}[/{min_order_color}]"
        table.add_row(
            name,
            buy_or_sell,
            buy_sell_units,
            buy_sell_currency,
            min_order,
            # fee
        )
    console.print(table)