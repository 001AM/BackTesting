from datetime import datetime, date, timedelta
from decimal import Decimal
from threading import Lock
from typing import Optional, List, Dict
from uuid import UUID
from functools import lru_cache
import concurrent.futures
import logging
import re
import time

import numpy as np
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from backend.models.database import Company, StockPrice, FundamentalData
from backend.models.schemas import CompanyCreate


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.db_lock = Lock()  # Thread safety for database operations

    def company_exists(self, symbol: str) -> bool:
        return self.db.query(Company).filter_by(symbol=symbol).first() is not None

    def company_create(self, company_data: Dict) -> bool:
        if not company_data or not company_data.get("symbol"):
            return False
        
        with self.db_lock:  # Thread-safe database operations
            if self.company_exists(company_data["symbol"]):
                logger.info(f"Skipping duplicate: {company_data['symbol']}")
                return False
            
            company_create = Company(
                symbol=company_data["symbol"],
                name=company_data["name"],
                sector=company_data["sector"],
                industry=company_data["industry"],
                market_cap_category=company_data["market_cap_category"],
                exchange=company_data["exchange"],
                is_active=company_data.get("is_active", True)
            )
            self.db.add(company_create)
            self.db.commit()
            logger.info(f"Added company: {company_data['symbol']}")
            return True

    def get_companies(self) -> bool:
        companies_list = SeleniumScrapper().get_nifty200()
        if not companies_list:
            logger.error("Failed to fetch companies list")
            return False
        print(companies_list)
        screener = ScreenerSymbolExtractor()
        symbols = screener.get_symbols_for_companies(companies_list)

        # Process symbols in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.get_company_data_from_yahoo, symbol): symbol 
                for symbol in symbols
            }
            
            # Process completed tasks
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    company_data = future.result()
                    if company_data:
                        created = self.company_create(company_data)
                        if created:
                            # Fetch all extra data if company was newly added
                            HistoricalDataCollector(self.db).collect_company_historical_data(company_data['symbol'], period="20y")
                            FundamentalDataCollector(self.db).collect_company_fundamental_data(company_data['symbol'])
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")

        return True

    @lru_cache(maxsize=1000)
    def get_company_data_from_yahoo(self, symbol: str) -> Optional[Dict]:
        try:
            yf_symbol = f"{symbol}.NS"
            stock = yf.Ticker(yf_symbol)
            info = stock.info

            if not info or 'symbol' not in info:
                return None

            market_cap = info.get('marketCap', 0)
            if market_cap > 2e10:
                category = 'Large'
            elif market_cap > 5e9:
                category = 'Mid'
            else:
                category = 'Small'

            return {
                'symbol': symbol,
                'name': info.get('longName') or info.get('shortName') or symbol,
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap_category': category,
                'exchange': 'NSE',
                'is_active': True
            }

        except Exception as e:
            logger.error(f"Error fetching Yahoo data for {symbol}: {e}")
            return None

