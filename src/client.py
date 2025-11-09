from src.endpoints.market_data import MarketDataAPI

class TradeStationClient:
    def __init__(
        self,
        *,
        token_manager
    ):
        self.token_manager = token_manager
        self.market_data = MarketDataAPI(
            token_manager=token_manager
        )

