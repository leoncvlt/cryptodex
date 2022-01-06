import csv

from rich.console import Console
from rich.table import Table

console = Console()

CURRENCIES = {"eur": "€", "usd": "$", "gbp": "£"}


def format_currency(value, currency):
    return f"{round(value, 2)} {CURRENCIES.get(currency, '')}"


def is_substantial(amount):
    return round(amount, 6) > 0


def display_portfolio_assets(assets, currency=None):
    table = Table()
    table.add_column("Asset")
    table.add_column("Value")
    table.add_column("Current %")
    table.add_column("Target %")
    table.add_column("Drift %")
    assets = list(
        filter(lambda a: (is_substantial(a.price * a.amount) or a.target > 0), assets)
    )
    for holding in assets:
        name = f"[bold]{holding.symbol.upper()}[/bold] ({holding.name})"
        amount = format_currency((holding.price * holding.amount), currency)
        allocation = f"{holding.allocation:.2f}%" if not holding.frozen else "-"
        target = f"{holding.target:.2f}%" if not holding.frozen else "-"
        drift = (
            f"{(holding.allocation - holding.target):.2f}%" if not holding.frozen else "-"
        )
        row_style = ""
        if holding.frozen:
            row_style = "dim"
        else:
            if holding.amount == 0:
                row_style = "green"
            if holding.target == 0:
                row_style = "red"
        table.add_row(
            name,
            amount,
            allocation,
            target,
            drift,
            style=row_style,
            end_section=(holding == assets[-1]),
        )
    total_portfolio_value = sum([h.price * h.amount for h in assets])
    table.add_row("[bold]Total", format_currency(total_portfolio_value, currency))
    console.print(table)


def write_portfolio_assets(filename, assets, currency=None):
    with open(filename, "w", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",", lineterminator="\n")
        writer.writerow(["Symbol", "Asset", "Price", "Amount", "Value"])
        for holding in (holding for holding in assets if is_substantial(holding.amount)):
            writer.writerow(
                [
                    holding.symbol.upper(),
                    holding.name,
                    holding.price,
                    holding.amount,
                    format_currency((holding.price * holding.amount), currency),
                ]
            )
        total = sum([h.price * h.amount for h in assets])
        writer.writerow(["", "", "", "", format_currency(total, currency)])


def display_orders(orders):
    table = Table()
    table.add_column("Asset")
    table.add_column("Order Type")
    table.add_column("Units")
    table.add_column("Balance")
    table.add_column("Min. Order")
    for order in orders:
        name = f"[bold]{order.symbol.upper()}"
        buy_or_sell = order.buy_or_sell.upper()
        buy_sell_units = f"{order.units:.5f}"
        buy_sell_currency = format_currency(order.cost, order.currency)
        min_order = str(order.minimum_order)
        row_style = (
            "red" if float(abs(order.units)) < float(order.minimum_order) else "green"
        )
        table.add_row(
            name,
            buy_or_sell,
            buy_sell_units,
            buy_sell_currency,
            min_order,
            style=row_style,
        )
    console.print(table)