class SeleniumScrapper:
    def __init__(self, headless: bool = True):
        options = webdriver.ChromeOptions()
        
        # Optimized options for speed
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Speed optimizations
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # Don't load images
        options.add_argument('--disable-javascript')  # Disable JS if not needed
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        if headless:
            options.add_argument('--headless')
            
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Reduced timeout for faster failure detection
        self.wait = WebDriverWait(self.driver, 15)

    def get_nifty200(self) -> List[str]:
        try:
            url = "https://www.moneycontrol.com/stocks/marketstats/indexcomp.php?optex=NSE&opttopic=indexcomp&index=49"
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Reduced wait time
            time.sleep(2)
            
            # Try to handle any popups first
            self._handle_popups()
            
            # Try multiple selectors for the company names
            companies = self._try_multiple_selectors()
            
            if not companies:
                logger.error("No companies found with any selector")
                return []
            
            logger.info(f"✅ Fetched {len(companies)} companies from Moneycontrol")
            return companies

        except Exception as e:
            logger.exception("❌ Error fetching Nifty 200 list:")
            return []

        finally:
            self.driver.quit()

    def _handle_popups(self):
        """Handle any popups that might appear - optimized"""
        try:
            popup_selectors = [
                '.qc-cmp2-summary-buttons__button',
                '.popup-close',
                '.close-button',
                '[data-dismiss="modal"]',
                '.modal-close'
            ]
            
            for selector in popup_selectors:
                try:
                    popup = WebDriverWait(self.driver, 1).until(  # Reduced timeout
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    popup.click()
                    logger.info(f"Closed popup with selector: {selector}")
                    break  # Exit after first successful popup close
                except TimeoutException:
                    continue
                    
        except Exception as e:
            logger.debug(f"No popups to handle: {e}")

    def _try_multiple_selectors(self) -> List[str]:
        """Try multiple selectors to find company names - optimized order"""
        # Ordered by most likely to work first
        selectors = [
            '//span[contains(@class, "ReuseTable_gld13")]/a',
            '//table//td/a[contains(@href, "/company/")]',
            '//a[contains(@href, "/company/")]',
            '//table//tr/td[1]/a',
            '//table//a[contains(@href, "company")]',
            '//div[contains(@class, "companyname")]/a',
            '//span[contains(@class, "companyname")]/a',
            '//a[contains(@class, "company")]'
        ]
        
        for selector in selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, selector)))
                
                companies = []
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 2:
                        companies.append(text)
                
                if companies:
                    logger.info(f"✅ Found {len(companies)} companies with selector: {selector}")
                    return companies[:200]
                    
            except TimeoutException:
                logger.debug(f"Selector failed: {selector}")
                continue
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        return []

class ScreenerSymbolExtractor:
    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        
        # Speed optimizations
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Additional speed optimizations
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        if headless:
            options.add_argument('--headless')
            
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Reduced timeout
        self.wait = WebDriverWait(self.driver, 10)
        
    def search_and_get_symbol(self, company_name):
        """Search for company on Screener.in and extract symbol - optimized"""
        try:
            print(f"Searching for: {company_name}")
            
            # Go to Screener.in
            self.driver.get("https://www.screener.in/")
            
            # Reduced wait time
            time.sleep(2.5)
            
            print("Current page:", self.driver.current_url)

            try:
                print("Waiting for input box...")
                
                # Reduced wait time for input box
                self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.home-search input[type="search"]')
                ))

                search_box = self.driver.find_element(By.CSS_SELECTOR, 'div.home-search input[type="search"]')
                search_box.click()
                search_box.clear()
                
                # Faster typing - send all at once instead of character by character
                search_box.send_keys(company_name)
                search_box.send_keys(Keys.RETURN)
                time.sleep(2)  # Reduced wait time

            except Exception as e:
                print("❌ Failed to locate search box:", e)
                return None

            # Wait for redirect with reduced timeout
            try:
                WebDriverWait(self.driver, 2.5).until(EC.url_contains('/company/'))
            except TimeoutException:
                print(f"⚠️ No redirect for {company_name}")

            symbol = self._extract_symbol_from_screener_page()
            if symbol:
                print(f"Found symbol: {symbol}")
                return symbol
            
            print(f"No symbol found for: {company_name}")
            return None
            
        except Exception as e:
            print(f"Error searching for {company_name} on Screener: {e}")
            return None
    
    def _extract_symbol_from_screener_page(self):
        """Extract NSE symbol from Screener.in company page - optimized order"""
        try:
            

            # Method 1: From <div class="company-links">
            try:
                nse_spans = self.driver.find_elements(By.XPATH,
                    '//div[contains(@class, "company-links")]//span[contains(text(), "NSE:")]')
                for span in nse_spans:
                    text = span.text.strip()
                    if "NSE:" in text:
                        symbol = text.split("NSE:")[1].strip()
                        if symbol.isalnum():
                            return symbol.upper()
            except Exception:
                pass
            
            # Method 1: From URL (fastest method first)
            current_url = self.driver.current_url
            if '/company/' in current_url:
                url_parts = current_url.rstrip('/').split('/')
                symbol = url_parts[-1]
                if symbol and symbol.replace('-', '').isalnum():
                    return symbol.upper()
                
            # Method 3: From page title
            try:
                title = self.driver.title
                if 'NSE:' in title:
                    return title.split('NSE:')[1].strip().split()[0].upper()
            except:
                pass

            # Method 4: Regex from HTML (last resort)
            try:
                html = self.driver.page_source
                match = re.search(r'NSE:\s*([A-Z]{3,10})', html)
                if match:
                    return match.group(1).upper()
            except:
                pass

            return None

        except Exception as e:
            print(f"Error extracting NSE symbol: {e}")
            return None

    def get_symbols_for_companies(self, company_names):
        """Get symbols for a list of company names - with parallel processing"""
        # Process in batches to avoid overwhelming the server
        batch_size = 10
        symbols = []
        
        for i in range(0, len(company_names), batch_size):
            batch = company_names[i:i + batch_size]
            batch_symbols = []
            
            for company_name in batch:
                if not company_name.strip():
                    continue
                symbol = self.search_and_get_symbol(company_name)
                if symbol:
                    batch_symbols.append(symbol)
                time.sleep(0.5)  # Reduced sleep time but still respectful
            
            symbols.extend(batch_symbols)
            
            # Small pause between batches
            if i + batch_size < len(company_names):
                time.sleep(1)
        
        return symbols
    
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

