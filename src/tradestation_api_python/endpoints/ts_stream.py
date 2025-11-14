from ..base_client import BaseStreamClient
from typing import Optional, Dict


class MarketDataStream(BaseStreamClient):
    """
    Handles real-time bar streaming from TradeStation Market Data API.

    Inherits connection management, token refresh, and auto-reconnect
    logic from `BaseStreamClient`. This class only defines the specific
    endpoint and parameters for bar data.

    Attributes
    ----------
    token_manager : TokenManager
        Manages OAuth tokens for authentication.
    """

    def __init__(self, *, token_manager):
        super().__init__(token_manager=token_manager)

    def stream_bars(
        self,
        *,
        symbol: str,
        interval: int = 1,
        unit: str = "Daily",
        barsback: Optional[int] = None,
        sessiontemplate: Optional[str] = None,
        on_message=None,
    ) -> None:
        """
        Stream real-time bar data for a given symbol and timeframe.

        Parameters
        ----------
        symbol : str
            Market symbol (e.g., "AAPL", "MSFT").
        interval : int, default=1
            Bar interval in minutes (for intraday bars).
        unit : str, default="Daily"
            Time unit ("Minute", "Daily", "Weekly", "Monthly").
        barsback : int, optional
            Number of historical bars to include at stream start.
        sessiontemplate : str, optional
            Session template (e.g., "USEQPreAndPost", "Default").
        on_message : callable, optional
            Callback function invoked with each parsed JSON message.
            Example: `lambda msg: print(msg["Close"])`

        Notes
        -----
        - This method blocks until `stop()` is called.
        - Use a background thread or asyncio adaptation for non-blocking.
        """
        url = (
            f"{self.token_manager.base_api_url}/marketdata/stream/"
            f"barcharts/{symbol}"
        )
        params: Dict[str, str | int] = {
            "interval": interval,
            "unit": unit,
            "barsback": barsback,
            "sessiontemplate": sessiontemplate,
        }
        params = {k: v for k, v in params.items() if v is not None}

        headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Accept": "application/vnd.tradestation.streams.v2+json",
        }

        self.logger.info(
            f"Starting bar stream for {symbol} ({unit} {interval})"
        )
        self.logger.debug(f"Stream params: {params}")

        self.stream_loop(
            url=url,
            params=params,
            headers=headers,
            on_message=on_message or self._default_message_handler,
        )

    def _default_message_handler(self, msg: dict):
        """Default message handler used when no callback is passed."""
        ts = msg.get("TimeStamp")
        o, h, l, c = (
            msg.get("Open"), msg.get("High"),
            msg.get("Low"), msg.get("Close")
        )
        if ts and o and h and l and c:
            self.logger.info(f"{ts} | O:{o} H:{h} L:{l} C:{c}")
        else:
            self.logger.debug(f"Stream message: {msg}")

    def stream_quotes(
        self,
        *,
        symbols: list[str],
        on_message=None,
    ) -> None:
        """
        Stream real-time quote updates for one or more symbols.

        Parameters
        ----------
        symbols : list of str
            One or more market symbols (e.g., ["AAPL", "MSFT"]).
        on_message : callable, optional
            Callback invoked with each parsed JSON message.

        Notes
        -----
        - Supports up to 100 symbols per request.
        - The stream remains open until `stop()` is called.
        - Each message typically contains bid/ask, last price,
        volume, and trade status fields.
        """
        if not symbols:
            raise ValueError("At least one symbol must be provided.")

        if len(symbols) > 100:
            raise ValueError("Maximum 100 symbols allowed per request.")

        symbols_as_str = ",".join(sym.strip().upper() for sym in symbols)

        url = (
            f"{self.token_manager.base_api_url}/marketdata/stream/"
            f"quotes/{symbols_as_str}"
        )

        headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Accept": "application/vnd.tradestation.streams.v2+json",
        }

        self.logger.info(f"Starting quote stream for {symbols_as_str}")

        self.stream_loop(
            url=url,
            params={},
            headers=headers,
            on_message=on_message or self._default_message_handler,
        )

    def stream_market_depth_quotes(
        self,
        *,
        symbol: str,
        max_levels: Optional[int] = 20,
        on_message=None,
    ) -> None:
        """
        Stream real-time market depth (Level II) quote updates for a symbol.

        Parameters
        ----------
        symbol : str
            Single market symbol (e.g., "AAPL", "MSFT").
        max_levels : int, optional, default=20
            Maximum number of bid/ask levels to receive per side.
            TradeStation supports up to 20.
        on_message : callable, optional
            Callback invoked with each parsed JSON message.
            Example: `lambda msg: print(msg["Bid"][0])`

        Notes
        -----
        - This endpoint streams full market depth updates (Level II data).
        - Stream remains open until `stop()` is called.
        - Each message may contain price, size, and order count per level.
        - Requires proper market data subscription (Level II access).
        """

        if not symbol:
            raise ValueError("A valid symbol must be provided.")

        url = (
            f"{self.token_manager.base_api_url}/marketdata/stream/"
            f"marketdepth/quotes/{symbol}"
        )

        headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Accept": "application/vnd.tradestation.streams.v2+json",
        }

        params: Dict[str, str | int] = {
            "maxlevels": max_levels,
        }
        params = {k: v for k, v in params.items() if v is not None}

        self.logger.info(
            f"Starting market depth stream for {symbol} "
            f"(max_levels={max_levels})"
        )

        self.stream_loop(
            url=url,
            params=params,
            headers=headers,
            on_message=on_message or self._default_message_handler,
        )

    def stream_market_depth_aggregates(
        self,
        *,
        symbol: str,
        max_levels: Optional[int] = 20,
        on_message=None,
    ) -> None:
        """
        Stream aggregate market depth data (Level II aggregates) for a symbol.

        This stream provides aggregated bid/ask quotes for equities, futures,
        and stock options. Each message represents a consolidated price level
        and side, with data aggregated from multiple participants.

        Parameters
        ----------
        symbol : str
            Single market symbol (e.g., "AAPL", "ESZ4").
        max_levels : int, optional, default=20
            Maximum number of aggregated bid/ask levels to return.
        on_message : callable, optional
            Callback invoked with each parsed JSON message.
            Example: `lambda msg: print(msg["Bid"][0])`

        Notes
        -----
        - Requires market depth (Level II) data entitlement.
        - Aggregates are recalculated in real time as orders change.
        - Stream remains open until `stop()` is called.
        """

        if not symbol:
            raise ValueError("A valid symbol must be provided.")

        url = (
            f"{self.token_manager.base_api_url}/marketdata/stream/"
            f"marketdepth/aggregates/{symbol}"
        )

        headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Accept": "application/vnd.tradestation.streams.v2+json",
        }

        params: Dict[str, str | int] = {"maxlevels": max_levels}
        params = {k: v for k, v in params.items() if v is not None}

        self.logger.info(
            f"Starting market depth aggregates stream for {symbol} "
            f"(max_levels={max_levels})"
        )

        self.stream_loop(
            url=url,
            params=params,
            headers=headers,
            on_message=on_message or self._default_message_handler,
        )


