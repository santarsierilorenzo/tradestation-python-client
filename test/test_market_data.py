from src.endpoints.market_data import MarketDataAPI
from unittest.mock import MagicMock, patch
import requests
import pytest


@pytest.fixture
def token_manager():
    """
    Provide a mocked TokenManager with stubbed token methods.
    """
    tm = MagicMock()
    tm.get_token.return_value = "valid_token"
    tm.refresh_token.return_value = "new_token"
    return tm


@patch("src.endpoints.market_data.requests.get")
def test_make_request_success(mock_get, token_manager):
    """
    Verify that make_request() handles a 200 OK and returns JSON data.
    """
    # Mock a valid HTTP 200 response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Bars": [{"Time": "2024-01-01"}]}
    mock_get.return_value = mock_resp

    api = MarketDataAPI(token_manager=token_manager)

    result = api.make_request(
        "url", {"Authorization": "Bearer X"}, {"interval": 1}
    )

    assert "Bars" in result
    mock_get.assert_called_once()


@patch("src.endpoints.market_data.requests.get")
def test_make_request_refresh_token(mock_get, token_manager):
    """
    Ensure make_request() refreshes token on 401 and retries once.
    """
    # First call fails with 401 Unauthorized
    first = MagicMock()
    first.status_code = 401
    first.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Unauthorized"
    )

    # Second call succeeds with 200 OK
    second = MagicMock()
    second.status_code = 200
    second.raise_for_status.return_value = None
    second.json.return_value = {"Bars": [{"Time": "2024-01-01"}]}

    mock_get.side_effect = [first, second]

    api = MarketDataAPI(token_manager=token_manager)
    res = api.make_request(
        "url", {"Authorization": "Bearer X"}, {"interval": 1}
    )

    assert isinstance(res, dict)
    assert res["Bars"][0]["Time"] == "2024-01-01"
    token_manager.refresh_token.assert_called_once()


@patch("src.endpoints.market_data.requests.get")
def test_make_request_raises_non_401(mock_get, token_manager):
    """
    Check that make_request() raises for HTTP errors other than 401.
    """
    # Simulate a 500 Internal Server Error
    resp = MagicMock()
    resp.status_code = 500
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Internal Server Error"
    )
    mock_get.return_value = resp

    api = MarketDataAPI(token_manager=token_manager)

    with pytest.raises(requests.exceptions.HTTPError):
        api.make_request("url", {"Authorization": "Bearer X"}, {"interval": 1})
