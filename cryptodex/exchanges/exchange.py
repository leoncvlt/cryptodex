from abc import ABC, abstractmethod


class Exchange(ABC):
    @abstractmethod
    def get_symbol(self, symbol):
        pass

    @abstractmethod
    def get_available_assets(self, currency):
        pass

    @abstractmethod
    def get_owned_assets(self, currency):
        pass

    @abstractmethod
    def get_assets_data(self, assets, currency):
        pass

    @abstractmethod
    def process_order(
        self, buy_or_sell, symbol, currency, units, exchange_data={}, mock=True
    ):
        pass