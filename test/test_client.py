from unittest.mock import MagicMock, patch
from src.client import TradeStationClient
import pytest


@patch("src.client.MarketDataAPI")
def test_client_initializes_market_data(mock_market_data):
    """
    Ensure TradeStationClient correctly instantiates MarketDataAPI
    using the provided TokenManager.
    """
    token_manager = MagicMock()
    client = TradeStationClient(token_manager=token_manager)

    assert client.token_manager is token_manager

    # Verify MarketDataAPI was created with the same token manager
    mock_market_data.assert_called_once_with(token_manager=token_manager)

    # The market_data attribute should be the mocked instance
    assert client.market_data == mock_market_data.return_value
