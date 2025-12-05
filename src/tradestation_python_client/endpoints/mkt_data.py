from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Tuple
from ..base_client import BaseAPIClient
from dateutil.parser import isoparse
from rich.progress import Progress
from datetime import date
import numpy as np
import requests
import time


class MarketDataAPI(BaseAPIClient):
    """
    Provides a robust interface to TradeStation Market Data endpoints.
    Includes safe chunking for large historical queries, retry logic for
    unstable API responses, date normalization, and automatic token
    refresh when required.

    Notes
    -----
    - TradeStation enforces a maximum of 57,600 bars per request.
    - Some valid API responses may contain no bars without raising
      errors (e.g., holidays, illiquid symbols, malformed ranges).
    - This client aggressively normalizes dates and retries empty or
      transient responses.
    """

    ts_max_bars_thresh = 57_600

    def __init__(self, *, token_manager) -> None:
        self.token_manager = token_manager

    def _normalize_date(self, ds: str) -> str:
        """
        Normalize an input date to YYYY-MM-DD (day precision).

        Parameters
        ----------
        ds : str
            Date input (various string formats supported).

        Returns
        -------
        str
            Normalized date in YYYY-MM-DD format.

        Raises
        ------
        ValueError
            If the input format cannot be parsed.
        """
        try:
            return str(np.datetime64(ds, "D"))
        except Exception:
            raise ValueError(f"Invalid date format: {ds}")

    def _chunk_dates(
        self, dates: np.ndarray, max_days: int
    ) -> List[Tuple[str, str]]:
        """
        Split a continuous date array into (start, end) chunks.

        Parameters
        ----------
        dates : np.ndarray
            Array of daily timestamps.
        max_days : int
            Maximum number of days allowed in a single request.

        Returns
        -------
        list of tuple(str, str)
            List of (start_date, end_date) pairs.
        """
        chunks: List[Tuple[str, str]] = []
        n = len(dates)

        for i in range(0, n, max_days):
            start = str(dates[i])
            end = str(dates[min(i + max_days - 1, n - 1)])
            chunks.append((start, end))

        return chunks

    def _request_with_retry(
        self,
        *,
        url: str,
        headers: Dict[str, str],
        params: Dict[str, Any],
        retries: int = 3,
        backoff: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Execute a request with retry logic and automatic token refresh.
        This handles empty responses, 5xx errors, and expired tokens.

        Parameters
        ----------
        url : str
            Target API endpoint.
        headers : dict
            HTTP headers including authorization.
        params : dict
            Query parameters.
        retries : int
            Maximum retry attempts.
        backoff : float
            Backoff multiplier for retry sleeping.

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        requests.exceptions.RequestException
            On persistent HTTP or network failures.
        RuntimeError
            If retry logic ends in an unexpected state.
        """
        for attempt in range(retries):
            try:
                res = self.make_request(
                    url=url,
                    headers=headers,
                    params=params
                )

                # TradeStation may return empty responses with 200 OK.
                if not res or ("Bars" in res and not res["Bars"]):
                    if attempt < retries - 1:
                        time.sleep(backoff * (attempt + 1))
                        continue

                return res

            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code

                # Expired token
                if status == 401 and attempt < retries - 1:
                    new_token = self.token_manager.refresh_token()
                    headers["Authorization"] = f"Bearer {new_token}"
                    continue

                # Retry on server errors
                if status >= 500 and attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
                    continue

                raise

            except Exception:
                if attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
                    continue
                raise

        raise RuntimeError("Retry mechanism reached an invalid state.")

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
        Retrieve bars between two dates, safely splitting the date
        range into multiple API calls when required.

        The function automatically:
        - normalizes input dates,
        - estimates bar count to decide if chunking is required,
        - splits requests into valid time windows,
        - retries intermittent failures,
        - refreshes expired tokens,
        - merges and chronologically sorts the results.

        Parameters
        ----------
        symbol : str
            Market symbol.
        first_date : str
            Start date (various formats accepted).
        interval : int
            Bar interval (minutes for intraday).
        unit : str
            Bar unit ("Minute", "Daily", "Weekly", "Monthly").
        last_date : str, optional
            End date. Defaults to today's date.
        sessiontemplate : str, optional
            Optional TS session template for filtering.
        max_workers : int
            Number of threads used for chunked retrieval.

        Returns
        -------
        dict
            Merged and chronologically sorted API response.

        Notes
        -----
        - Bars may be missing if the underlying market had no trading
          session on specific dates.
        - TradeStation may return empty bar sets without raising
          errors; these are logged as warnings during chunk retrieval.
        """
        if unit not in {"Minute", "Daily", "Weekly", "Monthly"}:
            raise ValueError("Invalid unit provided.")

        if last_date is None:
            last_date = date.today().strftime("%Y-%m-%d")

        f_date = self._normalize_date(first_date)
        l_date = self._normalize_date(last_date)

        if f_date > l_date:
            raise Exception("first_data can't be greater then last_date")

        url = (
            f"{self.token_manager.base_api_url}/marketdata/"
            f"barcharts/{symbol}"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        dates = np.arange(
            np.datetime64(f_date),
            np.datetime64(l_date) + np.timedelta64(1, "D"),
            dtype="datetime64[D]",
        )

        multiplier = (
            1440 if unit == "Minute"
            else 365 if unit == "Daily"
            else 52 if unit == "Weekly"
            else 12
        )

        bars_est = len(dates) * multiplier / interval

        # If below TS threshold, perform a single call.
        if bars_est <= self.ts_max_bars_thresh:
            params = {
                "interval": interval,
                "unit": unit,
                "firstdate": f_date,
                "lastdate": l_date,
                "sessiontemplate": sessiontemplate,
            }
            params = {k: v for k, v in params.items() if v is not None}

            return self._request_with_retry(
                url=url,
                headers=headers,
                params=params,
            )

        # Otherwise chunk the request.
        max_days = int(self.ts_max_bars_thresh * interval / multiplier)
        chunks = self._chunk_dates(dates, max_days)

        merged: Dict[str, Any] = {"Bars": []}

        with Progress() as progress:
            task = progress.add_task(
                f"[cyan]Fetching {symbol}...", total=len(chunks)
            )

            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = {
                    ex.submit(
                        self._request_with_retry,
                        url=url,
                        headers=headers.copy(),
                        params={
                            "interval": interval,
                            "unit": unit,
                            "firstdate": start,
                            "lastdate": end,
                            "sessiontemplate": sessiontemplate,
                        },
                    ): (start, end)
                    for start, end in chunks
                }

                for fut in as_completed(futures):
                    start, end = futures[fut]
                    progress.advance(task, 1)

                    try:
                        res = fut.result()
                    except Exception:
                        continue

                    if not res or not res.get("Bars"):
                        print(
                            f"[WARN] Empty bars for chunk {start} → {end}"
                        )
                        continue

                    merged["Bars"].extend(res["Bars"])

        merged["Bars"].sort(
            key=lambda b: isoparse(b["Time"])
        )

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
    ) -> Dict[str, Any]:
        """
        Retrieve a fixed number of bars using the `barsback` parameter.

        Parameters
        ----------
        symbol : str
            Market symbol.
        interval : int
            Bar interval.
        unit : str
            Bar unit.
        barsback : int, optional
            Number of bars to retrieve (max 57,600).
        last_date : str, optional
            Optional end date.
        sessiontemplate : str, optional
            Optional session template.

        Returns
        -------
        dict
            API response.

        Notes
        -----
        Designed for simple, recent lookback queries. For larger
        historical ranges prefer `get_bars_between()`.
        """
        if barsback and barsback > 57_600:
            raise ValueError("Requests limited to 57,600 bars per call")

        url = (
            f"{self.token_manager.base_api_url}/marketdata/barcharts/"
            f"{symbol}"
        )

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
            res = self._request_with_retry(
                url=url,
                headers=headers,
                params=params,
            )
            progress.advance(task, 1)
            return res

    def get_symbol_details(
        self,
        *,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Retrieve descriptive metadata for one or more symbols.

        Parameters
        ----------
        symbols : list[str]
            List of market symbols.

        Returns
        -------
        dict
            API response containing symbol details.

        Raises
        ------
        ValueError
            If input list is empty or exceeds API limits.
        """
        if not symbols:
            raise ValueError("At least one symbol must be provided.")

        if len(symbols) > 100:
            raise ValueError("Maximum 100 symbols per request.")

        encoded = ",".join(
            requests.utils.quote(s.strip()) for s in symbols
        )

        url = (
            f"{self.token_manager.base_api_url}/marketdata/"
            f"symbols/{encoded}"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        return self._request_with_retry(
            url=url,
            headers=headers,
            params={},
        )

    def get_crypto_symbol_names(self) -> Dict[str, Any]:
        """
        Retrieve the list of available cryptocurrency symbol names.

        Returns
        -------
        dict
            API response containing available crypto pairs.

        Notes
        -----
        These symbols are informational only and cannot be traded
        via this endpoint.
        """
        url = (
            f"{self.token_manager.base_api_url}/marketdata/"
            "symbollists/cryptopairs/symbolnames"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        return self._request_with_retry(
            url=url,
            headers=headers,
            params={},
        )

    def get_quote_snapshots(
        self,
        *,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Fetch snapshot quotes for a list of symbols.

        Parameters
        ----------
        symbols : list[str]
            Symbols to retrieve quotes for.

        Returns
        -------
        dict
            Latest quote snapshot for each symbol.

        Raises
        ------
        ValueError
            For invalid symbol lists.
        """
        if not symbols:
            raise ValueError("At least one symbol must be provided.")

        if len(symbols) > 100:
            raise ValueError("Maximum 100 symbols per request.")

        encoded = ",".join(
            requests.utils.quote(s.strip()) for s in symbols
        )

        url = (
            f"{self.token_manager.base_api_url}/marketdata/"
            f"quotes/{encoded}"
        )

        token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        return self._request_with_retry(
            url=url,
            headers=headers,
            params={},
        )
