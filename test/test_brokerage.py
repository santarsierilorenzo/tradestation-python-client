from tradestation_api_python.endpoints.broker import Brokerage
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytest


@pytest.fixture
def token_manager():
    """
    Provide a mocked TokenManager with stubbed token methods.
    """
    tm = MagicMock()
    tm.get_token.return_value = "valid_token"
    tm.refresh_token.return_value = "new_token"
    tm.base_api_url = "https://api.tradestation.com/v3"
    return tm


@patch.object(Brokerage, "make_request")
def test_get_accounts_success(mock_make_request):
    """
    Ensure get_accounts() calls make_request() correctly and
    returns its JSON response.
    """
    mock_make_request.return_value = {
        "Accounts": [{"AccountID": "12345", "Status": "Active"}]
    }

    token_manager = MagicMock()
    token_manager.get_token.return_value = "valid_token"

    api = Brokerage(token_manager=token_manager)
    result = api.get_accounts()

    assert isinstance(result, dict)
    assert "Accounts" in result
    mock_make_request.assert_called_once()

    # Verify the URL and headers passed to make_request
    called_args = mock_make_request.call_args.kwargs
    assert called_args["url"] == (
        "https://api.tradestation.com/v3/brokerage/accounts"
    )
    assert called_args["headers"]["Authorization"] == "Bearer valid_token"
    assert called_args["params"] == {}


@patch.object(Brokerage, "make_request", side_effect=Exception("API error"))
def test_get_accounts_failure(mock_make_request):
    """
    Ensure get_accounts() propagates exceptions from make_request().
    """
    token_manager = MagicMock()
    token_manager.get_token.return_value = "valid_token"

    api = Brokerage(token_manager=token_manager)
    with pytest.raises(Exception, match="API error"):
        api.get_accounts()


@patch.object(Brokerage, "make_request")
def test_get_accounts_success(mock_make, token_manager):
    """
    Ensure get_accounts() calls make_request() correctly and returns data.
    """
    mock_make.return_value = {"Accounts": [{"AccountID": "12345"}]}

    api = Brokerage(token_manager=token_manager)
    result = api.get_accounts()

    assert isinstance(result, dict)
    assert "Accounts" in result
    mock_make.assert_called_once()

    args = mock_make.call_args.kwargs
    assert args["url"] == "https://api.tradestation.com/v3/brokerage/accounts"
    assert args["headers"]["Authorization"] == "Bearer valid_token"
    assert args["params"] == {}


@patch.object(Brokerage, "make_request", side_effect=Exception("API error"))
def test_get_accounts_failure(mock_make, token_manager):
    """
    Ensure get_accounts() propagates exceptions from make_request().
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(Exception, match="API error"):
        api.get_accounts()


@patch.object(Brokerage, "make_request")
def test_get_balances_success(mock_make, token_manager):
    """
    Ensure get_balances() builds URL correctly and returns data.
    """
    mock_make.return_value = {"Balances": [{"AccountID": "12345"}]}

    api = Brokerage(token_manager=token_manager)
    result = api.get_balances(accounts=["12345", "67890"])

    assert isinstance(result, dict)
    assert "Balances" in result
    mock_make.assert_called_once()

    called_url = mock_make.call_args.kwargs["url"]
    assert "12345" in called_url and "67890" in called_url
    assert called_url.startswith(
        "https://api.tradestation.com/v3/brokerage/accounts/"
    )
    assert called_url.endswith("/balances")


def test_get_balances_empty_list(token_manager):
    """
    Ensure get_balances() raises on empty account list.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="At least one account"):
        api.get_balances(accounts=[])


def test_get_balances_too_many_accounts(token_manager):
    """
    Ensure get_balances() raises if more than 100 accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="Maximum 100 accounts"):
        api.get_balances(accounts=["acc"] * 101)


@patch.object(Brokerage, "make_request")
def test_get_balances_bod_success(mock_make, token_manager):
    """
    Ensure get_balances_bod() builds URL correctly and returns data.
    """
    mock_make.return_value = {"BODBalances": [{"AccountID": "ACC1"}]}

    api = Brokerage(token_manager=token_manager)
    result = api.get_balances_bod(accounts=["ACC1", "ACC2"])

    assert isinstance(result, dict)
    assert "BODBalances" in result
    mock_make.assert_called_once()

    called_url = mock_make.call_args.kwargs["url"]
    assert called_url.startswith(
        "https://api.tradestation.com/v3/brokerage/accounts/"
    )
    assert called_url.endswith("/bodbalances")
    assert "ACC1" in called_url and "ACC2" in called_url
    assert called_url.count(",") == 1  # Comma separation check


def test_get_balances_bod_empty_list(token_manager):
    """
    Ensure get_balances_bod() raises on empty account list.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="At least one account"):
        api.get_balances_bod(accounts=[])