class HistoricalDataCollector:
    def __init__(self, db: Session):
        self.db = db
        self.db_lock = Lock()
        self.failed_symbols = set()

    def collect_all_historical_data(self, period: str = "20y", batch_size: int = 10) -> bool:
        """
        Collect historical data for all companies in the database
        period: '1y', '2y', '5y', '20y', 'max'
        """
        companies = self.db.query(Company).filter(Company.is_active == True).all()
        
        if not companies:
            logger.error("No companies found in database")
            return False

        logger.info(f"Starting historical data collection for {len(companies)} companies")
        
        # Process companies in batches to avoid overwhelming the API
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_company = {
                    executor.submit(self.collect_company_historical_data, company.symbol, period): company
                    for company in batch
                }
                
                for future in concurrent.futures.as_completed(future_to_company):
                    company = future_to_company[future]
                    try:
                        success = future.result()
                        if success:
                            logger.info(f"✅ Historical data collected for {company.symbol}")
                        else:
                            logger.warning(f"❌ Failed to collect data for {company.symbol}")
                            self.failed_symbols.add(company.symbol)
                    except Exception as e:
                        logger.error(f"Error processing {company.symbol}: {e}")
                        self.failed_symbols.add(company.symbol)
            
            # Small pause between batches
            time.sleep(1)
        
        logger.info(f"Historical data collection completed. Failed symbols: {len(self.failed_symbols)}")
        return True

    def collect_company_historical_data(self, symbol: str, period: str = "20y") -> bool:
        """Collect historical price data for a specific company"""
        try:
            # Get company from database
            company = self.db.query(Company).filter(Company.symbol == symbol).first()
            if not company:
                logger.error(f"Company {symbol} not found in database")
                return False

            # Check if we already have recent data
            if self._has_recent_data(company.id):
                logger.info(f"Recent data already exists for {symbol}, skipping...")
                return True

            # Fetch data from Yahoo Finance
            yf_symbol = f"{symbol}.NS"
            stock = yf.Ticker(yf_symbol)
            
            # Get historical data
            hist_data = stock.history(period=period)
            
            if hist_data.empty:
                logger.warning(f"No historical data found for {symbol}")
                return False

            # Insert data into database
            return self._insert_historical_data(company.id, hist_data)

        except Exception as e:
            logger.error(f"Error collecting historical data for {symbol}: {e}")
            return False

    def _has_recent_data(self, company_id: int, days_threshold: int = 7) -> bool:
        """Check if we have recent data for the company"""
        recent_date = datetime.now() - timedelta(days=days_threshold)
        
        latest_record = self.db.query(StockPrice).filter(
            and_(
                StockPrice.company_id == company_id,
                StockPrice.date >= recent_date.date()
            )
        ).first()
        
        return latest_record is not None

    def _insert_historical_data(self, company_id: int, hist_data: pd.DataFrame) -> bool:
        """Insert historical data into database"""
        try:
            records_to_insert = []
            
            for date_idx, row in hist_data.iterrows():
                # Skip if data already exists
                existing = self.db.query(StockPrice).filter(
                    and_(
                        StockPrice.company_id == company_id,
                        StockPrice.date == date_idx.date()
                    )
                ).first()
                
                if existing:
                    continue
                
                # Create new record
                stock_price = StockPrice(
                    company_id=company_id,
                    date=date_idx.date(),
                    open=round(float(row['Open']), 4) if pd.notna(row['Open']) else None,
                    high=round(float(row['High']), 4) if pd.notna(row['High']) else None,
                    low=round(float(row['Low']), 4) if pd.notna(row['Low']) else None,
                    close=round(float(row['Close']), 4) if pd.notna(row['Close']) else None,
                    adjusted_close=round(float(row['Close']), 4) if pd.notna(row['Close']) else None,
                    volume=int(row['Volume']) if pd.notna(row['Volume']) and row['Volume'] > 0 else None
                )
                records_to_insert.append(stock_price)
            
            if records_to_insert:
                with self.db_lock:
                    self.db.add_all(records_to_insert)
                    self.db.commit()
                    logger.info(f"Inserted {len(records_to_insert)} price records")
            
            return True

        except Exception as e:
            logger.error(f"Error inserting historical data: {e}")
            self.db.rollback()
            return False

    def update_latest_prices(self) -> bool:
        """Update latest prices for all companies"""
        companies = self.db.query(Company).filter(Company.is_active == True).all()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_company = {
                executor.submit(self.collect_company_historical_data, company.symbol, "5d"): company
                for company in companies
            }
            
            success_count = 0
            for future in concurrent.futures.as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error updating {company.symbol}: {e}")
        
        logger.info(f"Updated prices for {success_count}/{len(companies)} companies")
        return True

