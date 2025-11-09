from typing import Optional, Dict
from src.base_client import BaseStreamClient
import logging


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
            "https://api.tradestation.com/v3/marketdata/stream/"
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
