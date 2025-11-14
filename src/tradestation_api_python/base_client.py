from typing import Dict
import requests
import logging
import json
import time


class BaseAPIClient:
    """
    Base HTTP client for TradeStation API endpoints.

    Handles authenticated GET requests and token refresh
    on 401 Unauthorized responses. Intended for inheritance
    by specific API clients (e.g., MarketDataAPI, OrdersAPI, etc.).
    """

    def __init__(
        self,
        token_manager
    ):
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
            token = self.token_manager.get_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = _get(params)

        resp.raise_for_status()
        
        return resp.json()


class BaseStreamClient:
    """
    Base class for handling real-time streaming connections with
    the TradeStation API.

    TradeStation exposes several streaming endpoints (e.g., market
    data bars, quotes, and order updates) using long-lived HTTP
    connections with the `stream=True` flag. Each event is sent as a
    JSON object terminated by a newline. This allows clients to
    process updates in real time without repeated polling.

    This base class encapsulates all the shared logic required to
    manage such a stream:
      • establishing the initial streaming connection,
      • decoding JSON line-by-line as messages arrive,
      • automatically refreshing expired OAuth tokens,
      • reconnecting in case of network interruptions or HTTP 401,
      • and dispatching messages to a user-defined callback.

    Subclasses (e.g., `MarketDataStream`, `OrderStream`, etc.)
    should implement only the endpoint-specific parts—typically
    constructing the request URL and defining the message handler.

    Attributes
    ----------
    token_manager : TokenManager
        Object responsible for providing and refreshing OAuth tokens.
    _running : bool
        Internal control flag used to gracefully stop the stream loop.

    Notes
    -----
    - The implementation is synchronous but designed to be easily
      adapted to asyncio with minimal structural changes.
    - When `stop()` is called, the main loop will terminate cleanly
      after the current iteration.
    - Errors are logged using a dedicated logger (`tradestation.stream`).
    """

    def __init__(
        self,
        token_manager
    ):
        self.token_manager = token_manager
        self._running = False

        self.logger = logging.getLogger("tradestation.stream")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            fmt = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(fmt)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def _connect(
        self,
        url,
        params,
        headers
    ):
        """Establishes the HTTP stream connection."""
        return requests.get(
            url,
            params=params,
            headers=headers,
            stream=True,
            timeout=30
        )

    def _read_stream(
        self,
        response,
        on_message
    ):
        """Iterates over JSON messages and dispatches to callback."""
        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
                on_message(data)
            except Exception as e:
                self.logger.error(f"Malformed stream message: {e}")

    def _refresh_and_reconnect(
        self,
        url,
        params,
        headers,
        on_message
    ):
        """Refreshes token and reopens stream on 401 or disconnection."""
        self.logger.warning(
            "Stream disconnected — refreshing token and reconnecting."
        )
        new_token = self.token_manager.get_token()
        headers["Authorization"] = f"Bearer {new_token}"
        self._run_stream(url, params, headers, on_message)

    def _run_stream(
        self,
        url,
        params,
        headers,
        on_message
    ):
        """Handles one connection attempt and auto-reconnect logic."""
        try:
            with self._connect(url, params, headers) as resp:
                if resp.status_code == 401:
                    self.logger.warning(
                        "Unauthorized (401) — token likely invalid."
                    )
                    return self._refresh_and_reconnect(
                        url,
                        params,
                        headers,
                        on_message
                    )

                elif not resp.ok:
                    self.logger.error(
                        f"Stream error {resp.status_code}: {resp.text}"
                    )
                    self.stop()
                    return

                ctype = resp.headers.get("Content-Type")
                self.logger.info(
                    f"Connected stream with content-type: {ctype}"
                )

                has_data = False
                for line in resp.iter_lines():
                    if not self._running:
                        self.logger.info("Stream stopped by user.")
                        break
                    if not line:
                        continue
                    has_data = True
                    try:
                        data = json.loads(line)
                        on_message(data)
                    except json.JSONDecodeError:
                        self.logger.warning("Invalid JSON chunk.")
                        continue

                if not has_data:
                    self.logger.info(
                        "No stream data received — waiting before reconnect."
                    )
                    time.sleep(10)

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Connection error: {e}")
            time.sleep(3)
            self._refresh_and_reconnect(url, params, headers, on_message)

    def stream_loop(
        self,
        url,
        params,
        headers,
        on_message
    ):
        """
        Public entry point for all streams.
        Keeps running until self.stop() is called.
        """
        self._running = True

        if "Authorization" not in headers:
            token = self.token_manager.get_token()
            headers["Authorization"] = f"Bearer {token}"

        self.logger.info(f"Starting stream: {url}")

        while self._running:
            # Main streaming loop:
            # - Keeps the connection alive until self.stop() is called.
            # - Automatically restarts the stream if the server closes it.
            # - If no data is received (e.g. market closed), a small delay
            #   (≈10s) inside _run_stream() prevents aggressive reconnects.
            # - If data flows normally, the loop continues uninterrupted.
            self._run_stream(
                url,
                params,
                headers,
                on_message
            )
            if self._running:
                time.sleep(1)

    def stop(self):
        """Stops the active stream loop."""
        self._running = False
