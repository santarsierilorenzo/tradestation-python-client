from src.client import TradeStationClient
from src.auth import TokenManager

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Create shared instance of TokenManager
    token_manager = TokenManager()

    # Facade Pattern, TradeStationClient is an entry point.
    ts_client = TradeStationClient(
        token_manager=token_manager
    )

    data = ts_client.market_data.get_bars_between(
        symbol="AAPL",
        first_date="2020-01-01",
        interval=1,
        unit="Minute",
        max_workers=15,
    )


