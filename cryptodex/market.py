from pycoingecko import CoinGeckoAPI


def fetch_market_data(self, currency):
    cg = CoinGeckoAPI()
    return cg.get_coins_markets(currency)
