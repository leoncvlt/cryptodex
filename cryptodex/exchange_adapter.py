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

import krakenex
from pycoingecko import CoinGeckoAPI

log = logging.getLogger(__name__)
console = Console()

SYMBOLS = {"btc": "xbt", "doge": "xdg"}


class ExchangeAdapter:
    def __init__(self, portfolio, currency, amount):
        k = krakenex.API()
        asset_pairs = k.query_public("AssetPairs")["result"]
        market_data = portfolio.fetch_market_data(currency)

        for coin in market_data:
            if len(portfolio.data) >= portfolio.model["assets"]:
                break
            translated_symbol = SYMBOLS.get(coin["symbol"], coin["symbol"])
            try:
                (pair_name, coin_in_exchange) = [
                    (k, v)
                    for k, v in asset_pairs.items()
                    if v["altname"] == f"{translated_symbol}{currency}".upper()
                ][0]
                portfolio.add(
                    {
                        "name": coin["name"],
                        "pair_name": pair_name,
                        "symbol": translated_symbol,
                        "market_cap": coin["market_cap"],
                        "fee": coin_in_exchange["fees"][0][-1],
                        "minimum_order": coin_in_exchange["ordermin"],
                    }
                )
            except:
                log.warning(
                    f"Coin {coin['name']} ({coin['symbol']}) not available for purchase with {currency}"
                )
                continue

        portfolio.allocate_by_sqrt_market_cap()

        tickers_pair = ",".join([coin["pair_name"] for coin in portfolio.data])
        tickers = k.query_public("Ticker", data={"pair": tickers_pair})["result"]
        for coin in portfolio.data:
            coin["price"] = tickers[coin["pair_name"]]["c"][0]
            coin["purchase_price"] = amount * (coin["allocation"] / 100)
            coin["purchase_units"] = coin["purchase_price"] / float(coin["price"])
