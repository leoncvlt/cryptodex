import os
import sys
import logging
import argparse
import random
import math
import toml

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

from pycoingecko import CoinGeckoAPI

log = logging.getLogger(__name__)
console = Console()

# from dataclasses import dataclass

# @dataclass
# class Coin:
#     symbol: str
#     allocation: float


class Portfolio:
    def allocate_by_sqrt_market_cap(self):
        total_market_cap = sum([coin["market_cap"] for coin in self.data])
        total_sqrt_market_cap = sum([math.sqrt(coin["market_cap"]) for coin in self.data])
        for coin in self.data:
            coin["market_cap_percent"] = 100 * coin["market_cap"] / total_market_cap
            coin["allocation"] = (
                100 * math.sqrt(coin["market_cap"]) / total_sqrt_market_cap
            )

    # def allocate_by_clamped_market_cap(self, max_value):
    #     total_market_cap = sum([coin["market_cap"] for coin in self.data])
    #     for coin in self.data:
    #         coin["market_cap_percent"] = 100 * coin["market_cap"] / total_market_cap
    #         coin["allocation"] = coin["market_cap_percent"]
    #     overflow = 0
    #     for i in range(0, len(self.data)):
    #         current_coin = self.data[i]
    #         if current_coin["allocation"] > max_value:
    #             overflow = current_coin["allocation"] - max_value
    #             self.data[i]["allocation"] = max_value
    #             redist_values = [
    #                 other_coin["allocation"]
    #                 for other_coin in self.data
    #                 if other_coin["allocation"] < max_value
    #             ]
    #             for j in range(0, len(self.data)):
    #                 other_coin = self.data[j]
    #                 if other_coin["allocation"] < max_value:
    #                     weighted_overflow = (
    #                         overflow * other_coin["allocation"] / sum(redist_values)
    #                     )
    #                     self.data[j]["allocation"] = (
    #                         other_coin["allocation"] + weighted_overflow
    #                     )

    def __init__(self, model):
        self.model = toml.load(model)
        self.data = []

    def fetch_market_data(self, currency):
        cg = CoinGeckoAPI()
        return cg.get_coins_markets(currency)

    def add(self, asset):
        self.data.append(asset)
