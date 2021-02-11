from exchanges.exchange import Exchange

import logging

from rich.console import Console
import krakenex

log = logging.getLogger(__name__)
console = Console()

SYMBOLS = {
    "btc": "xxbt",
    "doge": "xxdg",
    "eth": "xeth",
    "xrp": "xxrp",
    "ltc": "xltc",
    "xlm": "xxlm",
}


class KrakenExchange(Exchange):
    def __init__(self, key):
        self.api = krakenex.API()
        self.api.load_key(key.name)
        return

    def get_symbol(self, symbol):
        return SYMBOLS.get(symbol, symbol)

    def get_available_assets(self, currency):
        # filter assets pairs if they are tradeable with the desired currency
        # planning to use fiat currencies only for trading so adding a 'z' before it
        # https://support.kraken.com/hc/en-us/articles/360001185506-How-to-interpret-asset-codes
        asset_pairs = self.api.query_public("AssetPairs")["result"]
        tradeable_pairs = [
            asset
            for asset in asset_pairs.values()
            if asset["quote"].lower() == f"z{currency}"
        ]
        # return array of asset symbols, present as 'base' attribute in the asset pairs
        return [asset["base"].lower() for asset in tradeable_pairs]

    def get_owned_assets(self):
        return {
            key.lower(): value
            for key, value in self.api.query_private("Balance")["result"].items()
        }

    def get_assets_data(self, assets, currency):
        asset_pairs = self.api.query_public("AssetPairs")["result"]
        assets_data = [
            {
                "pair_name": assetpair,
                "symbol": asset["base"].lower(),
                "fee": asset["fees"][0][-1],
                "minimum_order": float(asset.get("ordermin", -1)),
                "exchange_data": {"asset_pair": assetpair, **asset},
            }
            for assetpair, asset in asset_pairs.items()
            if asset["base"].lower() in assets
            and asset["quote"].lower() == f"z{currency}"
            # ignore any trade pairs in dark pools
            # https://github.com/mobnetic/BitcoinChecker/issues/166#issuecomment-132743218
            and not ".d" in assetpair
        ]
        tickers_pair = ",".join([asset["pair_name"] for asset in assets_data])
        tickers = self.api.query_public("Ticker", data={"pair": tickers_pair})["result"]
        for asset in assets_data:
            pair_name = asset["pair_name"]
            asset["price"] = tickers[pair_name]["c"][0]
        return assets_data

    def process_order(self, order, mock=True):
        if not "asset_pair" in order.exchange_data:
            log.debug(
                "asset_pair parameter not found in exchange_data, attempting to build manually"
            )
        pair = order.exchange_data.get(
            "asset_pair", f"{order.symbol.upper()}{order.currency.upper()}"
        )
        log.info(
            f"Processing {order.buy_or_sell.upper()} order for "
            f"{round(order.units, 5)} units of {order.symbol} ({pair})"
        )
        order_result = self.api.query_private(
            "AddOrder",
            {
                "pair": pair,
                "type": order.buy_or_sell,
                "ordertype": "market",
                "volume": order.units,
                "validate": mock,
            },
        )
        if order_result["error"]:
            return (False, order_result["error"])
        else:
            return (True, order_result["result"])
