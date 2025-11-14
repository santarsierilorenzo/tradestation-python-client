from unittest.mock import MagicMock, patch
from src.base_client import BaseAPIClient
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


@patch("src.base_client.requests.get")
def test_make_request_refresh_token(mock_get):
    tm = MagicMock()
    tm.get_token.return_value = "new_token"

    first = MagicMock(status_code=401)
    second = MagicMock(status_code=200)
    second.json.return_value = {"ok": True}
    mock_get.side_effect = [first, second]

    api = BaseAPIClient(token_manager=tm)
    res = api.make_request("url", {"Authorization": "Bearer old"}, {})

    assert res == {"ok": True}
    tm.get_token.assert_called_once()
    mock_get.assert_called()