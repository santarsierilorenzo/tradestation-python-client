from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict
from datetime import date
import numpy as np
import requests

def get_bars(
    token: str,
    *,
    symbol: str,
    interval: int = 1,
    unit: str = "Daily",
    barsback: Optional[int] = None,
    first_date: Optional[str] = None,
    last_date: Optional[str] = None,
    sessiontemplate: Optional[str] = None,
) -> Dict:
    """
    Retrieve historical market data bars for a given symbol and timeframe.

    This method calls the TradeStation "Get Bars" endpoint to obtain
    aggregated OHLCV data for the specified instrument. Bars can be
    retrieved either by requesting a number of bars back from the
    latest bar (`barsback`) or by specifying a date range
    (`firstdate` / `lastdate`).

    Args:
        symbol (str):
            The instrument symbol to query (e.g. "MSFT").
        interval (int, optional):
            Interval size for each bar. For intraday data, this
            represents minutes per bar. Defaults to 1.
        unit (str, optional):
            Time unit for the bars. Valid values: "Minute", "Daily",
            "Weekly", "Monthly". Defaults to "Daily".
        barsback (int, optional):
            Number of bars to retrieve. Mutually exclusive with
            `firstdate`. Maximum of 57,600 for intraday data.
        firstdate (str, optional):
            Start timestamp (ISO 8601 format). Mutually exclusive with
            `barsback`.
        lastdate (str, optional):
            End timestamp (ISO 8601 format). Defaults to current time.
        sessiontemplate (str, optional):
            U.S. equity session template. Ignored for non-U.S. symbols.
            Valid values: "USEQPre", "USEQPost", "USEQPreAndPost",
            "USEQ24Hour", "Default".
        startdate (str, optional):
            Deprecated. Use `lastdate` instead.

    Returns:
        dict:
            Parsed JSON response containing a list of bar objects,
            each including:
              - `time`: Bar timestamp (ISO 8601)
              - `open`: Opening price
              - `high`: Highest price
              - `low`: Lowest price
              - `close`: Closing price
              - `volume`: Traded volume

    Notes:
        - Intraday requests are limited to 57,600 bars per call.
        - `barsback` and `firstdate` cannot be used together.
        - Session templates apply only to U.S. equities.
    """
    
    if barsback is not None and first_date is not None:
        raise ValueError("barsback and firstdate are mutually exclusive")
    
    if barsback != None:
        if barsback > 57_600:
            raise ValueError(
                "Intraday requests are limited to 57,600 bars per call"
            )
    
    url = f"https://api.tradestation.com/v3/marketdata/barcharts/{symbol}"
    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "interval": interval,
        "unit": unit,
        "barsback": barsback,
        "firstdate": first_date,
        "lastdate": last_date,
        "sessiontemplate": sessiontemplate,
    }

    params = {k: v for k, v in params.items() if v is not None}

    response = requests.get(
        url,
        headers=headers,
        params=params
    )
    response.raise_for_status()

    return response.json()


def get_bars_between(
    token: str,
    *,
    symbol: str,
    first_date: str,
    interval: int = 1,
    unit: str = "Daily",
    last_date: Optional[str] = None,
    sessiontemplate: Optional[str] = None,
    max_workers: int = 15
):
    """
    Retrieve market data bars between two dates, with automatic chunking
    and parallel requests for large intraday datasets.

    This function calls the TradeStation "Get Bars" endpoint and returns
    aggregated OHLCV data for the specified instrument. If the estimated
    number of intraday bars between `first_date` and `last_date` exceeds
    57,600 (the API limit per request), the date range is automatically
    split into smaller chunks and fetched concurrently using a thread pool.

    Args:
        token (str):
            Valid OAuth2 Bearer token for authentication.
        symbol (str):
            Instrument symbol to query (e.g. "MSFT").
        first_date (str):
            Start timestamp in ISO 8601 format (e.g. "2024-01-01").
        interval (int, optional):
            Interval size for each bar. For intraday data, this represents
            minutes per bar. Defaults to 1.
        unit (str, optional):
            Time unit for the bars. Valid values: "Minute", "Daily",
            "Weekly", "Monthly". Defaults to "Daily".
        last_date (str, optional):
            End timestamp in ISO 8601 format. Defaults to the current date
            if not provided.
        sessiontemplate (str, optional):
            U.S. equity session template. Ignored for non-U.S. symbols.
            Valid values: "USEQPre", "USEQPost", "USEQPreAndPost",
            "USEQ24Hour", "Default".
        max_workers (int, optional):
            Maximum number of parallel threads used when fetching multiple
            time chunks. Defaults to 15.

    Returns:
        dict:
            Parsed JSON response containing merged API data, including:
              - `Bars`: List of bar objects with:
                    - `Time`: Bar timestamp (ISO 8601)
                    - `Open`: Opening price
                    - `High`: Highest price
                    - `Low`: Lowest price
                    - `Close`: Closing price
                    - `Volume`: Traded volume
              - Other metadata fields preserved from the API response.

    Raises:
        requests.exceptions.RequestException:
            If any HTTP request fails or the server returns an error.
        ValueError:
            If invalid or conflicting parameters are provided.

    Notes:
        - Intraday requests are limited to 57,600 bars per call.
        - Requests exceeding that limit are automatically split
          and executed concurrently.
        - All partial results are merged and chronologically ordered.
        - `barsback` and date-based parameters are mutually exclusive.
    """

    if last_date is None:
        last_date = date.today().strftime("%Y-%m-%d")

    url = f"https://api.tradestation.com/v3/marketdata/barcharts/{symbol}"
    headers = {"Authorization": f"Bearer {token}"}

    def make_request(first: str, last: str):
        """Perform a single REST call."""
        params = {
            "interval": interval,
            "unit": unit,
            "firstdate": first,
            "lastdate": last,
            "sessiontemplate": sessiontemplate,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    # Single call for non-intraday data
    if unit != "Minute":
        return make_request(first_date, last_date)

    # Build date range, include last_date
    dates = np.arange(
        first_date,
        np.datetime64(last_date) + np.timedelta64(1, "D"),
        dtype="datetime64[D]"
    )

    # Estimate total bars
    bars_estimate = len(dates) * 1440 / interval
    if bars_estimate <= 57_600:
        return make_request(first_date, last_date)

    # Compute max days per chunk
    max_days = int(57_600 * interval / 1440)
    chunks = []
    for i in range(0, len(dates), max_days):
        start = str(dates[i])
        end = str(dates[min(i + max_days - 1, len(dates) - 1)])
        chunks.append((start, end))

    merged = {}

    # Parallel execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(make_request, s, e): (s, e) for s, e in chunks
        }

        for future in as_completed(futures):
            response = future.result()
            if not merged:
                merged = response
                continue
            # Merge responses progressively
            for k, v in response.items():
                if k == "Bars":
                    merged.setdefault("Bars", []).extend(v)
                else:
                    merged[k] = v

    # Ensure chronological order
    if "Bars" in merged:
        merged["Bars"].sort(key=lambda b: b.get("Time", ""))

    return merged



