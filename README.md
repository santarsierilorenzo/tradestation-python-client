# tradestation-api-python

<p align="center">
  <a href="https://github.com/santarsierilorenzo/tradestation-api-python/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/santarsierilorenzo/tradestation-api-python/ci.yml?style=flat-square" alt="CI/CD Pipeline"></a>
  <a href="https://coveralls.io/github/santarsierilorenzo/tradestation-api-python?branch=main"><img src="https://coveralls.io/repos/github/santarsierilorenzo/tradestation-api-python/badge.svg?branch=main" alt="Code Coverage"/></a>
  <a href="https://github.com/santarsierilorenzo/tradestation-api-python/releases"><img src="https://img.shields.io/github/v/release/santarsierilorenzo/tradestation-api-python?style=flat-square" alt="Latest Release"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg?style=flat-square" alt="Platform">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Requests-007EC6?style=for-the-badge&logo=python&logoColor=white" alt="Requests">
  <img src="https://img.shields.io/badge/PyTest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="PyTest">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/ThreadPoolExecutor-FF9F00?style=for-the-badge&logo=python&logoColor=white" alt="ThreadPoolExecutor">
  <img src="https://img.shields.io/badge/Thread%20Safe-C7253E?style=for-the-badge&logo=python&logoColor=white" alt="Thread Safety">
</p>

<p align="center">
  <b>Fully Thread-Safe · Streaming Ready · Designed for Real-Time Trading</b><br>
  <i>Developed with ❤️ by Lorenzo Santarsieri · Built for TradeStation APIs</i>
</p>


&nbsp;

## ⚠️ Disclaimer & Security
**tradestation-api-python** is an **unofficial SDK** for interacting with TradeStation APIs.  
It’s designed for research, prototyping, and automated trading integrations.  
Not affiliated with or endorsed by TradeStation Technologies, Inc.

> ⚡ **By default**, the SDK runs in the **SIM (sandbox)** environment.  
> To connect to LIVE trading, initialize `TokenManager(use_sim=False)`.

&nbsp;

## 🧩 Overview
This SDK simplifies access to TradeStation endpoints, handling:
- OAuth2 token management (with automatic refresh & thread safety)
- REST endpoints for brokerage & market data
- Streaming (real-time) data connections
- Multi-threaded data fetching for large historical datasets

&nbsp;

## 🔧 Core Modules

| Module | Description |
|--------|--------------|
| `auth.py` | Manages OAuth2 tokens, refresh logic, and race-condition prevention |
| `base_client.py` | Low-level HTTP client with retry and error handling |
| `client.py` | Unified entry point: exposes all TradeStation API services |
| `endpoints/broker.py` | Account, balance, orders & positions |
| `endpoints/mkt_data.py` | Historical & live market data |
| `endpoints/ts_stream.py` | Real-time streaming (bars, quotes, orders, etc.) |

<br>

## ⚙️ Concurrency and Streaming

### 🧵 Thread Safety
`TokenManager` ensures only one thread refreshes tokens at a time using a global lock (`threading.Lock`).

### ⚡ Parallel Data Fetch
`get_bars_between()` automatically splits large historical queries into smaller API chunks and fetches them concurrently using `ThreadPoolExecutor`.

```python
from src.client import TradeStationClient
from src.auth import TokenManager

token_manager = TokenManager(use_sim=True)
ts = TradeStationClient(token_manager=token_manager)

data = ts.market_data.get_bars_between(
    symbol="AAPL",
    first_date="2025-01-01",
    last_date="2025-02-01",
    unit="Minute",
    interval=5,
    max_workers=10
)
```

✅ Automatically merges partial results and sorts chronologically.

<br>

## 🧠 Streaming
Example of subscribing to real-time market bars:

```python
from src.client import TradeStationClient
from src.auth import TokenManager

token_manager = TokenManager(use_sim=True)
ts = TradeStationClient(token_manager=token_manager)

ts.market_data_stream.stream_bars(
    symbol="AAPL",
    interval=1,
    unit="Minute",
    on_message=lambda msg: print(msg)
)
```

Streaming endpoints auto-reconnect and use a built-in keep-alive mechanism.

<br>

## 🧪 Testing

Run the test suite to validate functionality:

```bash
pytest -v
```

Covers:
- REST requests & token refresh
- Concurrency / lock behavior
- Streaming message parsing & reconnection

<br>

## 🧰 Development Setup

The SDK includes full Docker + DevContainer support for a reproducible setup.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### 🧑‍💻 Setup Steps

**1️⃣ Clone the repository**
```bash
git clone https://github.com/santarsierilorenzo/tradestation-api-python
cd tradestation-api-python
```

**2️⃣ Open in VS Code and rebuild**
```bash
Ctrl + Shift + P  →  Dev Containers: Rebuild Without Cache and Reopen in Container
```

**3️⃣ Configure environment**
Create a `.env` file at the root with your TradeStation credentials:

```bash
TS_CLIENT_ID=your_client_id
TS_CLIENT_SECRET=your_client_secret
TS_REFRESH_TOKEN=your_refresh_token
```

**4️⃣ Run inside the container**
Open an integrated terminal and test:

```bash
python -m examples.get_market_data_example
```

> 🧩 This setup ensures a clean, isolated environment without polluting your host system.

<br>

## 🪪 License
MIT © 2025 — Developed with ❤️ by Lorenzo Santarsieri
