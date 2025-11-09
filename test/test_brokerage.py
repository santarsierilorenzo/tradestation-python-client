from src.endpoints.brokerage import Brokerage
from unittest.mock import patch, MagicMock
import pytest


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
