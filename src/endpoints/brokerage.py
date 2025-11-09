from src.base_client import BaseAPIClient
from typing import Dict
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
        url = "https://api.tradestation.com/v3/brokerage/accounts"
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
            "https://api.tradestation.com/v3/brokerage/accounts/"
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
            "https://api.tradestation.com/v3/brokerage/accounts/"
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
