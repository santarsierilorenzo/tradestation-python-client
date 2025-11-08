from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, Generator
from datetime import date
import numpy as np
import requests
import logging
import json
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


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

    This function calls the TradeStation REST endpoint
    `/v3/marketdata/barcharts/{symbol}` to obtain aggregated OHLCV
    data for the specified instrument. Bars can be fetched either by
    a `barsback` count or by a date range (`firstdate` / `lastdate`).

    Parameters
    ----------
    token : str
        OAuth2 bearer token for the TradeStation API.
    symbol : str
        The instrument symbol (e.g., "MSFT").
    interval : int, default=1
        Interval size for each bar. For intraday data, this represents
        minutes per bar.
    unit : str, default="Daily"
        Time unit for bars. Valid values: "Minute", "Daily",
        "Weekly", "Monthly".
    barsback : int, optional
        Number of bars to retrieve. Mutually exclusive with `firstdate`.
        Max value: 57,600 for intraday data.
    first_date : str, optional
        Start timestamp in ISO 8601 format.
    last_date : str, optional
        End timestamp in ISO 8601 format. Defaults to current date.
    sessiontemplate : str, optional
        U.S. equity session template. Valid values:
        "USEQPre", "USEQPost", "USEQPreAndPost",
        "USEQ24Hour", "Default".

    Returns
    -------
    dict
        JSON response containing a list of bar objects with fields:
        `Time`, `Open`, `High`, `Low`, `Close`, and `Volume`.

    Raises
    ------
    ValueError
        If invalid or conflicting parameters are provided.
    requests.exceptions.RequestException
        On network or HTTP error.

    Notes
    -----
    - Intraday requests are limited to 57,600 bars per call.
    - `barsback` and `first_date` cannot be used together.
    - Session templates apply only to U.S. equity symbols.
    """
    if barsback and first_date:
        raise ValueError("barsback and firstdate are mutually exclusive")
    if barsback and barsback > 57_600:
        raise ValueError("Intraday requests limited to 57,600 bars per call")

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

    log.info(f"Requesting bars for {symbol} ({unit}, intv={interval})")
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        count = len(data.get("Bars", []))
        log.info(f"Received {count} bars for {symbol}")
        return data
    except requests.exceptions.RequestException as e:
        log.error(f"Error retrieving bars for {symbol}: {e}")
        raise


def get_bars_between(
    token: str,
    *,
    symbol: str,
    first_date: str,
    interval: int = 1,
    unit: str = "Daily",
    last_date: Optional[str] = None,
    sessiontemplate: Optional[str] = None,
    max_workers: int = 15,
) -> Dict:
    """
    Retrieve market data bars between two dates with automatic chunking
    and parallel requests.

    This function splits large intraday ranges into smaller date chunks
    to comply with the TradeStation API limit (57,600 bars per call).
    Each chunk is fetched concurrently using a thread pool, and all
    partial results are merged chronologically.

    Parameters
    ----------
    token : str
        OAuth2 bearer token for authentication.
    symbol : str
        The instrument symbol (e.g., "MSFT").
    first_date : str
        Start timestamp (ISO 8601 format).
    interval : int, default=1
        Number of minutes per bar for intraday data.
    unit : str, default="Daily"
        Bar time unit: "Minute", "Daily", "Weekly", "Monthly".
    last_date : str, optional
        End timestamp (ISO 8601). Defaults to today's date.
    sessiontemplate : str, optional
        U.S. equity session template. Ignored for non-U.S. symbols.
    max_workers : int, default=15
        Maximum number of threads for parallel requests.

    Returns
    -------
    dict
        Combined JSON response containing all bars, sorted by time.

    Raises
    ------
    ValueError
        If invalid or conflicting parameters are provided.
    requests.exceptions.RequestException
        If any HTTP request fails.

    Notes
    -----
    - Intraday requests are split automatically when exceeding limits.
    - Non-minute units (daily/weekly/monthly) are retrieved in a single
      request.
    - All merged results preserve chronological order.
    """
    if not last_date:
        last_date = date.today().strftime("%Y-%m-%d")

    url = f"https://api.tradestation.com/v3/marketdata/barcharts/{symbol}"
    headers = {"Authorization": f"Bearer {token}"}

    def make_request(start: str, end: str) -> Dict:
        params = {
            "interval": interval,
            "unit": unit,
            "firstdate": start,
            "lastdate": end,
            "sessiontemplate": sessiontemplate,
        }
        params = {k: v for k, v in params.items() if v is not None}
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    if unit != "Minute":
        log.info(f"{symbol} {unit} bars {first_date} → {last_date}")
        return make_request(first_date, last_date)

    dates = np.arange(
        first_date,
        np.datetime64(last_date) + np.timedelta64(1, "D"),
        dtype="datetime64[D]",
    )
    bars_est = len(dates) * 1440 / interval
    if bars_est <= 57_600:
        log.info(f"{symbol} intraday single call (~{int(bars_est)} bars)")
        return make_request(first_date, last_date)

    max_days = int(57_600 * interval / 1440)
    chunks = []
    for i in range(0, len(dates), max_days):
        start = str(dates[i])
        end = str(dates[min(i + max_days - 1, len(dates) - 1)])
        chunks.append((start, end))
    log.info(
        f"{symbol} split into {len(chunks)} chunks (~{int(bars_est)} bars)"
    )

    merged = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(make_request, s, e): (s, e) for s, e in chunks}
        for fut in as_completed(futs):
            s, e = futs[fut]
            try:
                res = fut.result()
                log.info(f"Chunk {s} → {e}: {len(res.get('Bars', []))} bars")
                if not merged:
                    merged = res
                else:
                    for k, v in res.items():
                        if k == "Bars":
                            merged.setdefault("Bars", []).extend(v)
                        else:
                            merged[k] = v
            except Exception as e:
                log.error(f"Chunk {s} → {e} failed: {e}")

    if "Bars" in merged:
        merged["Bars"].sort(key=lambda b: b.get("Time", ""))
        log.info(f"Total merged bars for {symbol}: {len(merged['Bars'])}")
    return merged


def stream_bars(
    token: str,
    *,
    symbol: str,
    interval: int = 1,
    unit: str = "minute",
    barsback: Optional[int] = None,
    sessiontemplate: Optional[str] = None,
    reconnect_delay: int = 5,
    heartbeat_timeout: int = 60,
) -> Generator[Dict[str, Any], None, None]:
    """
    Stream live bar data for a given symbol using the TradeStation
    Market Data HTTP streaming endpoint.

    This function opens a persistent HTTP connection to the endpoint
    `/v3/marketdata/stream/barcharts/{symbol}` and yields each bar
    update as soon as it is received. If the connection drops, it is
    automatically re-established after `reconnect_delay` seconds.

    Parameters
    ----------
    token : str
        OAuth2 bearer token for the TradeStation API.
    symbol : str
        Instrument symbol to stream (e.g., "MSFT").
    interval : int, default=1
        Number of minutes per bar. Must be 1 for non-minute units.
    unit : str, default="minute"
        Bar timeframe: "minute", "daily", "weekly", "monthly".
    barsback : int, optional
        Number of historical bars to fetch before live updates.
    sessiontemplate : str, optional
        Session template to include pre/post-market data for U.S.
        equities. Valid values: "USEQPre", "USEQPost",
        "USEQPreAndPost", "USEQ24Hour", "Default".
    reconnect_delay : int, default=5
        Seconds to wait before reconnecting after a disconnection.
    heartbeat_timeout : int, default=60
        Seconds of inactivity before logging a heartbeat message.

    Yields
    ------
    dict
        JSON message containing bar data. Each update typically
        includes:
          - "Symbol": instrument name.
          - "Bars": list of bar objects with keys:
              "TimeStamp", "Open", "High", "Low", "Close", "Volume".

    Raises
    ------
    requests.exceptions.RequestException
        On HTTP or network failure.
    json.JSONDecodeError
        If a received chunk cannot be parsed as JSON.

    Notes
    -----
    - The function blocks while waiting for new data and should be
      executed in a background thread or separate process.
    - When the market is closed, the connection stays alive but no
      updates are streamed.
    - To stop streaming, break out of the generator loop manually.

    Examples
    --------
    >>> for msg in stream_bars(token, symbol="MSFT"):
    ...     if "Bars" in msg:
    ...         bar = msg["Bars"][-1]
    ...         print(bar["TimeStamp"], bar["Close"])
    """
    url = (
        f"https://api.tradestation.com/v3/marketdata/"
        f"stream/barcharts/{symbol}"
    )
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "interval": str(interval),
        "unit": unit.lower(),
        "barsback": str(barsback) if barsback else None,
        "sessiontemplate": sessiontemplate,
    }
    params = {k: v for k, v in params.items() if v is not None}

    while True:
        try:
            log.info(f"Connecting to stream for {symbol}")
            with requests.get(
                url, headers=headers, params=params,
                stream=True, timeout=90
            ) as resp:
                resp.raise_for_status()
                last_event = time.time()
                for line in resp.iter_lines():
                    if not line:
                        if time.time() - last_event > heartbeat_timeout:
                            log.info(
                                f"No data for {heartbeat_timeout}s "
                                f"({symbol} alive)"
                            )
                            last_event = time.time()
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                        last_event = time.time()
                        yield data
                    except json.JSONDecodeError:
                        log.warning(f"Invalid JSON chunk for {symbol}")
        except requests.exceptions.ChunkedEncodingError:
            log.warning(f"{symbol} chunked encoding error, reconnecting")
        except requests.exceptions.RequestException as e:
            log.error(f"{symbol} stream error: {e}")
        except Exception as e:
            log.exception(f"Unexpected stream error for {symbol}: {e}")

        log.info(f"Reconnecting {symbol} in {reconnect_delay}s")
        time.sleep(reconnect_delay)
