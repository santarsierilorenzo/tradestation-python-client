from ..base_client import BaseAPIClient
from typing import Dict, Optional
from datetime import datetime
import requests


class Brokerage(BaseAPIClient):
    """
    Provides access to TradeStation Brokerage API endpoints.

    This class handles requests related to user brokerage data such as
    account information, balances, and trading permissions.
    It inherits from `BaseAPIClient` to leverage the shared
    HTTP request and token management logic.

    Attributes
    ----------
    token_manager : TokenManager
        Object responsible for providing and refreshing OAuth tokens.
    """

    def __init__(
        self,
        *,
        token_manager
    ) -> None:
        """
        Initialize a Brokerage API client.

        Parameters
        ----------
        token_manager : TokenManager
            Instance managing authentication tokens for API requests.
        """
        self.token_manager = token_manager

    def get_accounts(self) -> Dict:
        """
        Retrieve the list of brokerage accounts associated with the
        authenticated user.

        Returns
        -------
        dict
            JSON response containing available accounts, each typically
            including:
              - `AccountID`: Unique account identifier
              - `AccountType`: Account category (e.g., Individual, IRA)
              - `Description`: Human-readable name or label
              - `Status`: Current account status (Active, Closed, etc.)

        Raises
        ------
        requests.exceptions.RequestException
            If the HTTP request fails or the API returns an error response.

        Notes
        -----
        - Requires a valid access token.
        - Data returned may vary based on account type and permissions.
        """
        url = f"{self.token_manager.base_api_url}/brokerage/accounts"
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = self.make_request(
            url=url,
            headers=headers,
            params={}
        )

        return response

    def get_balances(
        self,
        *,
        accounts: list[str]
    ) -> Dict:
        """
        Retrieve account balances for one or more specified accounts.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs to query (max 100).

        Returns
        -------
        dict
            JSON response containing balance data for each account,
            including typical fields such as:
              - `AccountID`: Account identifier
              - `CashBalance`: Current cash available
              - `NetWorth`: Total account value
              - `MarginBalance`: Outstanding margin balance

        Raises
        ------
        ValueError
            If no accounts are provided or more than 100 accounts are passed.
        requests.exceptions.RequestException
            If the HTTP request fails or the API returns an error.

        Notes
        -----
        - Input accounts are URL-encoded automatically.
        - Requires a valid access token.
        """
        if not accounts:
            raise ValueError("At least one account must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")

        accounts_as_str = ",".join(
            [requests.utils.quote(acc.strip()) for acc in accounts]
        )

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/balances"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = self.make_request(
            url=url,
            headers=headers,
            params={}
        )

        return response

    def get_balances_bod(
        self,
        *,
        accounts: list[str]
    ) -> Dict:
        """
        Retrieve the Beginning-of-Day (BOD) balances for the specified accounts.

        This endpoint returns the account balances as they were at the
        start of the current trading day. Supported for Cash, Margin,
        Futures, and DVP account types.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs to query (maximum 100).

        Returns
        -------
        dict
            JSON response containing BOD balances for each account,
            typically including:
            - `AccountID`: Unique account identifier
            - `CashBalance`: Opening cash balance
            - `NetWorth`: Account value at session open
            - `MarginBalance`: Margin balance at open

        Raises
        ------
        ValueError
            If no accounts are provided or more than 100 accounts are passed.
        requests.exceptions.RequestException
            If the HTTP request fails or the API returns an error.

        Notes
        -----
        - Use this method for static, session-start account snapshots.
        - Requires a valid access token.
        """
        if not accounts:
            raise ValueError("At least one account must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")

        accounts_as_str = ",".join(
            [requests.utils.quote(acc.strip()) for acc in accounts]
        )

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/bodbalances"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = self.make_request(
            url=url,
            headers=headers,
            params={}
        )

        return response

    def get_historical_orders(
        self,
        *,
        accounts: list[str],
        since: str,
        page_size: Optional[int] = 600,
        next_token: Optional[str] = None,
    ) -> Dict:
        """
        Retrieve historical (closed) orders for the given accounts.

        This endpoint returns all historical orders except open ones,
        sorted in descending order by close time. The request is valid for
        all account types.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs to query (maximum 100).
        since : str
            Date string in 'YYYY-MM-DD' format indicating the earliest
            close time to include. Must be within the past 90 days.
        page_size : int, optional, default=600
            Maximum number of records to return per page.
        next_token : str, optional
            Continuation token for paginated results (if applicable).

        Returns
        -------
        dict
            JSON response containing historical orders. Each entry may include:
              - `OrderID`: Unique identifier of the order.
              - `Symbol`: Traded instrument.
              - `Quantity`: Size of the trade.
              - `ClosedDateTime`: When the order was closed.

        Raises
        ------
        ValueError
            If no accounts are provided, more than 100 are specified,
            or 'since' is older than 90 days.
        requests.exceptions.RequestException
            If the HTTP request fails or the API returns an error.

        Notes
        -----
        - Orders are returned in descending chronological order.
        - The 'since' parameter cannot exceed 90 days before today.
        - Use 'next_token' for pagination.
        - Requires a valid access token.
        """

        if not accounts:
            raise ValueError("At least one account must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")
        
        date_since = datetime.strptime(since, "%Y-%m-%d").date()
        if (datetime.now().date() - date_since).days > 90:
            raise ValueError("`since` must be within the past 90 days.")

        accounts_as_str = ",".join(
            [requests.utils.quote(acc.strip()) for acc in accounts]
        )

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/historicalorders"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "since": since,
            "pageSize": page_size,
            "nextToken": next_token,
        }
        params = {k: v for k, v in params.items() if v is not None}

        response = self.make_request(
            url=url,
            headers=headers,
            params=params
        )

        return response

    def get_historical_orders_by_id(
        self,
        *,
        accounts: list[str],
        order_ids: list[str],
        since: str,
    ) -> Dict:
        """
        Retrieve specific historical orders by ID for given accounts.

        This endpoint returns details of closed (non-open) orders matching
        the provided order IDs. The query is valid for all account types.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs to query (maximum 100).
        order_ids : list of str
            One or more order IDs to retrieve (maximum 100).
        since : str
            Date string in 'YYYY-MM-DD' format, must be within
            the past 90 days.

        Returns
        -------
        dict
            JSON response containing the matching historical orders.
            Each entry typically includes:
            - `OrderID`: Unique order identifier
            - `Symbol`: Traded instrument
            - `Quantity`: Order size
            - `ClosedDateTime`: When the order was closed

        Raises
        ------
        ValueError
            If `accounts` or `order_ids` are empty or exceed 100,
            or if `since` is older than 90 days.
        requests.exceptions.RequestException
            If the HTTP request fails or the API returns an error.

        Notes
        -----
        - Orders are returned in descending close-time order.
        - Requires a valid access token.
        """
        if not accounts:
            raise ValueError("At least one account must be provided.")

        if not order_ids:
            raise ValueError("At least one order ID must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")

        if len(order_ids) > 100:
            raise ValueError("Maximum 100 order IDs allowed per request.")

        date_since = datetime.strptime(since, "%Y-%m-%d").date()
        if (datetime.now().date() - date_since).days > 90:
            raise ValueError("`since` must be within the past 90 days.")

        accounts_as_str = ",".join(
            [requests.utils.quote(acc.strip()) for acc in accounts]
        )

        ids_as_str = ",".join(
            [requests.utils.quote(oid.strip()) for oid in order_ids]
        )

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/historicalorders/{ids_as_str}"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        params = {"since": since}

        response = self.make_request(
            url=url,
            headers=headers,
            params=params
        )

        return response
    
    def get_orders(
        self,
        *,
        accounts: list[str],
        page_size: Optional[int] = 600,
        next_token: Optional[str] = None,
    ) -> Dict:
        """
        Retrieve today's and open orders for the given accounts.

        This endpoint returns all open orders and today's executed orders,
        sorted in descending order by time placed (open) or time executed
        (closed). The request is valid for all account types.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs to query (maximum 100).
        page_size : int, optional, default=600
            Maximum number of records returned per page.
        next_token : str, optional
            Continuation token for paginated results.

        Returns
        -------
        dict
            JSON response containing orders. Each entry typically includes:
            - `OrderID`: Unique identifier
            - `Symbol`: Traded instrument
            - `Status`: Open, Filled, or Canceled
            - `TimePlaced` / `TimeExecuted`: Timestamps

        Raises
        ------
        ValueError
            If `accounts` is empty or exceeds 100 items.
        requests.exceptions.RequestException
            If the HTTP request fails or returns an error response.

        Notes
        -----
        - Open and today's orders are returned.
        - Use `next_token` for pagination.
        - Requires a valid access token.
        """
        if not accounts:
            raise ValueError("At least one account must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")

        accounts_as_str = ",".join(
            [requests.utils.quote(acc.strip()) for acc in accounts]
        )

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/orders"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "pageSize": page_size,
            "nextToken": next_token,
        }
        params = {k: v for k, v in params.items() if v is not None}

        response = self.make_request(
            url=url,
            headers=headers,
            params=params
        )

        return response

    def get_orders_by_id(
        self,
        *,
        accounts: list[str],
        order_ids: list[str],
    ) -> Dict:
        """
        Retrieve today's and open orders filtered by specific order IDs.

        This endpoint returns open orders and today's executed orders for
        the specified accounts, limited to the provided list of order IDs.
        The results are sorted in descending order by time placed (open)
        or time executed (closed). Valid for all account types.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs to query (maximum 100).
        order_ids : list of str
            One or more order IDs to filter (maximum 100).

        Returns
        -------
        dict
            JSON response containing the filtered orders. Each entry
            typically includes:
            - `OrderID`: Unique identifier
            - `Symbol`: Traded instrument
            - `Status`: Open, Filled, or Canceled
            - `TimePlaced` / `TimeExecuted`: Timestamps

        Raises
        ------
        ValueError
            If `accounts` or `order_ids` are empty or exceed 100 items.
        requests.exceptions.RequestException
            If the HTTP request fails or the API returns an error.

        Notes
        -----
        - Only today's and open orders are returned.
        - Requires a valid access token.
        """
        if not accounts:
            raise ValueError("At least one account must be provided.")

        if not order_ids:
            raise ValueError("At least one order ID must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")

        if len(order_ids) > 100:
            raise ValueError("Maximum 100 order IDs allowed per request.")

        accounts_as_str = ",".join(
            [requests.utils.quote(acc.strip()) for acc in accounts]
        )

        ids_as_str = ",".join(
            [requests.utils.quote(oid.strip()) for oid in order_ids]
        )

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/orders/{ids_as_str}"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = self.make_request(
            url=url,
            headers=headers,
            params={}
        )

        return response
    
    def get_positions(
        self,
        *,
        accounts: list[str],
        symbol: list[str] = None,
    ) -> Dict:
        """
        Retrieve open positions for the given accounts.

        This endpoint fetches position data for the specified accounts,
        optionally filtered by one or more symbols. It supports Cash,
        Margin, Futures, and DVP account types.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs to query (maximum 100).
        symbol : list of str, optional
            One or more symbols to filter positions (e.g. ["AAPL", "MSFT"]).

        Returns
        -------
        dict
            JSON response containing position data. Each entry typically
            includes:
            - `Symbol`: Traded instrument
            - `Quantity`: Position size
            - `AveragePrice`: Average entry price
            - `UnrealizedPL`: Unrealized profit/loss

        Raises
        ------
        ValueError
            If `accounts` is empty or exceeds 100 items.
        requests.exceptions.RequestException
            If the HTTP request fails or the API returns an error.

        Notes
        -----
        - Accepts both equity and futures accounts.
        - The optional `symbol` parameter can be used to limit the scope
        of returned positions.
        """
        if not accounts:
            raise ValueError("At least one account must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")

        accounts_as_str = ",".join(
            [requests.utils.quote(acc.strip()) for acc in accounts]
        )

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/positions"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "symbol": symbol,
        }
        params = {k: v for k, v in params.items() if v is not None}

        response = self.make_request(
            url=url,
            headers=headers,
            params=params
        )

        return response
