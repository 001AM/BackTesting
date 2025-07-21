# Backend Documentation

## Overview

This backend service provides infrastructure for fetching, processing, and storing stock market data including:

* ✅ Nifty 200 companies data (scraped from Moneycontrol and NSE)
* 📈 Historical stock prices
* 📊 Fundamental company data (financials, ratios, etc.)
* 🧠 Data setup and management for backtesting

---

## Folder Structure

```
backend/
├── main.py                    # FastAPI app entrypoint
├── api/v1/endpoints/
│   ├── populate.py           # Endpoints to populate company data
│   ├── stock_data.py         # Endpoints for stock filtering/statistics
│   └── back_test.py          # Endpoint to run backtesting
├── services/
│   ├── populate_services.py  # Data population logic from external sources
│   ├── back_test_services.py # Core backtest simulation engine
│   ├── back_test_metrics.py  # Risk and return metric calculators
│   └── stock_data_services.py # Stock api logic
├── db/
│   └── session.py            # SQLAlchemy DB session handler
├── models/
│   ├── database.py           # SQLAlchemy ORM table definitions
│   └── schemas.py            # Pydantic models for request/response
├── config/
│   └── settings.py           # App config and env variable loader
```

---

## 🗂 Models & Schemas

### `Company` (ORM Model)

* Table: `companies`
* Fields:

  * `id`, `symbol`, `name`, `sector`, `industry`
  * `market_cap_category`, `exchange`, `is_active`
  * `created_at`, `updated_at`
* Relationships:

  * `prices` → StockPrice
  * `fundamentals` → FundamentalData
  * `updates` → DataUpdateLog

### `StockPrice` (ORM Model)

* Table: `stock_prices`
* Fields:

  * `id`, `company_id`, `date`
  * `open`, `high`, `low`, `close`, `adjusted_close`, `volume`
  * `created_at`

### `FundamentalData` (ORM Model)

* Table: `fundamental_data`
* Fields include:

  * **Profit & Loss**: `revenue`, `pat`, `ebitda`, `operating_profit`, `interest_expense`
  * **Balance Sheet**: `total_assets`, `total_liabilities`, `shareholders_equity`, `cash_and_equivalents`, `total_debt`
  * **Cash Flow**: `operating_cash_flow`, `capex`, `free_cash_flow`
  * **Market**: `market_cap`, `shares_outstanding`
  * **Ratios**: `roce`, `roe`, `roa`, `eps`, `pe_ratio`, `pb_ratio`, `debt_to_equity`, `current_ratio`, `quick_ratio`, `gross_margin`, `operating_margin`, `net_margin`
  * Timestamps: `created_at`, `updated_at`

### `DataUpdateLog` (ORM Model)

* Table: `data_update_logs`
* Fields:

  * `id`, `company_id`, `data_type`, `last_update_date`, `status`, `error_message`, `records_updated`, `created_at`

---

### `schemas.py` (Pydantic Models)

#### `ResponseModel`

* Generic API response format

```json
{
  "message": "success",
  "data": ...,
  "errors": ...
}
```

#### `CompanyCreate`

* Used to create a company

```json
{
  "symbol": "TCS",
  "name": "Tata Consultancy Services",
  "sector": "IT",
  "industry": "Software",
  "market_cap_category": "Large",
  "exchange": "NSE",
  "is_active": true
}
```

#### `StockFilterParams`

* Query filters:

  * `sector`, `min_market_cap`, `pe_min`, `pe_max`, `search`

#### `StockStatsResponse`

* Response for `/stocks/statistics/`

  * `total_stocks`, `total_sectors`, `data_completeness`, `last_updated`

#### `SymbolListRequest`

```json
{
  "symbol_list": ["TCS", "INFY"]
}
```

#### `BacktestRequest`

```json
{
  "start_date": "2020-01-01",
  "end_date": "2023-01-01",
  "portfolio_size": 20,
  "rebalancing_frequency": "quarterly",
  "weighting_method": "equal",
  "initial_capital": 1000000,
  "min_market_cap": 1000,
  "max_market_cap": 100000,
  "min_roce": 15,
  "pat_positive": 10,
  "ranking_metrics": [{"roe": true}],
  "benchmark_symbol": "NIFTY50"
}
```

---


## 🔌 FastAPI Services

Defined in:

* `services/populate_services.py`
* `services/back_test_services.py`
* `services/back_test_metrics.py`
* `services/stock_data_services.py`

Each file exposes REST services grouped by functionality.

---

### 1. `CompanyService`

Handles all database operations related to companies.

#### Key Methods:

* `company_exists(symbol)`: Checks if a company is already in the database.
* `company_create(company_data)`: Adds a new company to the database.
* `get_companies()`: Full pipeline:

  * Scrapes company names
  * Resolves symbols
  * Fetches company details from Yahoo Finance
  * Adds to DB and triggers data collection

---

### 2. `SeleniumScrapper`

