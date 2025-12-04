# tradestation-python-client

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Requests-007EC6?style=for-the-badge&logo=python&logoColor=white" alt="Requests">
  <img src="https://img.shields.io/badge/PyTest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="PyTest">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/ThreadPoolExecutor-FF9F00?style=for-the-badge&logo=python&logoColor=white" alt="ThreadPoolExecutor">
  <img src="https://img.shields.io/badge/Thread%20Safe-C7253E?style=for-the-badge&logo=python&logoColor=white" alt="Thread Safety">
</p>

<p align="center">
  <b>Fully Thread-Safe · Streaming Ready</b><br>
  <i> Built for TradeStation APIs</i>
</p>


&nbsp;

`tradestation-python-client` is an **unofficial Python client** for interacting with the TradeStation APIs.

### 📦 Installation (PyPI Package)

Install the package from **PyPI**:

```bash
pip install tradestation-python-client
```

Import it in your project:

```python
from tradestation_python_client import TradeStationClient, TokenManager
```

This repository also includes a full development environment, but the primary distribution is a **PyPI-installable client**.


### ⚠️ Disclaimer

`tradestation-python-client` is an **unofficial Python client** for interacting with the TradeStation REST and Streaming APIs.  
It is not affiliated with or endorsed by TradeStation Technologies, Inc.

- By default, it connects to the **SIM** (sandbox) environment.
- To use LIVE trading:

```python
TokenManager(use_sim=False)
```


### 🧩 Overview
This client provides:

- OAuth2 token handling with automatic refresh and thread safety  
- REST endpoints (Brokerage & Market Data)  
- Real-time streaming support  
- Parallel historical data fetching  
- Clean, modern Python interface  


### 🔧 Core Modules

| Module | Description |
|--------|-------------|
| `auth.py` | OAuth2 token management with thread-safe refresh |
| `base_client.py` | HTTP layer with retries, timeouts, and error handling |
| `client.py` | Main high-level interface for all services |
| `endpoints/broker.py` | Orders, balances, positions, accounts |
| `endpoints/mkt_data.py` | Historical + intraday market data |
| `endpoints/ts_stream.py` | Real-time streaming (bars, quotes, orders, etc.) |

### 🧪 Testing

Run the test suite:

```bash
pytest -v
```

Includes tests for:

- Token refresh  
- Thread safety  
- Streaming message parsing  
- HTTP error handling  


### 🧰 Development Environment (DevContainer + Docker)

For contributors or advanced users, the repository provides a fully reproducible development environment.

#### Prerequisites

- Docker Desktop  
- Visual Studio Code  
- Dev Containers extension  

### Setup

##### 1️⃣ Clone the repository

```bash
git clone https://github.com/santarsierilorenzo/tradestation-python-client
cd tradestation-python-client
```

##### 2️⃣ Open inside DevContainer

```
Ctrl + Shift + P → Dev Containers: Rebuild Without Cache and Reopen
```

##### 3️⃣ Configure environment variables

Create a `.env` file:

```env
TS_CLIENT_ID=your_client_id
TS_CLIENT_SECRET=your_client_secret
TS_REFRESH_TOKEN=your_refresh_token
```

##### 4️⃣ Run an example

```bash
python -m examples.get_market_data_example
```

## ⚙️ Usage Examples

#### Basic Initialization

```python
from tradestation_python_client import TradeStationClient, TokenManager

token_manager = TokenManager(use_sim=True)
ts = TradeStationClient(token_manager=token_manager)
```

#### Parallel Historical Data Fetching

```python
data = ts.market_data.get_bars_between(
    symbol="AAPL",
    first_date="2025-01-01",
    last_date="2025-02-01",
    unit="Minute",
    interval=5,
    max_workers=10
)
```

#### Real-Time Streaming

```python
ts.market_data_stream.stream_bars(
    symbol="AAPL",
    interval=1,
    unit="Minute",
    on_message=lambda msg: print(msg)
)
```


### 🪪 License
MIT © 2025 — Developed with ❤️ by Lorenzo Santarsieri
