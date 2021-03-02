# cryptodex

A python tool to automate and mantain a cryptocurrency-based portfolio tracking the market index.

## Disclaimer
**I am not a qualified licensed investment advisor and I don't have any professional finance experience. This tool neither is, nor should be construed as an offer, solicitation, or recommendation to buy or sell any cryptocurencies assets. Use it at your own risk.**

## Installation & Requirements

Make sure you're in your virtual environment of choice, then run
- `poetry install --no-dev` if you have [Poetry](https://python-poetry.org/) installed
- `pip install -r requirements.txt` otherwise

## Explanation
This tool helps applying the "own the market" approach popularized by global index funds to the cryptocurrency market. It will automatically build a portfolio by fetching a list of the top cryptocurrencies by market cap available in your exchange of choice, sets their allocation based on its square root (to avoid over-representatio of big players like bitcoin) and spread any investment made to it accordingly. By making regular investments over time, the portfolio will be kept up to date with the latest market cap rankings and rebalanced to target the updated allocations.


## Usage
```
cryptodex [OPTIONS] STRATEGY COMMAND [ARGS]...

  Automate and mantain a cryptocurrency-based portfolio tracking the market
  index.

  STRATEGY: path to the .toml strategy file

Options:
  -v, --verbose  Increase output verbosity.
  --help         Show this message and exit.

Commands:
  balance  Display your current portfolio balance
  buy      Invest a lump sum into the portfolio
  refresh  Re-fetch current assets prices / allocations
  sell     Sell the equivalent of a lump sum from your portfolio
```

## Strategy File
The application is started by passing the path to a strategy file, a .toml configuration file dicting how the portfolio should be built, which currency to base the trades on and which exchange to use. An example strategy file is:
```toml
# the fiat currency to use as base for all cryptocurrency trading
# allowed currencies so far are ["usd", "eur", "gbp"]
currency = "usd"

[portfolio]
# the amount of assets to hold in the portfolio. the assets will be fetched 
# from the assets on the exchange which are available for trading with the
# fiat currency specified above  and will be allocated based on the square 
# root of their market cap
assets = 16

# exclude the assets in the list from being allocated in the portfolio.
# list assets by their symbol, e.g. "xbt", "eth"
exclude = []

# number of 'frozen' assets to keep in the portfolio, on top of the ones above.
# a 'frozen' asset is an asset which is allocated in the portfolio based on its
# market cap, but is neiher sold or bought. They are effectively used as
# 'buffers' to avoid having repeated buy / sell orders due to assets
# bouncing in and out of your portfolio because of their market cap changing.
frozen = 2

[exchange]
# name of the exchange platform to fetch assets from / send orders to,
# plus the secret and private details for its API key.
# supported exchanges so far are ["kraken"]
platform = "kraken"
key = "keykeykeykeykeykeykeykeykeykeykeykeykeykeykeykeykeykeykey"
secret = "secretsecretsecretsecretsecretsecretsecretsecretsecretsecretsecretsecretsecretsecretsecr"
```

## Commands
Once initialized with a strategy file, `cryptodex` will connect to the specified exchange, sync / build up your portfolio and start an interactive shell. At this point you can pass one of the following commands:

### `balance`
Displays your current portfolio balance, alongside with the latest target allocation.

### `buy [OPTIONS] [AMOUNT]`
Invest a lump sum `[AMOUNT]` into the portfolio by purchasing assets units proportionally to their target allocations.

Options:
- `--estimate`: Estimate and display the portfolio balance after the sale
- `--rebalance / --no-rebalance`: Rebalance the portfolio towards its planned allocation during the purchase (default: rebalance)
- `--mock / --no-mock`: Only validate orders, do not send them to the exchange (default: mock)

### `sell [OPTIONS] [AMOUNT]` 
Sell the equivalent of a lump sum `[AMOUNT]` from your portfolio by selling assets units proportionally to their target allocations.

Options:
- `--estimate`: Estimate and display the portfolio balance after the sale
- `--rebalance / --no-rebalance`: Rebalance the portfolio towards its planned allocation during the sale (default: rebalance)
- `--mock / --no-mock`: Only validate orders, do not send them to the exchange (default: mock)

### `refresh`
Re-fetch current assets prices / allocations

---

When calling `buy` or `sell`, you will be presented with a list of the orders that will be sent to the exchange to fullfill your request. To see an estimate of what your portfolio will look like once the orders are through, pass the `--estimate` flag.

By default, `buy` and `sell` run in mock mode, which tells the exchange to only validate orders without executing them. To tell the exchange to actually process the orders, pass the `--no-mock` flag (you will be asked to confirm the orders submission anyway).

## Exchanges
The application is built in a modular way to support different exchange platforms - right now the only supported exchange is [Kraken](https://www.kraken.com/). To implement additional exchanges, extend the abstract `Exchange` class implementing all required abstract methods:

## Support [![Buy me a coffee](https://img.shields.io/badge/-buy%20me%20a%20coffee-lightgrey?style=flat&logo=buy-me-a-coffee&color=FF813F&logoColor=white "Buy me a coffee")](https://www.buymeacoffee.com/leoncvlt)
If this tool has proven useful to you, consider [buying me a coffee](https://www.buymeacoffee.com/leoncvlt) to support development of this and [many other projects](https://github.com/leoncvlt?tab=repositories).