def test_get_balances_bod_too_many_accounts(token_manager):
    """
    Ensure get_balances_bod() raises if more than 100 accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="Maximum 100 accounts"):
        api.get_balances_bod(accounts=["ACC"] * 101)


@patch.object(Brokerage, "make_request")
def test_get_historical_orders_success(mock_make, token_manager):
    """
    Ensure get_historical_orders() builds URL and params correctly
    for valid inputs.
    """
    mock_make.return_value = {"Orders": [{"OrderID": "O123"}]}

    api = Brokerage(token_manager=token_manager)
    recent_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    result = api.get_historical_orders(
        accounts=["ACC1"],
        since=recent_date,
        page_size=100,
        next_token="abc"
    )

    assert isinstance(result, dict)
    assert "Orders" in result
    mock_make.assert_called_once()

    call = mock_make.call_args.kwargs
    assert "ACC1" in call["url"]
    assert call["url"].endswith("/historicalorders")
    assert call["params"]["since"] == recent_date
    assert call["params"]["pageSize"] == 100
    assert call["params"]["nextToken"] == "abc"


@patch.object(Brokerage, "make_request")
def test_get_historical_orders_valid_date_format(mock_make, token_manager):
    """
    Ensure get_historical_orders() accepts only valid 'YYYY-MM-DD' dates.
    """
    mock_make.return_value = {"Orders": []}
    api = Brokerage(token_manager=token_manager)

    # Use a recent valid date
    recent_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    api.get_historical_orders(
        accounts=["ACC1"],
        since=recent_date,
    )

    call = mock_make.call_args.kwargs
    assert call["params"]["since"] == recent_date


def test_get_historical_orders_invalid_date_format(token_manager):
    """
    Ensure invalid date formats raise ValueError (e.g., full ISO timestamps).
    """
    api = Brokerage(token_manager=token_manager)

    # Invalid ISO with time component
    with pytest.raises(ValueError):
        api.get_historical_orders(
            accounts=["ACC1"],
            since="2024-11-09T00:00:00Z",
        )

    # Invalid date format with slashes
    with pytest.raises(ValueError):
        api.get_historical_orders(
            accounts=["ACC1"],
            since="2024/11/09",
        )


def test_get_historical_orders_date_too_old(token_manager):
    """
    Ensure ValueError is raised when 'since' exceeds the 90-day limit.
    """
    api = Brokerage(token_manager=token_manager)
    old_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")

    with pytest.raises(ValueError, match="must be within the past 90 days"):
        api.get_historical_orders(accounts=["ACC1"], since=old_date)


def test_get_historical_orders_empty_accounts(token_manager):
    """
    Ensure ValueError is raised when no accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    recent_date = datetime.now().strftime("%Y-%m-%d")

    with pytest.raises(ValueError, match="At least one account"):
        api.get_historical_orders(accounts=[], since=recent_date)


def test_get_historical_orders_too_many_accounts(token_manager):
    """
    Ensure ValueError is raised when more than 100 accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    recent_date = datetime.now().strftime("%Y-%m-%d")

    too_many = [f"A{i}" for i in range(101)]
    with pytest.raises(ValueError, match="Maximum 100 accounts"):
        api.get_historical_orders(accounts=too_many, since=recent_date)


@patch.object(Brokerage, "make_request")
def test_get_historical_orders_by_id_success(mock_make, token_manager):
    """
    Ensure get_historical_orders_by_id() builds correct URL and params.
    """
    mock_make.return_value = {"Orders": [{"OrderID": "ORD123"}]}

    api = Brokerage(token_manager=token_manager)
    recent_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    result = api.get_historical_orders_by_id(
        accounts=["ACC1"],
        order_ids=["ORD123"],
        since=recent_date,
    )

    assert isinstance(result, dict)
    assert "Orders" in result

    mock_make.assert_called_once()
    call = mock_make.call_args.kwargs
    assert "ACC1" in call["url"]
    assert "ORD123" in call["url"]
    assert call["params"]["since"] == recent_date


def test_get_historical_orders_by_id_empty_accounts(token_manager):
    """
    Ensure ValueError is raised when no accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    date_str = datetime.now().strftime("%Y-%m-%d")

    with pytest.raises(ValueError, match="At least one account"):
        api.get_historical_orders_by_id(
            accounts=[], order_ids=["O1"], since=date_str
        )


def test_get_historical_orders_by_id_empty_order_ids(token_manager):
    """
    Ensure ValueError is raised when no order IDs are provided.
    """
    api = Brokerage(token_manager=token_manager)
    date_str = datetime.now().strftime("%Y-%m-%d")

    with pytest.raises(ValueError, match="At least one order ID"):
        api.get_historical_orders_by_id(
            accounts=["ACC1"], order_ids=[], since=date_str
        )


