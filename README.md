# tradestation-api-python

Welcome!  
`tradestation-api-python` is a Python package created to simplify the use of the TradeStation APIs.

---

## ⚠️ Read Before Continuing

**Disclaimer:**  
This is an **unofficial** package. Before using it, please make sure you fully understand the TradeStation API and its capabilities. This tool is provided *as-is* and is not affiliated with or endorsed by TradeStation Technologies, Inc.

---

## 🔐 Security Notice

Before using this package in production, **always** test your setup in a **simulated environment**.  
TradeStation APIs allow you to **place and modify real orders**, which can have financial consequences.  
Make sure you have a complete understanding of how this tool and the API work before executing any trades.


## ⚙️ Concurrency and Thread Safety

This package includes **built-in thread safety** and **multi-threaded data retrieval** mechanisms to ensure reliable and performant API interactions.

### Token Management and Race Conditions

The `TokenManager` class implements a **shared lock** (`threading.Lock`) to prevent race conditions during token refresh operations.  
If multiple threads attempt to access or refresh the OAuth2 token simultaneously, only one thread performs the refresh while others wait for completion, ensuring consistent state and avoiding invalid tokens.

```python
from src.auth import TokenManager

tm = TokenManager()
token = tm.get_token()  # safely refreshed and reused across threads
```

### Multi-Threaded Historical Data Retrieval

When retrieving large historical datasets, the function `get_bars_between()` automatically:
- **splits** requests into smaller time chunks when exceeding API limits (57,600 bars per call),  
- **dispatches** them concurrently via a `ThreadPoolExecutor`,  
- and **merges** all partial results into a single, chronologically ordered response.

```python
from src.marketdata import get_bars_between

data = get_bars_between(
    token=token,
    symbol="MSFT",
    first_date="2023-01-01",
    last_date="2023-06-01",
    unit="Minute",
    interval=5,
    max_workers=10
)
```

This approach provides:
- **parallel network I/O** for faster retrieval of historical data,  
- **automatic chunking** of intraday requests,  
- **safe token reuse** across concurrent threads.

