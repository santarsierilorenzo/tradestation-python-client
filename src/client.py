from src.endpoints.ts_stream import MarketDataStream, BrokerStream
from src.endpoints.mkt_data import MarketDataAPI
from src.endpoints.broker import Brokerage

class TradeStationClient:
    """
    Central entry point for all TradeStation API modules.
    Aggregates sub-clients such as MarketDataAPI, OrdersAPI, etc.
    """

    def __init__(
        self,
        *,
        token_manager,
    ):
        self.token_manager = token_manager
        
        # Sub-clients share the same TokenManager instance
        self.market_data = MarketDataAPI(token_manager=token_manager)
        self.market_data_stream = MarketDataStream(token_manager=token_manager)
        self.broker = Brokerage(token_manager=token_manager)
        self.broker_stream = BrokerStream(token_manager=token_manager)


