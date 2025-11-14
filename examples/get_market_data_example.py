from tradestation_python_client.client import TradeStationClient
from tradestation_python_client.auth import TokenManager

if __name__ == "__main__":
    # Create shared instance of TokenManager
    token_manager = TokenManager(use_sim=True)

    # Facade Pattern, TradeStationClient is an entry point.
    ts_client = TradeStationClient(
        token_manager=token_manager
    )

    # Get bars between a range of dates
    data1 = ts_client.market_data.get_bars_between(
        symbol="AAPL",
        first_date="2025-01-01",
        interval=1,
        unit="Minute",
        max_workers=15,
    )

    # Get bars back from a last date
    data2 = ts_client.market_data.get_bars(
        symbol="AAPL",
        barsback=100,
        last_date="2020-01-01",
        interval=1,
        unit="Minute",
    )

    # Get symbols detail
    symbols_detail = ts_client.market_data.get_symbol_details(
        symbols=["AAPL", "MSFT"]
    )

