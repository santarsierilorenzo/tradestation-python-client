from tradestation_python_client.client import TradeStationClient
from tradestation_python_client.auth import TokenManager
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

if __name__ == "__main__":
    # Creare un istanza condivisa di TokenManager.
    token_manager = TokenManager(use_sim=True)

    # Facade Pattern, TradeStationClient is an entry point.
    ts_client = TradeStationClient(
        token_manager=token_manager
    )

    ts_client.market_data_stream.stream_quotes(
        symbols=["AAPL"],
    )
