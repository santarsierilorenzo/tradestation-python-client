from typing import Dict
import pandas as pd


def bars_to_dataframe(
    bars_dict: Dict
) -> pd.DataFrame:
    """
    Convert a raw bars dictionary into a cleaned and structured pandas
    DataFrame.

    The input dictionary is expected to contain a "Bars" key mapping to a list
    of bar records with the following fields:
    - TimeStamp
    - Open
    - High
    - Low
    - Close
    - TotalVolume
    - UpVolume
    - DownVolume
    - OpenInterest

    The function:
    1. Loads the bars into a DataFrame.
    2. Renames columns to snake_case.
    3. Extracts `date` and `time` from the timestamp field.
    4. Removes the original timestamp.
    5. Reorders the columns.
    6. Enforces consistent numeric/string dtypes.

    Parameters
    ----------
    bars_dict : Dict
        Dictionary containing the raw bar data, typically parsed from an API
        response.

    Returns
    -------
    pandas.DataFrame
        A cleaned DataFrame with the schema:
        ['date', 'time', 'open', 'high', 'low', 'close',
         'total_volume', 'up_volume', 'down_volume', 'open_interest'].
        Dates and times are strings; numeric fields have consistent float/int
        dtypes.

    Raises
    ------
    KeyError
        If required fields are missing from the input dictionary.
    ValueError
        If timestamp parsing fails.
    """

    df = pd.DataFrame(bars_dict["Bars"])

    rename_map = {
        "TimeStamp": "timestamp",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "TotalVolume": "total_volume",
        "UpVolume": "up_volume",
        "DownVolume": "down_volume",
        "OpenInterest": "open_interest",
    }

    df = df[list(rename_map.keys())].rename(columns=rename_map)

    # Extract date & time from timestamp
    ts = pd.to_datetime(df["timestamp"])
    df["date"] = ts.dt.date.astype(str)
    df["time"] = ts.dt.time.astype(str)

    # Drop timestamp and reorder columns
    ordered_cols = [
        "date", "time", "open", "high", "low", "close",
        "total_volume", "up_volume", "down_volume", "open_interest"
    ]

    df = df[ordered_cols]

    # Enforce dtypes
    df = df.astype({
        "open": "float64",
        "high": "float64",
        "low": "float64",
        "close": "float64",
        "total_volume": "int64",
        "up_volume": "int64",
        "down_volume": "int64",
        "open_interest": "int64",
    })

    return df
