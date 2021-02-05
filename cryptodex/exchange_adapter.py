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


class ExchangeAdapter:
    def translate_symbol(self, symbol):
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
                # **a,
                "pair_name": assetpair,
                "symbol": asset["base"].lower(),
                "fee": asset["fees"][0][-1],
                "minimum_order": float(asset.get("ordermin", -1)),
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

    def get_tickers_data(self, assets):
        tickers_pair = ",".join([coin["pair_name"] for coin in portfolio.data])
        tickers = k.query_public("Ticker", data={"pair": tickers_pair})["result"]
        for coin in portfolio.data:
            coin["price"] = tickers[coin["pair_name"]]["c"][0]
            coin["purchase_price"] = amount * (coin["allocation"] / 100)
            coin["purchase_units"] = coin["purchase_price"] / float(coin["price"])

    def __init__(self, key):
        self.api = krakenex.API()
        self.api.load_key(key.name)
        return

        tickers_pair = ",".join([coin["pair_name"] for coin in portfolio.data])
        tickers = k.query_public("Ticker", data={"pair": tickers_pair})["result"]
        for coin in portfolio.data:
            coin["price"] = tickers[coin["pair_name"]]["c"][0]
            coin["purchase_price"] = amount * (coin["allocation"] / 100)
            coin["purchase_units"] = coin["purchase_price"] / float(coin["price"])
