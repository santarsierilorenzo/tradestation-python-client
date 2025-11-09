from src.endpoints.brokerage import Brokerage
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def token_manager():
    tm = MagicMock()
    tm.get_token.return_value = "valid_token"
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