class FundamentalDataCollector:
    def __init__(self, db: Session):
        self.db = db
        self.db_lock = Lock()

    def collect_all_fundamental_data(self, batch_size: int = 5) -> bool:
        """Collect fundamental data for all companies"""
        companies = self.db.query(Company).filter(Company.is_active == True).all()
        
        if not companies:
            logger.error("No companies found in database")
            return False

        logger.info(f"Starting fundamental data collection for {len(companies)} companies")
        
        # Process in smaller batches for fundamental data (more intensive)
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_company = {
                    executor.submit(self.collect_company_fundamental_data, company.symbol): company
                    for company in batch
                }
                
                for future in concurrent.futures.as_completed(future_to_company):
                    company = future_to_company[future]
                    try:
                        success = future.result()
                        if success:
                            logger.info(f"✅ Fundamental data collected for {company.symbol}")
                        else:
                            logger.warning(f"❌ Failed to collect fundamental data for {company.symbol}")
                    except Exception as e:
                        logger.error(f"Error processing fundamentals for {company.symbol}: {e}")
            
            # Longer pause between batches for fundamental data
            time.sleep(2)
        
        logger.info("Fundamental data collection completed")
        return True

    def collect_company_fundamental_data(self, symbol: str) -> bool:
        """Collect fundamental data for a specific company"""
        try:
            company = self.db.query(Company).filter(Company.symbol == symbol).first()
            if not company:
                logger.error(f"Company {symbol} not found in database")
                return False

            # Get data from Yahoo Finance
            yf_symbol = f"{symbol}.NS"
            stock = yf.Ticker(yf_symbol)
            
            # Get various data
            info = stock.info
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            # Process quarterly and annual data
            success = True
            
            # Process financials if available
            if not financials.empty:
                success &= self._process_financial_data(company.id, financials, 'A')
            
            # Process balance sheet if available
            if not balance_sheet.empty:
                success &= self._process_balance_sheet_data(company.id, balance_sheet, 'A')
            
            # Process cash flow if available
            if not cash_flow.empty:
                success &= self._process_cash_flow_data(company.id, cash_flow, 'A')
            
            # Add current market data
            if info:
                success &= self._add_current_market_data(company.id, info)
            
            return success

        except Exception as e:
            logger.error(f"Error collecting fundamental data for {symbol}: {e}")
            return False

    def _process_financial_data(self, company_id: int, financials: pd.DataFrame, period_type: str) -> bool:
        """Process financial statement data"""
        try:
            for date_col in financials.columns:
                report_date = date_col.date()
                
                # Check if record already exists
                existing = self.db.query(FundamentalData).filter(
                    and_(
                        FundamentalData.company_id == company_id,
                        FundamentalData.report_date == report_date,
                        FundamentalData.period_type == period_type
                    )
                ).first()
                
                if existing:
                    continue
                
                # Extract financial data
                revenue = self._safe_get_value(financials, 'Total Revenue', date_col)
                net_income = self._safe_get_value(financials, 'Net Income', date_col)
                ebitda = self._safe_get_value(financials, 'EBITDA', date_col)
                operating_income = self._safe_get_value(financials, 'Operating Income', date_col)
                interest_expense = self._safe_get_value(financials, 'Interest Expense', date_col)
                
                # Create fundamental data record
                fundamental_data = FundamentalData(
                    company_id=company_id,
                    report_date=report_date,
                    period_type=period_type,
                    revenue=revenue,
                    pat=net_income,
                    ebitda=ebitda,
                    operating_profit=operating_income,
                    interest_expense=interest_expense
                )
                
                with self.db_lock:
                    self.db.add(fundamental_data)
                    self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing financial data: {e}")
            return False

    def _process_balance_sheet_data(self, company_id: int, balance_sheet: pd.DataFrame, period_type: str) -> bool:
        """Process balance sheet data"""
        try:
            for date_col in balance_sheet.columns:
                report_date = date_col.date()
                
                # Find or create the fundamental data record
                fundamental_data = self.db.query(FundamentalData).filter(
                    and_(
                        FundamentalData.company_id == company_id,
                        FundamentalData.report_date == report_date,
                        FundamentalData.period_type == period_type
                    )
                ).first()
                
                if not fundamental_data:
                    fundamental_data = FundamentalData(
                        company_id=company_id,
                        report_date=report_date,
                        period_type=period_type
                    )
                
                # Extract balance sheet data
                fundamental_data.total_assets = self._safe_get_value(balance_sheet, 'Total Assets', date_col)
                fundamental_data.total_liabilities = self._safe_get_value(balance_sheet, 'Total Liabilities Net Minority Interest', date_col)
                fundamental_data.shareholders_equity = self._safe_get_value(balance_sheet, 'Total Equity Gross Minority Interest', date_col)
                fundamental_data.cash_and_equivalents = self._safe_get_value(balance_sheet, 'Cash And Cash Equivalents', date_col)
                fundamental_data.total_debt = self._safe_get_value(balance_sheet, 'Total Debt', date_col)
                
                with self.db_lock:
                    self.db.merge(fundamental_data)
                    self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing balance sheet data: {e}")
            return False

    def _process_cash_flow_data(self, company_id: int, cash_flow: pd.DataFrame, period_type: str) -> bool:
        """Process cash flow data"""
        try:
            for date_col in cash_flow.columns:
                report_date = date_col.date()
                
                # Find or create the fundamental data record
                fundamental_data = self.db.query(FundamentalData).filter(
                    and_(
                        FundamentalData.company_id == company_id,
                        FundamentalData.report_date == report_date,
                        FundamentalData.period_type == period_type
                    )
                ).first()
                
                if not fundamental_data:
                    fundamental_data = FundamentalData(
                        company_id=company_id,
                        report_date=report_date,
                        period_type=period_type
                    )
                
                # Extract cash flow data
                fundamental_data.operating_cash_flow = self._safe_get_value(cash_flow, 'Operating Cash Flow', date_col)
                fundamental_data.capex = self._safe_get_value(cash_flow, 'Capital Expenditure', date_col)
                
                # Calculate free cash flow
                if fundamental_data.operating_cash_flow and fundamental_data.capex:
                    fundamental_data.free_cash_flow = fundamental_data.operating_cash_flow + fundamental_data.capex
                
                with self.db_lock:
                    self.db.merge(fundamental_data)
                    self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing cash flow data: {e}")
            return False

    def _add_current_market_data(self, company_id: int, info: dict) -> bool:
        """Add current market data and ratios"""
        try:
            # Get the most recent fundamental data record
            latest_fundamental = self.db.query(FundamentalData).filter(
                FundamentalData.company_id == company_id
            ).order_by(desc(FundamentalData.report_date)).first()
            
            if not latest_fundamental:
                # Create a new record with current date
                latest_fundamental = FundamentalData(
                    company_id=company_id,
                    report_date=datetime.now().date(),
                    period_type='C'  # Current
                )
            
            # Update with current market data
            latest_fundamental.market_cap = self._safe_get_info_value(info, 'marketCap')
            latest_fundamental.shares_outstanding = self._safe_get_info_value(info, 'sharesOutstanding')
            latest_fundamental.pe_ratio = self._safe_get_info_value(info, 'trailingPE')
            latest_fundamental.pb_ratio = self._safe_get_info_value(info, 'priceToBook')
            latest_fundamental.eps = self._safe_get_info_value(info, 'trailingEps')
            latest_fundamental.roe = self._safe_get_info_value(info, 'returnOnEquity')
            latest_fundamental.roa = self._safe_get_info_value(info, 'returnOnAssets')
            latest_fundamental.debt_to_equity = self._safe_get_info_value(info, 'debtToEquity')
            latest_fundamental.current_ratio = self._safe_get_info_value(info, 'currentRatio')
            latest_fundamental.quick_ratio = self._safe_get_info_value(info, 'quickRatio')
            latest_fundamental.gross_margin = self._safe_get_info_value(info, 'grossMargins')
            latest_fundamental.operating_margin = self._safe_get_info_value(info, 'operatingMargins')
            latest_fundamental.net_margin = self._safe_get_info_value(info, 'profitMargins')
            
            with self.db_lock:
                self.db.merge(latest_fundamental)
                self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding current market data: {e}")
            return False

    def _safe_get_value(self, df: pd.DataFrame, key: str, date_col) -> Optional[Decimal]:
        """Safely get value from DataFrame"""
        try:
            if key in df.index:
                value = df.loc[key, date_col]
                if pd.notna(value) and value != 0:
                    return Decimal(str(float(value)))
        except (KeyError, ValueError, TypeError):
            pass
        return None

    def _safe_get_info_value(self, info: dict, key: str) -> Optional[Decimal]:
        """Safely get value from info dictionary"""
        try:
            value = info.get(key)
            if value is not None and value != 0:
                return Decimal(str(float(value)))
        except (ValueError, TypeError):
            pass
        return None

