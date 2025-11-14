from src.base_client import BaseAPIClient, BaseStreamClient
from src.endpoints.ts_stream import MarketDataStream, BrokerStream
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def token_manager():
    """
    Provide a mocked TokenManager with stubbed token methods.
    """
    tm = MagicMock()
    tm.get_token.return_value = "valid_token"
    tm.get_token.return_value = "new_token"
    tm.base_api_url = "https://api.tradestation.com/v3"
    return tm


@patch("requests.get")
def test_make_request_refresh_token(mock_get):
    """Ensure token refresh on 401 works correctly."""
    mock_resp_401 = MagicMock(status_code=401)
    mock_resp_ok = MagicMock(status_code=200, json=lambda: {"ok": True})
    mock_get.side_effect = [mock_resp_401, mock_resp_ok]

    token_manager = MagicMock()
    token_manager.get_token.return_value = "newtok"

    api = BaseAPIClient(token_manager)
    res = api.make_request("url", {"Authorization": "Bearer X"}, {})
    assert res == {"ok": True}
    token_manager.get_token.assert_called_once()
    assert mock_get.call_count == 2


@patch.object(BaseStreamClient, "_run_stream")
def test_stream_loop_starts_and_stops(mock_run):
    """Ensure stream_loop runs once and stops when requested."""
    tm = MagicMock()
    client = BaseStreamClient(token_manager=tm)

    def stop_soon(*args, **kwargs):
        client._running = False
    mock_run.side_effect = stop_soon

    client.stream_loop("url", {}, {"Authorization": "t"}, MagicMock())
    mock_run.assert_called_once()


def test_refresh_and_reconnect_triggers_run_stream():
    """
    Ensure _refresh_and_reconnect refreshes token and recalls _run_stream.
    """
    tm = MagicMock()
    tm.get_token.return_value = "fresh"
    client = BaseStreamClient(token_manager=tm)
    client._run_stream = MagicMock()

    client._refresh_and_reconnect("url", {}, {}, MagicMock())
    tm.get_token.assert_called_once()
    client._run_stream.assert_called_once()


@patch.object(BaseStreamClient, "stream_loop")
def test_stream_bars_constructs_url_and_headers(mock_loop):
    """Ensure stream_bars builds correct URL, headers, and params."""
    tm = MagicMock()
    tm.get_token.return_value = "tok"
    api = MarketDataStream(token_manager=tm)

    api.stream_bars(symbol="AAPL", interval=5, unit="Minute", barsback=3)
    mock_loop.assert_called_once()

    call = mock_loop.call_args.kwargs
    assert "AAPL" in call["url"]
    assert call["params"]["interval"] == 5
    assert "Authorization" in call["headers"]
    assert "Accept" in call["headers"]
    assert "on_message" in call


def test_default_message_handler_logs():
    """Ensure default handler logs a valid bar message."""
    tm = MagicMock()
    api = MarketDataStream(token_manager=tm)

    api.logger = MagicMock()  # sostituisci il vero logger con un mock

    msg = {
        "TimeStamp": "2024-11-07T21:00:00Z",
        "Open": "1",
        "High": "2",
        "Low": "0.5",
        "Close": "1.5",
    }

    api._default_message_handler(msg)

    api.logger.info.assert_called_once()
    call_arg = api.logger.info.call_args[0][0]
    assert "O:1" in call_arg
    assert "C:1.5" in call_arg


@patch.object(MarketDataStream, "stream_loop")
def test_stream_quotes_success(mock_stream, caplog):
    """Ensure stream_quotes builds correct URL and headers."""
    tm = MagicMock()
    tm.get_token.return_value = "fake_token"

    api = MarketDataStream(token_manager=tm)
    api._default_message_handler = MagicMock()

    api.stream_quotes(symbols=["AAPL", "MSFT"])

    # Assert stream_loop was called correctly
    mock_stream.assert_called_once()
    call = mock_stream.call_args.kwargs

    # Check URL and headers
    assert "quotes/AAPL,MSFT" in call["url"]
    assert call["headers"]["Authorization"] == "Bearer fake_token"
    assert call["headers"]["Accept"].startswith("application/vnd.tradestation")

    # No params for quotes
    assert call["params"] == {}
    # Default message handler used
    assert call["on_message"] == api._default_message_handler


