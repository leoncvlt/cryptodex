from abc import ABC, abstractmethod


class Exchange(ABC):
    @abstractmethod
    def get_symbol(self, symbol):
        """
        given an asset symbol from coingecko, return the asset symbol in the exchange
        this method is used to normalize assets naming across exchanges as some
        of them use slightly different rules for asset symbols names,
        for example bitcoin is "btc" on coingecko but "xxbt" on kraken
        """
        pass

    @abstractmethod
    def get_available_assets(self, currency):
        """
        given a fiat currency, returns a list of asset symbols which are
        tradeable using that currency
        """
        pass

    @abstractmethod
    def get_owned_assets(self):
        """
        returns the assets owned in the exchange in the form of a dictionary of
        mapping their symbols to the amount of units owned
        """
        pass

    @abstractmethod
    def get_assets_data(self, assets, currency):
        """
        given a list of assets symbols and a fiat currency, returns a list of dictionaries
        contains the data for each asset. Each must contain the following fields:
        [symbol]: the symbol of the asset
        [minimum_order]: the minimum amount of units that can be traded for the assets
        [price]: the price of a unit of the asset
        [fee]: the % fee for a market order trade

        additionally, you can return a generic dictionary in a [exchange_data] field which
        will be passed to the order objects created when sending a buy / sell command
        """
        pass

    @abstractmethod
    def process_order(self, order, mock=True):
        """
        given a order object, send the order to the exchange for processing
        if the 'mock' flag is False, only run orders validations / simulations
        """
        pass