from concurrent.futures import ThreadPoolExecutor, as_completed
from ..base_client import BaseAPIClient
from typing import Optional, Dict, Any
from rich.progress import Progress
from datetime import date
import numpy as np
import requests


class MarketDataAPI(BaseAPIClient):
    """
    Provides access to TradeStation Market Data endpoints.

    Handles historical and intraday bar retrieval, automatic
    chunking for large data ranges, and automatic token refresh
    through the injected `TokenManager`.

    Attributes
    ----------
    ts_max_bars_thresh : int
        Maximum number of bars per request supported by TradeStation.
    token_manager : TokenManager
        Object responsible for providing and refreshing OAuth tokens.
    """

    ts_max_bars_thresh = 57_600

    def __init__(
        self,
        *,
        token_manager
    ) -> None:
        self.token_manager = token_manager

    def get_bars_between(
        self,
        *,
        symbol: str,
        first_date: str,
        interval: int = 1,
        unit: str = "Daily",
        last_date: Optional[str] = None,
        sessiontemplate: Optional[str] = None,
        max_workers: int = 15,
    ) -> Dict[str, Any]:
        """
        Retrieve market data bars between two dates, automatically
        splitting large requests into smaller chunks for parallel execution.

        Parameters
        ----------
        symbol : str
            The market symbol (e.g., "MSFT").
        first_date : str
            Start timestamp (ISO 8601 format).
        interval : int, default=1
            Bar interval (minutes for intraday data).
        unit : str, default="Daily"
            Bar time unit: "Minute", "Daily", "Weekly", "Monthly".
        last_date : str, optional
            End timestamp (ISO 8601). Defaults to today's date.
        sessiontemplate : str, optional
            U.S. session template, ignored for non-US symbols.
        max_workers : int, default=15
            Number of threads used for concurrent chunk retrieval.

        Returns
        -------
        dict
            Combined JSON response containing all retrieved bars,
            sorted in chronological order.
        """
        
        def organize_params(start: str, end: str) -> Dict[str, Any]:
            """
            Prepare the query parameters for a bar request.
            Filters out None values to avoid invalid API params.
            """
            params = {
                "interval": interval,
                "unit": unit,
                "firstdate": start,
                "lastdate": end,
                "sessiontemplate": sessiontemplate,
            }
            return {k: v for k, v in params.items() if v is not None}

        if not last_date:
            # If last_date is None, default to today's date.
            last_date = date.today().strftime("%Y-%m-%d")

        if first_date > last_date:
            raise Exception("first_data can't be greater then last_date")

        url = f"{self.token_manager.base_api_url}/marketdata/barcharts/{symbol}"
        
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        # We first create an array containing the range of dates of interest.
        dates = np.arange(
            first_date,
            np.datetime64(last_date) + np.timedelta64(1, "D"),
            dtype="datetime64[D]",
        )

        # Validate the unit parameter.
        if unit not in {"Minute", "Daily", "Weekly", "Monthly"}:
            raise ValueError("Please set `unit` with a proper resolution.")

        # We estimate the number of bars to retrieve.
        multiplier = (
            1440 if unit == "Minute"
            else 365 if unit == "Daily"
            else 52 if unit == "Weekly"
            else 12
        )
        bars_est = len(dates) * multiplier / interval

        # If the estimated number of bars doesn't exceed the TradeStation
        # threshold, we make a single request.
        if bars_est <= self.ts_max_bars_thresh:
            params = organize_params(first_date, last_date)
            return self.make_request(url=url, headers=headers, params=params)

        # Determine the maximum number of days per chunk.
        # Example: with 1-minute data and a limit of 57,600 bars,
        # we can handle roughly 40 days per request.
        max_days = int(self.ts_max_bars_thresh * interval / multiplier)
        chunks = []

        for i in range(0, len(dates), max_days):
            # We loop with step = max_days and store start/end dates
            # for each chunk of the request.
            start = str(dates[i])
            end = str(dates[min(i + max_days - 1, len(dates) - 1)])
            chunks.append((start, end))

        merged = {}
        total_chunks = len(chunks)
        completed = 0

        with Progress() as progress:
            # Fancy progress bar
            task = progress.add_task(
                f"[cyan]Fetching {symbol}...", total=total_chunks
            )

            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {
                    ex.submit(
                        self.make_request,
                        url,
                        headers,
                        organize_params(start, end),
                    ): (start, end)
                    for start, end in chunks
                }

                for fut in as_completed(futs):
                    start, end = futs[fut]
                    try:
                        res = fut.result()
                        # Update progress per completed chunk.
                        progress.advance(task, 1)

                        if not merged:
                            # First successful chunk
                            merged = res
                        else:
                            for k, v in res.items():
                                if k == "Bars":
                                    merged.setdefault("Bars", []).extend(v)
                                else:
                                    merged[k] = v

                    except Exception as e:
                        # Skip failed chunks but continue processing others
                        progress.advance(task, 1)
                    completed += 1

        # Ensure chronological order
        if "Bars" in merged:
            merged["Bars"].sort(key=lambda b: b.get("Time", ""))

        return merged

    def get_bars(
        self,
        *,
        symbol: str,
        interval: int = 1,
        unit: str = "Daily",
        barsback: Optional[int] = None,
        last_date: Optional[str] = None,
        sessiontemplate: Optional[str] = None,
    ) -> Dict:
        """
        Retrieve a fixed number of historical bars for a given symbol.

        This method wraps the TradeStation `/barcharts` endpoint for
        fetching recent or compact historical data using the `barsback`
        parameter. It supports both intraday and higher timeframes
        (daily, weekly, monthly).

        Parameters
        ----------
        symbol : str
            The market symbol (e.g., "AAPL" or "MSFT").
        interval : int, default=1
            Interval size for each bar (minutes for intraday data).
        unit : str, default="Daily"
            Time unit of the bars: "Minute", "Daily", "Weekly", "Monthly".
        barsback : int, optional
            Number of bars to retrieve. Must not exceed 57,600.
        last_date : str, optional
            End timestamp (ISO 8601 format). Defaults to the latest bar.
        sessiontemplate : str, optional
            U.S. session template (USEQPre, USEQPost, etc.).
            Ignored for non-U.S. instruments.

        Returns
        -------
        dict
            JSON response containing OHLCV bar data and metadata.

        Raises
        ------
        ValueError
            If `barsback` exceeds TradeStation API limits.
        requests.exceptions.RequestException
            If the HTTP request fails or the server returns an error.

        Notes
        -----
        - Designed for small, recent lookback windows (e.g., last N bars).
        - Use `get_bars_between()` for large or date-range queries.
        """
        if barsback and barsback > 57_600:
            raise ValueError(
                "Requests limited to 57,600 bars per call"
            )

        url = f"{self.token_manager.base_api_url}/marketdata/barcharts/{symbol}"
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "interval": interval,
            "unit": unit,
            "barsback": barsback,
            "lastdate": last_date,
            "sessiontemplate": sessiontemplate,
        }
        params = {k: v for k, v in params.items() if v is not None}

        with Progress() as progress:
            task = progress.add_task(
                f"[cyan]Fetching {symbol}...", total=1
            )

            response = self.make_request(
                url=url,
                headers=headers,
                params=params
            )

            progress.advance(task, 1)

            return response

    def get_symbol_details(
        self,
        *,
        symbols: list[str]
    ) -> Dict:
        """
        Retrieve detailed metadata for one or more market symbols.

        Parameters
        ----------
        symbols : list[str]
            A list of market symbols (e.g., ["AAPL", "MSFT"]).

        Returns
        -------
        dict
            JSON response with symbol metadata.

        Raises
        ------
        ValueError
            If no symbols are provided or the list exceeds API limits.
        requests.exceptions.RequestException
            If the HTTP request fails or the server returns an error.
        """
        if not symbols:
            raise ValueError("At least one symbol must be provided.")

        if len(symbols) > 100:
            raise ValueError("Maximum 100 symbols allowed per request.")

        symbols_as_str = ",".join(
            [requests.utils.quote(sym.strip()) for sym in symbols]
        )

        url = (
            f"{self.token_manager.base_api_url}/marketdata/symbols/"
            f"{symbols_as_str}"
        )
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        return self.make_request(url=url, headers=headers, params={})
    
    def get_crypto_symbol_names(self) -> Dict:
        """
        Fetch crypto symbol names for all available cryptocurrency pairs
        (e.g., BTCUSD, ETHUSD, LTCUSD, BCHUSD).

        Notes
        -----
        - These symbols provide market data only; they cannot be traded.
        - Endpoint: /v3/marketdata/symbollists/cryptopairs/symbols
        """
        url = (
            f"{self.token_manager.base_api_url}/marketdata/symbollists/"
            "cryptopairs/symbolnames"
        )
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        return self.make_request(url=url, headers=headers, params={})

    def get_quote_snapshots(
        self,
        *,
        symbols: list[str]
    ) -> Dict:
        """
        Fetches a full snapshot of the latest quotes for the given symbols.

        This method returns the most recent quote (Level 1) information
        for each symbol specified. For real-time continuous updates,
        use the streaming quote endpoint.

        Parameters
        ----------
        symbols : list of str
            One or more market symbols (e.g., ["AAPL", "MSFT"]).

        Returns
        -------
        dict
            JSON response mapping each symbol to its latest quote data.

        Raises
        ------
        ValueError
            If no symbols are provided or more than 100 symbols are specified.
        """

        if not symbols:
            raise ValueError("At least one symbol must be provided.")

        if len(symbols) > 100:
            raise ValueError("Maximum 100 symbols allowed per request.")

        symbols_as_str = ",".join(
            [requests.utils.quote(sym.strip()) for sym in symbols]
        )

        url = (
            f"{self.token_manager.base_api_url}/marketdata/quotes/"
            f"{symbols_as_str}"
        )
        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        return self.make_request(url=url, headers=headers, params={})