def test_stream_quotes_raises_no_symbols():
    """Ensure ValueError if symbols list is empty."""
    tm = MagicMock()
    api = MarketDataStream(token_manager=tm)

    with pytest.raises(ValueError, match="At least one symbol"):
        api.stream_quotes(symbols=[])


def test_stream_quotes_raises_too_many_symbols():
    """Ensure ValueError if more than 100 symbols are passed."""
    tm = MagicMock()
    api = MarketDataStream(token_manager=tm)

    symbols = [f"SYM{i}" for i in range(101)]

    with pytest.raises(ValueError, match="Maximum 100 symbols"):
        api.stream_quotes(symbols=symbols)


@patch.object(MarketDataStream, "stream_loop")
def test_stream_market_depth_quotes_success(mock_stream_loop):
    """Ensure market depth stream starts correctly with valid inputs."""
    tm = MagicMock()
    api = MarketDataStream(token_manager=tm)

    api.stream_market_depth_quotes(symbol="AAPL", max_levels=10)

    mock_stream_loop.assert_called_once()
    call = mock_stream_loop.call_args.kwargs

    assert "marketdepth/quotes/AAPL" in call["url"]
    assert call["params"]["maxlevels"] == 10
    assert "Authorization" in call["headers"]
    assert call["headers"]["Accept"].startswith("application/vnd.tradestation")


def test_stream_market_depth_quotes_no_symbol():
    """Ensure ValueError is raised if no symbol is provided."""
    tm = MagicMock()
    api = MarketDataStream(token_manager=tm)

    with pytest.raises(ValueError, match="symbol"):
        api.stream_market_depth_quotes(symbol="")


@patch.object(MarketDataStream, "stream_loop")
def test_stream_market_depth_quotes_valid(mock_stream_loop):
    """Ensure the market depth stream builds correct URL and headers."""
    token_manager = MagicMock()
    token_manager.get_token.return_value = "fake_token"

    stream = MarketDataStream(token_manager=token_manager)

    # Call the method under test
    stream.stream_market_depth_quotes(
        symbol="AAPL",
        max_levels=10,
        on_message=lambda msg: msg,
    )

    # Check that stream_loop was called once
    mock_stream_loop.assert_called_once()
    args, kwargs = mock_stream_loop.call_args

    # Validate URL and headers
    assert "marketdepth/quotes/AAPL" in kwargs["url"]
    assert kwargs["headers"]["Authorization"] == "Bearer fake_token"
    assert kwargs["headers"]["Accept"].startswith(
        "application/vnd.tradestation"
    )

    # Validate params
    params = kwargs["params"]
    assert params["maxlevels"] == 10
    assert callable(kwargs["on_message"])


def test_stream_market_depth_quotes_invalid_symbol():
    """Ensure ValueError is raised when symbol is missing."""
    token_manager = MagicMock()
    stream = MarketDataStream(token_manager=token_manager)

    # Symbol missing → must raise
    try:
        stream.stream_market_depth_quotes(symbol=None)
    except ValueError as e:
        assert "valid symbol" in str(e)
    else:
        raise AssertionError("Expected ValueError for missing symbol")


@patch("time.sleep")
def test_run_stream_sleeps_when_no_data(mock_sleep):
    tm = MagicMock()
    client = BaseStreamClient(token_manager=tm)

    fake_response = MagicMock()
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None
    fake_response.status_code = 200
    fake_response.ok = True
    fake_response.headers = {"Content-Type": "application/json"}
    fake_response.iter_lines.return_value = []

    client._connect = MagicMock(return_value=fake_response)
    client._refresh_and_reconnect = MagicMock()

    client._run_stream("url", {}, {}, MagicMock())

    mock_sleep.assert_called_once()


@patch.object(BrokerStream, "stream_loop")
def test_stream_orders_by_id_valid(mock_stream, token_manager):
    api = BrokerStream(token_manager=token_manager)
    api.stream_orders_by_id(
        accounts=["ACC1"],
        order_ids=["ORD123"],
    )
    mock_stream.assert_called_once()
    args = mock_stream.call_args.kwargs
    assert "ACC1" in args["url"]
    assert "ORD123" in args["url"]


@patch.object(BrokerStream, "stream_loop")
def test_stream_positions_valid(mock_stream, token_manager):
    api = BrokerStream(token_manager=token_manager)
    api.stream_positions(accounts=["ACC1"], changes=True)

    mock_stream.assert_called_once()
    args = mock_stream.call_args.kwargs
    assert "ACC1" in args["url"]
    assert args["params"]["changes"] == "true"