class BacktestingDataManager:
    def __init__(self, db: Session):
        self.db = db
        self.historical_collector = HistoricalDataCollector(db)
        self.fundamental_collector = FundamentalDataCollector(db)
        self.company = CompanyService(db)
        self.db_lock = Lock()  

    def setup_backtesting_data(self, period: str = "20y") -> bool:
        """Complete setup for backtesting data"""
        logger.info("🚀 Starting backtesting data setup...")
        companies_list = SeleniumScrapper().get_nifty200()
        if not companies_list:
            logger.error("Failed to fetch companies list")
            return False

        batch_size = 10
        for i in range(0, len(companies_list), batch_size):
            batch = companies_list[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(companies_list) + batch_size - 1)//batch_size}")
            
            # Process each company in the batch
            for company_name in batch:
                if not company_name.strip():
                    continue
                    
                try:
                    # Get symbol for this company
                    screener = ScreenerSymbolExtractor()
                    symbol = screener.search_and_get_symbol(company_name)
                    
                    if not symbol:
                        logger.warning(f"No symbol found for: {company_name}")
                        continue
                    
                    # Get company data from Yahoo
                    company_data = self.company.get_company_data_from_yahoo(symbol)
                    if not company_data:
                        logger.warning(f"No company data found for: {symbol}")
                        continue
                    
                    # Create company record
                    created = self.company.company_create(company_data)
                    if created:
                        logger.info(f"✅ Created company: {symbol}")
                        
                        # Immediately collect historical data
                        logger.info(f"📊 Collecting historical data for {symbol}...")
                        historical_success = self.historical_collector.collect_company_historical_data(symbol, period="20y")
                        if historical_success:
                            logger.info(f"✅ Historical data collected for {symbol}")
                        else:
                            logger.warning(f"❌ Historical data collection failed for {symbol}")
                        
                        # Immediately collect fundamental data
                        logger.info(f"📈 Collecting fundamental data for {symbol}...")
                        fundamental_success = self.fundamental_collector.collect_company_fundamental_data(symbol)
                        if fundamental_success:
                            logger.info(f"✅ Fundamental data collected for {symbol}")
                        else:
                            logger.warning(f"❌ Fundamental data collection failed for {symbol}")
                    else:
                        logger.info(f"Company {symbol} already exists, skipping data collection")
                    
                    # Small delay to be respectful to APIs
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing {company_name}: {e}")
                    continue
            
            # Pause between batches
            logger.info(f"Batch {i//batch_size + 1} completed. Pausing before next batch...")
            time.sleep(2)
        
        logger.info("✅ All companies processed successfully!")
        
        # Step 3: Generate data quality report
        self.generate_data_quality_report()
        
        logger.info("✅ Backtesting data setup completed successfully!")
        return True

    def update_all_data(self) -> bool:
        """Update all data (daily routine)"""
        logger.info("🔄 Updating all data...")
        
        # Update latest prices
        self.historical_collector.update_latest_prices()
        
        # Update fundamental data (weekly)
        current_date = datetime.now()
        if current_date.weekday() == 0:  # Monday
            self.fundamental_collector.collect_all_fundamental_data()
        
        logger.info("✅ Data update completed!")
        return True

    def generate_data_quality_report(self):
        """Generate a data quality report"""
        logger.info("📋 Generating data quality report...")
        
        # Count companies
        total_companies = self.db.query(Company).count()
        
        # Count price records
        total_price_records = self.db.query(StockPrice).count()
        
        # Count fundamental records
        total_fundamental_records = self.db.query(FundamentalData).count()
        
        # Companies with recent price data
        recent_date = datetime.now() - timedelta(days=7)
        companies_with_recent_data = self.db.query(Company).join(StockPrice).filter(
            StockPrice.date >= recent_date.date()
        ).distinct().count()
        
        # Companies with fundamental data
        companies_with_fundamentals = self.db.query(Company).join(FundamentalData).distinct().count()
        
        logger.info(f"""
        📊 DATA QUALITY REPORT
        ═══════════════════════════════════════
        Total Companies: {total_companies}
        Total Price Records: {total_price_records:,}
        Total Fundamental Records: {total_fundamental_records:,}
        Companies with Recent Prices: {companies_with_recent_data}/{total_companies}
        Companies with Fundamentals: {companies_with_fundamentals}/{total_companies}
        Data Coverage: {(companies_with_recent_data/total_companies)*100:.1f}%
        ═══════════════════════════════════════
        """)

    def get_backtesting_universe(self, min_history_days: int = 252) -> List[str]:
        """Get list of symbols suitable for backtesting"""
        min_date = datetime.now() - timedelta(days=min_history_days)
        
        companies = self.db.query(Company).join(StockPrice).filter(
            StockPrice.date <= min_date.date()
        ).distinct().all()
        
        return [company.symbol for company in companies]