def test_get_historical_orders_by_id_too_many_accounts(token_manager):
    """
    Ensure ValueError is raised when more than 100 accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    date_str = datetime.now().strftime("%Y-%m-%d")
    too_many = [f"A{i}" for i in range(101)]

    with pytest.raises(ValueError, match="Maximum 100 accounts"):
        api.get_historical_orders_by_id(
            accounts=too_many, order_ids=["O1"], since=date_str
        )


def test_get_historical_orders_by_id_too_many_order_ids(token_manager):
    """
    Ensure ValueError is raised when more than 100 order IDs are provided.
    """
    api = Brokerage(token_manager=token_manager)
    date_str = datetime.now().strftime("%Y-%m-%d")
    too_many = [f"O{i}" for i in range(101)]

    with pytest.raises(ValueError, match="Maximum 100 order IDs"):
        api.get_historical_orders_by_id(
            accounts=["ACC1"], order_ids=too_many, since=date_str
        )


def test_get_historical_orders_by_id_date_too_old(token_manager):
    """
    Ensure ValueError raised when 'since' exceeds 90-day limit.
    """
    api = Brokerage(token_manager=token_manager)
    old_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")

    with pytest.raises(ValueError, match="within the past 90 days"):
        api.get_historical_orders_by_id(
            accounts=["ACC1"], order_ids=["O1"], since=old_date
        )


@patch.object(Brokerage, "make_request")
def test_get_orders_success(mock_make, token_manager):
    """
    Ensure get_orders() constructs URL and params correctly.
    """
    mock_make.return_value = {"Orders": [{"OrderID": "O123"}]}

    api = Brokerage(token_manager=token_manager)
    result = api.get_orders(
        accounts=["ACC1"],
        page_size=100,
        next_token="tok123"
    )

    assert isinstance(result, dict)
    assert "Orders" in result
    mock_make.assert_called_once()

    call = mock_make.call_args.kwargs
    assert "ACC1" in call["url"]
    assert call["url"].endswith("/orders")
    assert call["params"]["pageSize"] == 100
    assert call["params"]["nextToken"] == "tok123"


def test_get_orders_empty_accounts(token_manager):
    """
    Ensure ValueError raised when no accounts provided.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="At least one account"):
        api.get_orders(accounts=[])


def test_get_orders_too_many_accounts(token_manager):
    """
    Ensure ValueError raised when >100 accounts provided.
    """
    api = Brokerage(token_manager=token_manager)
    too_many = [f"ACC{i}" for i in range(101)]

    with pytest.raises(ValueError, match="Maximum 100 accounts"):
        api.get_orders(accounts=too_many)


@patch.object(Brokerage, "make_request")
def test_get_orders_by_id_success(mock_make, token_manager):
    """
    Ensure get_orders_by_id() builds URL and calls make_request correctly.
    """
    mock_make.return_value = {"Orders": [{"OrderID": "O123"}]}

    api = Brokerage(token_manager=token_manager)
    result = api.get_orders_by_id(
        accounts=["ACC1"],
        order_ids=["O123"],
    )

    assert isinstance(result, dict)
    assert "Orders" in result
    mock_make.assert_called_once()

    call = mock_make.call_args.kwargs
    assert "ACC1" in call["url"]
    assert "O123" in call["url"]
    assert call["url"].endswith("/orders/O123")


def test_get_orders_by_id_empty_accounts(token_manager):
    """
    Ensure ValueError raised when no accounts provided.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="At least one account"):
        api.get_orders_by_id(accounts=[], order_ids=["O1"])


def test_get_orders_by_id_empty_order_ids(token_manager):
    """
    Ensure ValueError raised when no order IDs provided.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="At least one order ID"):
        api.get_orders_by_id(accounts=["ACC1"], order_ids=[])


def test_get_orders_by_id_too_many_accounts(token_manager):
    """
    Ensure ValueError raised when >100 accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    too_many = [f"A{i}" for i in range(101)]

    with pytest.raises(ValueError, match="Maximum 100 accounts"):
        api.get_orders_by_id(accounts=too_many, order_ids=["O1"])


def test_get_orders_by_id_too_many_order_ids(token_manager):
    """
    Ensure ValueError raised when >100 order IDs are provided.
    """
    api = Brokerage(token_manager=token_manager)
    too_many = [f"O{i}" for i in range(101)]

    with pytest.raises(ValueError, match="Maximum 100 order IDs"):
        api.get_orders_by_id(accounts=["ACC1"], order_ids=too_many)


@patch.object(Brokerage, "make_request")
def test_get_positions_success(mock_make, token_manager):
    """
    Ensure get_positions() constructs URL and params correctly.
    """
    mock_make.return_value = {"Positions": [{"Symbol": "AAPL"}]}

    api = Brokerage(token_manager=token_manager)
    result = api.get_positions(
        accounts=["ACC1"],
        symbol=["AAPL"]
    )

    assert isinstance(result, dict)
    assert "Positions" in result
    mock_make.assert_called_once()

    call = mock_make.call_args.kwargs
    assert "ACC1" in call["url"]
    assert call["url"].endswith("/positions")
    assert call["params"]["symbol"] == ["AAPL"]


def test_get_positions_empty_accounts(token_manager):
    """
    Ensure ValueError raised when no accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    with pytest.raises(ValueError, match="At least one account"):
        api.get_positions(accounts=[])


def test_get_positions_too_many_accounts(token_manager):
    """
    Ensure ValueError raised when more than 100 accounts are provided.
    """
    api = Brokerage(token_manager=token_manager)
    too_many = [f"A{i}" for i in range(101)]

    with pytest.raises(ValueError, match="Maximum 100 accounts"):
        api.get_positions(accounts=too_many)
