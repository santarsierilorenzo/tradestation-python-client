from src.endpoints.mkt_data import MarketDataAPI
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


@patch("src.endpoints.mkt_data.requests.get")
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


@patch("src.endpoints.mkt_data.requests.get")
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


@patch("src.endpoints.mkt_data.requests.get")
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


def test_get_bars_between_invalid_date_order(token_manager):
    """
    Ensure get_bars_between() raises if first_date > last_date.
    """
    api = MarketDataAPI(token_manager=token_manager)

    with pytest.raises(Exception, match="first_data can't be greater"):
        api.get_bars_between(
            symbol="MSFT",
            first_date="2024-12-01",
            last_date="2024-01-01",
            unit="Daily",
        )


@pytest.fixture
def token_manager():
    """
    Provide a mocked TokenManager with stubbed token methods.
    """
    tm = MagicMock()
    tm.get_token.return_value = "valid_token"
    tm.refresh_token.return_value = "new_token"
    return tm


@patch("src.endpoints.mkt_data.requests.get")
def test_make_request_success(mock_get, token_manager):
    """
    Verify make_request() handles a 200 OK and returns JSON data.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Bars": [{"Time": "2024-01-01"}]}
    mock_get.return_value = mock_resp

    api = MarketDataAPI(token_manager=token_manager)
    result = api.make_request("url", {"Authorization": "Bearer X"},
                              {"interval": 1})

    assert "Bars" in result
    mock_get.assert_called_once()


@patch("src.endpoints.mkt_data.requests.get")
def test_make_request_refresh_token(mock_get, token_manager):
    """
    Ensure make_request() refreshes token on 401 and retries once.
    """
    first = MagicMock()
    first.status_code = 401
    first.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Unauthorized"
    )

    second = MagicMock()
    second.status_code = 200
    second.raise_for_status.return_value = None
    second.json.return_value = {"Bars": [{"Time": "2024-01-01"}]}
    mock_get.side_effect = [first, second]

    api = MarketDataAPI(token_manager=token_manager)
    res = api.make_request("url", {"Authorization": "Bearer X"},
                           {"interval": 1})

    assert res["Bars"][0]["Time"] == "2024-01-01"
    token_manager.refresh_token.assert_called_once()


@patch("src.endpoints.mkt_data.requests.get")
def test_make_request_raises_non_401(mock_get, token_manager):
    """
    Check make_request() raises errors other than 401.
    """
    resp = MagicMock()
    resp.status_code = 500
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Internal Server Error"
    )
    mock_get.return_value = resp

    api = MarketDataAPI(token_manager=token_manager)

    with pytest.raises(requests.exceptions.HTTPError):
        api.make_request("url", {"Authorization": "Bearer X"},
                         {"interval": 1})


@patch.object(MarketDataAPI, "make_request")
def test_get_bars_success(mock_make, token_manager):
    """
    Verify get_bars() builds params correctly and returns API data.
    """
    mock_make.return_value = {"Bars": [{"Time": "2024-01-01"}]}
    api = MarketDataAPI(token_manager=token_manager)

    result = api.get_bars(symbol="MSFT", barsback=50, unit="Daily")
    assert "Bars" in result
    mock_make.assert_called_once()
    call_args = mock_make.call_args[1]["params"]
    assert call_args["unit"] == "Daily"
    assert call_args["barsback"] == 50


def test_get_bars_invalid_barsback(token_manager):
    """
    Ensure get_bars() raises if barsback exceeds 57,600.
    """
    api = MarketDataAPI(token_manager=token_manager)
    with pytest.raises(ValueError):
        api.get_bars(symbol="MSFT", barsback=100000)


@patch.object(MarketDataAPI, "make_request")
def test_get_bars_between_single_request(mock_make, token_manager):
    """
    Validate get_bars_between() makes one request for small ranges.
    """
    mock_make.return_value = {"Bars": [{"Time": "2024-01-01"}]}
    api = MarketDataAPI(token_manager=token_manager)
    res = api.get_bars_between(symbol="MSFT",
                               first_date="2024-01-01",
                               last_date="2024-01-05",
                               unit="Daily")
    assert "Bars" in res
    mock_make.assert_called_once()


def test_get_bars_between_invalid_unit(token_manager):
    """
    Ensure get_bars_between() raises ValueError for invalid units.
    """
    api = MarketDataAPI(token_manager=token_manager)
    with pytest.raises(ValueError):
        api.get_bars_between(symbol="MSFT",
                             first_date="2024-01-01",
                             unit="Hourly")


def test_get_symbol_details_valid(token_manager):
    """
    Ensure get_symbol_details() calls make_request() with the right URL
    and headers when valid symbols are provided.
    """
    with patch.object(MarketDataAPI, "make_request") as mock_req:
        mock_req.return_value = {"AAPL": {"Description": "Apple Inc."}}
        api = MarketDataAPI(token_manager=token_manager)

        res = api.get_symbol_details(symbols=["AAPL", "MSFT"])

        assert isinstance(res, dict)
        mock_req.assert_called_once()
        called_url = mock_req.call_args.kwargs["url"]
        assert "AAPL" in called_url and "MSFT" in called_url


def test_get_symbol_details_empty_list(token_manager):
    """
    Ensure get_symbol_details() raises if no symbols are given.
    """
    api = MarketDataAPI(token_manager=token_manager)
    with pytest.raises(ValueError, match="At least one symbol"):
        api.get_symbol_details(symbols=[])


def test_get_symbol_details_too_many_symbols(token_manager):
    """
    Ensure get_symbol_details() raises if more than 100 symbols are passed.
    """
    api = MarketDataAPI(token_manager=token_manager)
    with pytest.raises(ValueError, match="Maximum 100 symbols"):
        api.get_symbol_details(symbols=["SYM"] * 101)


@patch.object(MarketDataAPI, "make_request")
def test_get_crypto_symbol_names_calls_correct_url(mock_make, token_manager):
    mock_make.return_value = {"symbols": ["BTCUSD", "ETHUSD"]}
    api = MarketDataAPI(token_manager=token_manager)

    result = api.get_crypto_symbol_names()

    mock_make.assert_called_once()
    call = mock_make.call_args.kwargs
    assert "cryptopairs/symbolnames" in call["url"]
    assert call["headers"]["Authorization"].startswith("Bearer ")
    assert result == {"symbols": ["BTCUSD", "ETHUSD"]}


@patch.object(MarketDataAPI, "make_request")
def test_get_quote_snapshots_minimal(mock_make, token_manager):
    mock_make.return_value = {"AAPL": {"Last": 150.0}}
    api = MarketDataAPI(token_manager=token_manager)

    result = api.get_quote_snapshots(symbols=["AAPL"])

    mock_make.assert_called_once()
    call = mock_make.call_args.kwargs
    assert "quotes/AAPL" in call["url"]
    assert "Authorization" in call["headers"]
    assert result == {"AAPL": {"Last": 150.0}}
