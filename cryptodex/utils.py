from rich.console import Console
from rich.table import Table

console = Console()

CURRENCIES = {"eur": "€", "usd": "$", "gbp": "£"}


def format_currency(value, currency):
    return f"{round(value, 2)} {CURRENCIES.get(currency, '')}"


def display_portfolio_assets(assets, currency=None):
    table = Table()
    table.add_column("Asset")
    table.add_column("Value")
    table.add_column("Current %")
    table.add_column("Target %")
    table.add_column("Drift %")
    for holding in assets:
        name = f"[bold]{holding.symbol.upper()}[/bold] ({holding.name})"
        amount = format_currency((holding.price * holding.amount), currency)
        allocation = f"{holding.allocation:.2f}%" if not holding.frozen else "-"
        target = f"{holding.target:.2f}%" if not holding.frozen else "-"
        drift = (
            f"{(holding.allocation - holding.target):.2f}%" if not holding.frozen else "-"
        )
        row_style = "dim" if holding.frozen else ""

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