Scrapes Nifty 200 companies using Selenium.

#### Key Methods:

* `get_nifty200()`: Extracts names of companies from Moneycontrol.
* `get_nifty200_symbol()`: Extracts symbols from NSE.
* `_handle_popups()`: Dismisses site popups.
* `_try_multiple_selectors()`: Attempts different selectors to scrape reliably.

---

### 3. `ScreenerSymbolExtractor`

Maps company names to symbols using Screener.in.

#### Key Methods:

* `search_and_get_symbol(company_name)`: Searches for a company and extracts its NSE symbol.
* `get_symbols_for_companies(list_of_names)`: Batch extraction of symbols using above method.

---

### 4. `HistoricalDataCollector`

Fetches historical price data for companies via Yahoo Finance.

#### Key Methods:

* `collect_all_historical_data(period)`: Collects for all companies in batches.
* `collect_company_historical_data(symbol, period)`: Fetches historical price data for a company.
* `update_latest_prices()`: Fetches last 5 days of price data.

---

### 5. `FundamentalDataCollector`

Fetches and stores financial statements and ratios.

#### Key Methods:

* `collect_all_fundamental_data()`: Triggers full collection for all companies.
* `collect_all_periods_fundamental_data(symbol)`: Annual and Quarterly data fetching.
* `_create_comprehensive_fundamental_record(...)`: Normalizes raw data into a `FundamentalData` record.
* `_calculate_financial_ratios(...)`: Computes key metrics like ROE, ROA, ROCE, EPS, etc.

---

### 6. `BacktestingDataManager`

Manages all bulk operations and setups for analysis/backtesting.

#### Key Methods:

* `setup_backtesting_data()`: Full pipeline from scraping to storage.
* `fast_setup_backtesting_data(symbols)`: Setup based on predefined symbol list.
* `setup_nifty200_data()`: Shortcut to process Nifty 200 only.
* `update_all_data()`: Routine updater.
* `generate_data_quality_report()`: Logs completeness of data across companies.

---
### 7. `BackTestServices`

* Takes cleaned historical and fundamental data
* Filters universe based on user criteria (ROCE, PAT, etc.)
* Ranks using metrics like ROE, Market Cap, etc.
* Builds portfolio & rebalances at intervals

---

### 8. `PerformanceMetrics`

* Calculates:

  * Cumulative Return
  * Annual Return
  * Volatility
  * Sharpe Ratio
  * Max Drawdown
* Compares vs benchmark index like NIFTY50

---
### 9. `StockDataServices`

* Used to get stock data
* Filters data according to symbol, company, etc.

---
## 🔌 FastAPI Endpoints

Defined in:

* `api/v1/endpoints/populate.py`
* `api/v1/endpoints/stock_data.py`
* `api/v1/endpoints/back_test.py`

Each file exposes REST endpoints grouped by functionality.

---

### 📥 `/api/v1/populate/` — Company & Data Initialization

#### `POST /populate/companies/`

**Purpose**: Scrapes Nifty 200 companies → resolves symbols → fetches from Yahoo → saves to DB
**Calls**:

* `SeleniumScrapper`
* `ScreenerSymbolExtractor`
* `CompanyService`
* `HistoricalDataCollector`
* `FundamentalDataCollector`

#### `POST /populate/companies/symbols/`

**Purpose**: Populate based on a user-given list of company names
**Body**: `{ "symbol_list": ["TCS", "INFY", ...] }`

#### `GET /populate/quality_report/`

**Purpose**: Returns data completeness and freshness report
**Calls**: `BacktestingDataManager.generate_data_quality_report()`

---

### 📊 `/api/v1/stocks/` — Stock Filtering, Stats

#### `GET /stocks/universe/`

**Purpose**: Filter stocks based on query params like sector, PE, market cap
**Query Params**: `sector`, `min_market_cap`, `pe_min`, `pe_max`, `search`
**Calls**: SQLAlchemy ORM queries on `FundamentalData`

#### `GET /stocks/statistics/`

**Purpose**: Returns:

* total stocks
* number of sectors
* data completeness score
* last update date
  **Calls**: Aggregates from `Company` and `FundamentalData`

---

### 📈 `/api/v1/backtest/` — Run Backtest Simulation

#### `POST /backtest/backtest/`

**Purpose**: Core endpoint to execute a backtest
**Body**:

```json
{
  "start_date": "2020-01-01",
  "end_date": "2023-01-01",
  "portfolio_size": 20,
  "rebalancing_frequency": "quarterly",
  "weighting_method": "equal",
  "initial_capital": 1000000,
  "benchmark_symbol": "NIFTY50",
  "min_roce": 15,
  "ranking_metrics": [{"roe": true}]
}
```

**Returns**: Portfolio results with performance metrics
**Calls**:

* `BackTestServices.run_backtest()`
* `PerformanceMetrics.calculate_comprehensive_metrics(results)`

---