class BrokerStream(BaseStreamClient):
    """
    Streams real-time order updates from the TradeStation Brokerage API.

    This stream delivers order status events (e.g. placed, filled, canceled)
    for one or more brokerage accounts.
    """

    def __init__(self, *, token_manager):
        super().__init__(token_manager=token_manager)

    def stream_orders(
        self,
        *,
        accounts: list[str],
        on_message=None,
    ) -> None:
        """
        Stream real-time order updates for the given accounts.

        Parameters
        ----------
        accounts : list of str
            Account IDs (max 100) for which to stream order events.
        on_message : callable, optional
            Callback executed for each parsed event message.
        """
        if not accounts:
            raise ValueError("At least one account must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")

        accounts_as_str = ",".join(acc.strip().upper() for acc in accounts)

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/orders"
        )

        headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Accept": "application/vnd.tradestation.streams.v2+json",
        }

        self.logger.info(
            f"Starting orders stream for accounts: {accounts_as_str}"
        )

        self.stream_loop(
            url=url,
            params={},
            headers=headers,
            on_message=on_message or self._default_message_handler,
        )

    def _default_message_handler(
        self,
        msg: dict
    ) -> None:
        """Logs incoming order stream events in a readable format."""
        oid = msg.get("OrderID")
        status = msg.get("Status")
        symbol = msg.get("Symbol")
        qty = msg.get("Quantity")
        side = msg.get("BuyOrSell")

        if not any([oid, status, symbol]):
            return

        self.logger.info(
            f"Order {oid or '-'} | {symbol or '?'} {side or '?'} "
            f"{qty or '?'} | Status: {status or '?'}"
        )

    def stream_orders_by_id(
        self,
        *,
        accounts: list[str],
        order_ids: list[str],
        on_message=None,
    ) -> None:
        """
        Stream real-time updates for specific orders in the given accounts.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs (max 100) for which to stream order events.
        order_ids : list of str
            One or more specific order IDs (max 100) to stream updates for.
        on_message : callable, optional
            Callback executed for each parsed event message.

        Raises
        ------
        ValueError
            If no accounts or order IDs are provided, or if limits are
            exceeded.
        """

        if not accounts:
            raise ValueError("At least one account must be provided.")
        if not order_ids:
            raise ValueError("At least one order ID must be provided.")

        if len(accounts) > 100:
            raise ValueError("Maximum 100 accounts allowed per request.")
        if len(order_ids) > 100:
            raise ValueError("Maximum 100 order IDs allowed per request.")

        accounts_as_str = ",".join(acc.strip().upper() for acc in accounts)
        ids_as_str = ",".join(oid.strip().upper() for oid in order_ids)

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/orders/{ids_as_str}"
        )

        headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Accept": "application/vnd.tradestation.streams.v2+json",
        }

        self.logger.info(
            f"Starting order-by-ID stream for accounts={accounts_as_str}, "
            f"orders={ids_as_str}"
        )

        self.stream_loop(
            url=url,
            params={},
            headers=headers,
            on_message=on_message or self._default_message_handler,
        )

    def stream_positions(
        self,
        *,
        accounts: list[str],
        changes: Optional[bool] = False,
        on_message=None,
    ) -> None:
        """
        Stream real-time position updates for the given accounts.

        Parameters
        ----------
        accounts : list of str
            One or more account IDs (max 25) for which to stream positions.
        changes : bool, optional, default=False
            If True, only streams position changes instead of all open
            positions.
        on_message : callable, optional
            Callback executed for each parsed event message.

        Raises
        ------
        ValueError
            If no accounts are provided or if more than 25 are specified.

        Notes
        -----
        - Valid for Cash, Margin, Futures, and DVP account types.
        - The stream remains open until `stop()` is called.
        """

        if not accounts:
            raise ValueError("At least one account must be provided.")
        if len(accounts) > 25:
            raise ValueError("Maximum 25 accounts allowed per request.")

        accounts_as_str = ",".join(acc.strip().upper() for acc in accounts)

        url = (
            f"{self.token_manager.base_api_url}/brokerage/accounts/"
            f"{accounts_as_str}/positions"
        )

        headers = {
            "Authorization": f"Bearer {self.token_manager.get_token()}",
            "Accept": "application/vnd.tradestation.streams.v2+json",
        }

        self.logger.info(
            f"Starting positions stream for accounts={accounts_as_str} "
            f"(changes={changes})"
        )

        params: Dict[str, str | int] = {
            "changes": str(changes).lower(),
        }

        self.stream_loop(
            url=url,
            params=params,
            headers=headers,
            on_message=on_message or self._default_message_handler,
        )

