from typing import Dict
import requests


class BaseAPIClient:
    """
    Base HTTP client for TradeStation API endpoints.

    Handles authenticated GET requests and token refresh
    on 401 Unauthorized responses. Intended for inheritance
    by specific API clients (e.g., MarketDataAPI, OrdersAPI, etc.).
    """

    def __init__(self, token_manager):
        self.token_manager = token_manager

    def make_request(
        self,
        url: str,
        headers: dict,
        params: dict
    ) -> Dict:
        """
        Execute an authenticated GET request with automatic token refresh.

        Parameters
        ----------
        url : str
            Full endpoint URL.
        headers : dict
            HTTP headers (must include Authorization).
        params : dict
            Query parameters for the request.

        Returns
        -------
        dict
            Parsed JSON response.
        """
        def _get(params):
            return requests.get(url, headers=headers, params=params)

        resp = _get(params)
        if resp.status_code == 401:
            token = self.token_manager.refresh_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = _get(params)

        resp.raise_for_status()
        
        return resp.json()
