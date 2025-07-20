# Standard Library
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import lru_cache
from threading import Lock
from typing import Optional, List, Dict, Any
from uuid import UUID
import concurrent.futures
import logging
import re
import time

# Third-party Libraries
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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# SQLAlchemy
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

# Project Modules
from backend.models.database import Company, StockPrice, FundamentalData, DataUpdateLog
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
        service = Service("/usr/lib/chromium/chromedriver")
        try:
            # Check if chromedriver is in PATH
            service = Service('/usr/local/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"System ChromeDriver not found, trying ChromeDriverManager: {e}")
            try:
                # Use ChromeDriverManager as fallback
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception as e2:
                print(f"ChromeDriverManager failed: {e2}")
                # Last resort - try without explicit service
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

    def get_nifty200_symbol(self) -> List[str]:
        try:
            url = "https://www.nseindia.com/market-data/live-equity-market?symbol=NIFTY%20200"
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)

            # Wait for the table to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table#equityStockTable")))

            # Let JS-rendered content finish loading (use sleep or wait for visibility of row count)
            time.sleep(2)

            # Extract all symbols by locating anchor tags in first column
            symbol_elements = self.driver.find_elements(By.CSS_SELECTOR, "table#equityStockTable tbody tr td a")

            # Filter only valid symbols (should be in uppercase typically)
            symbols = [elem.text.strip() for elem in symbol_elements if elem.text.strip().isupper()]

            if not symbols:
                logger.error("No symbols found in the table")
                return []

            logger.info(f"✅ Fetched {len(symbols)} symbols from NSE India")
            return symbols

        except Exception as e:
            logger.exception("❌ Error fetching Nifty 200 symbols:")
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
        try:
            # Check if chromedriver is in PATH
            service = Service('/usr/local/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"System ChromeDriver not found, trying ChromeDriverManager: {e}")
            try:
                # Use ChromeDriverManager as fallback
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception as e2:
                print(f"ChromeDriverManager failed: {e2}")
                # Last resort - try without explicit service
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
        self.failed_symbols = set()

    def collect_all_fundamental_data(self, batch_size: int = 5) -> bool:
        """Collect fundamental data for all companies with comprehensive coverage"""
        companies = self.db.query(Company).filter(Company.is_active == True).all()
        
        if not companies:
            logger.error("No companies found in database")
            return False

        logger.info(f"Starting comprehensive fundamental data collection for {len(companies)} companies")
        
        # Process in smaller batches for fundamental data
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_company = {
                    executor.submit(self.collect_all_periods_fundamental_data, company.symbol): company
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
                            self.failed_symbols.add(company.symbol)
                    except Exception as e:
                        logger.error(f"Error processing fundamentals for {company.symbol}: {e}")
                        self.failed_symbols.add(company.symbol)
            
            # Longer pause between batches for fundamental data
            time.sleep(5)  # Increased delay to avoid rate limiting
        
        
        logger.info(f"Fundamental data collection completed. Failed symbols: {len(self.failed_symbols)}")
        return True

    def collect_all_periods_fundamental_data(self, symbol: str) -> bool:
        """Collect fundamental data for all periods (annual, quarterly, monthly)"""
        try:
            company = self.db.query(Company).filter(Company.symbol == symbol).first()
            if not company:
                logger.error(f"Company {symbol} not found in database")
                return False

            # Get data from Yahoo Finance
            yf_symbol = f"{symbol}.NS"
            stock = yf.Ticker(yf_symbol)
            
            # Get all available data periods
            success = True
            
            # Annual data (most comprehensive)
            logger.debug(f"Collecting annual data for {symbol}")
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            info = stock.info
            
            if not financials.empty:
                success &= self._process_comprehensive_data(
                    company.id, financials, balance_sheet, cash_flow, info, 'A'
                )
            else:
                logger.warning(f"No annual financials found for {symbol}")
                success = False
            
            # Quarterly data (more recent)
            logger.debug(f"Collecting quarterly data for {symbol}")
            q_financials = stock.quarterly_financials
            q_balance_sheet = stock.quarterly_balance_sheet
            q_cash_flow = stock.quarterly_cashflow
            
            if not q_financials.empty:
                success &= self._process_comprehensive_data(
                    company.id, q_financials, q_balance_sheet, q_cash_flow, info, 'Q'
                )
            else:
                logger.warning(f"No quarterly financials found for {symbol}")
                success = False
            
            # Monthly data (from history)

            logger.info(f"Collecting monthly data for {symbol}")
            success &= self._collect_monthly_fundamentals(company.id, stock)
            
            return success

        except Exception as e:
            logger.error(f"Error collecting all periods fundamental data for {symbol}: {e}")
            return False

    def _collect_monthly_fundamentals(self, company_id: int, stock: yf.Ticker) -> bool:
        """Collect monthly fundamental data from historical prices"""
        try:
            # Get 2 years of monthly data
            hist = stock.history(period="2y", interval="1mo")
            
            if hist.empty:
                logger.info("No monthly history data available")
                return False
            
            # Create monthly fundamental records (simplified)
            for date_idx, row in hist.iterrows():
                report_date = date_idx.date()
                
                # Check if record already exists
                existing = self.db.query(FundamentalData).filter(
                    and_(
                        FundamentalData.company_id == company_id,
                        FundamentalData.report_date == report_date,
                        FundamentalData.period_type == 'M'
                    )
                ).first()
                
                if existing:
                    continue
                
                # Create simplified monthly record
                fundamental_data = FundamentalData(
                    company_id=company_id,
                    report_date=report_date,
                    period_type='M',
                    
                    # Basic price data
                    market_cap=None,  # Will be filled from info if available
                    close_price=round(float(row['Close']), 4) if pd.notna(row['Close']) else None,
                    volume=int(row['Volume']) if pd.notna(row['Volume']) else None,
                    
                    # Other fields will be null for monthly data
                    revenue=None,
                    pat=None,
                    ebitda=None
                )
                
                with self.db_lock:
                    self.db.add(fundamental_data)
            
            self.db.commit()
            return True
            
        except Exception as e:
            print(str(e))
            logger.warning(f"Error collecting monthly fundamentals: {e}")
            return False

    def _process_comprehensive_data(self, company_id: int, financials: pd.DataFrame, 
                                balance_sheet: pd.DataFrame, cash_flow: pd.DataFrame, 
                                info: dict, period_type: str) -> bool:
        """Process all fundamental data with validation"""
        try:
            # Get all available dates from financials with proper checking
            if financials.empty:
                logger.warning(f"No {period_type} financial data available")
                return False
                
            dates = list(financials.columns)  # Convert to list to avoid DatetimeIndex issues
            if not dates:
                logger.warning(f"No {period_type} data dates available")
                return False
            
            success = True
            records_added = 0
            
            for date_col in dates:
                if not isinstance(date_col, (pd.Timestamp, datetime)):
                    logger.warning(f"Invalid date format in {period_type} data: {date_col}")
                    continue
                    
                report_date = date_col.date() if hasattr(date_col, 'date') else date_col
                
                # Skip if data is too old (more than 20 years)
                if (datetime.now().date() - report_date).days > 365 * 20:
                    continue
                
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
                
                # Create comprehensive fundamental data record
                fundamental_data = self._create_comprehensive_fundamental_record(
                    company_id, report_date, period_type, financials, balance_sheet, 
                    cash_flow, info, date_col
                )
                
                # Validate critical fields before adding
                if not self._validate_fundamental_record(fundamental_data):
                    logger.warning(f"Skipping incomplete {period_type} data for {report_date}")
                    continue
                
                with self.db_lock:
                    self.db.add(fundamental_data)
                    records_added += 1
            
            if records_added > 0:
                self.db.commit()
                logger.debug(f"Added {records_added} {period_type} records")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing {period_type} comprehensive data: {e}")
            return False
        
    def _validate_fundamental_record(self, record: FundamentalData) -> bool:
        """Validate that the record has essential data"""
        # At least one of these key metrics should be present
        key_metrics = [
            record.revenue,
            record.pat,
            record.ebitda,
            record.operating_cash_flow,
            record.total_assets
        ]
        
        return any(metric is not None for metric in key_metrics)

    def _create_comprehensive_fundamental_record(self, company_id: int, report_date, 
        period_type: str, financials: pd.DataFrame,
        balance_sheet: pd.DataFrame, cash_flow: pd.DataFrame,
        info: dict, date_col) -> FundamentalData:
        """Enhanced version with better error handling and data validation"""
        
        # Initialize all fields to None first
        fundamental_data = FundamentalData(
            company_id=company_id,
            report_date=report_date,
            period_type=period_type,
            
            # Initialize all fields as None
            revenue=None, pat=None, ebitda=None, operating_profit=None,
            interest_expense=None, total_assets=None, total_liabilities=None,
            shareholders_equity=None, cash_and_equivalents=None, total_debt=None,
            operating_cash_flow=None, capex=None, free_cash_flow=None,
            market_cap=None, shares_outstanding=None, roce=None, roe=None,
            roa=None, eps=None, pe_ratio=None, pb_ratio=None,
            debt_to_equity=None, current_ratio=None, quick_ratio=None,
            gross_margin=None, operating_margin=None, net_margin=None
        )
        
        try:
            # Extract P&L data with alternative keys
            fundamental_data.revenue = self._safe_get_df_value(
                financials, 'Total Revenue', date_col, 
                ['Revenue', 'Net Sales', 'Total Net Sales']
            )
            
            fundamental_data.pat = self._safe_get_df_value(
                financials, 'Net Income', date_col,
                ['Net Income Common Stockholders', 'Net Income Applicable To Common Shares']
            )
            
            fundamental_data.ebitda = self._safe_get_df_value(
                financials, 'EBITDA', date_col,
                ['Normalized EBITDA', 'EBITDA']
            )
            
            fundamental_data.operating_profit = self._safe_get_df_value(
                financials, 'Operating Income', date_col,
                ['Operating Revenue', 'Operating Income Or Loss']
            )
            
            fundamental_data.interest_expense = self._safe_get_df_value(
                financials, 'Interest Expense', date_col,
                ['Interest Expense Non Operating', 'Net Interest Income']
            )
            
            # Extract Balance Sheet data with alternatives
            fundamental_data.total_assets = self._safe_get_df_value(
                balance_sheet, 'Total Assets', date_col,
                ['Total Assets', 'Total Assets Net']
            )
            
            fundamental_data.total_liabilities = self._safe_get_df_value(
                balance_sheet, 'Total Liabilities Net Minority Interest', date_col,
                ['Total Liabilities', 'Total Liabilities And Stockholders Equity']
            )
            
            fundamental_data.shareholders_equity = self._safe_get_df_value(
                balance_sheet, 'Total Equity Gross Minority Interest', date_col,
                ['Stockholders Equity', 'Total Stockholders Equity']
            )
            
            fundamental_data.cash_and_equivalents = self._safe_get_df_value(
                balance_sheet, 'Cash And Cash Equivalents', date_col,
                ['Cash', 'Cash Cash Equivalents And Short Term Investments']
            )
            
            fundamental_data.total_debt = self._safe_get_df_value(
                balance_sheet, 'Total Debt', date_col,
                ['Long Term Debt', 'Total Debt And Capital Lease Obligation']
            )
            
            # Extract Cash Flow data with alternatives
            fundamental_data.operating_cash_flow = self._safe_get_df_value(
                cash_flow, 'Operating Cash Flow', date_col,
                ['Cash Flow From Operating Activities', 'Total Cash From Operating Activities']
            )
            
            fundamental_data.capex = self._safe_get_df_value(
                cash_flow, 'Capital Expenditure', date_col,
                ['Capital Expenditures', 'Capex']
            )
            
            # Calculate derived metrics
            if fundamental_data.operating_cash_flow and fundamental_data.capex:
                fundamental_data.free_cash_flow = fundamental_data.operating_cash_flow + fundamental_data.capex
            
            # Get market data (use current values for all periods)
            fundamental_data.market_cap = self._safe_get_info_value(info, 'marketCap')
            fundamental_data.shares_outstanding = self._safe_get_info_value(info, 'sharesOutstanding')
            
            # Calculate financial ratios
            ratios = self._calculate_financial_ratios(
                fundamental_data.revenue, fundamental_data.pat, fundamental_data.ebitda,
                fundamental_data.operating_profit, fundamental_data.total_assets,
                fundamental_data.total_liabilities, fundamental_data.shareholders_equity,
                fundamental_data.total_debt, fundamental_data.market_cap,
                fundamental_data.shares_outstanding, info
            )
            
            # Apply calculated ratios
            for key, value in ratios.items():
                setattr(fundamental_data, key, value)
            
        except Exception as e:
            logger.error(f"Error creating comprehensive record: {e}")
        
        return fundamental_data

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
            quarterly_financials = stock.quarterly_financials
            balance_sheet = stock.balance_sheet
            quarterly_balance_sheet = stock.quarterly_balance_sheet
            cash_flow = stock.cashflow
            quarterly_cash_flow = stock.quarterly_cashflow
            # Process data
            success = True
            
            # Process annual data
            if not financials.empty:
                success &= self._process_comprehensive_data(company.id, financials, balance_sheet, cash_flow, info, 'A')
            
            # Process quarterly data
            if not quarterly_financials.empty:
                success &= self._process_comprehensive_data(company.id, quarterly_financials, quarterly_balance_sheet, quarterly_cash_flow, info, 'Q')

            self.update_data_log(company.id,"fundamental","success",0, "")
            return success

        except Exception as e:
            logger.error(f"Error collecting fundamental data for {symbol}: {e}")
            self.update_data_log(company.id,"fundamental","error",0, str(e))
            return False

    def _calculate_financial_ratios(self, revenue, net_income, ebitda, operating_income,
                                   total_assets, total_liabilities, shareholders_equity,
                                   total_debt, market_cap, shares_outstanding, info: dict) -> Dict[str, Any]:
        """Calculate all financial ratios"""
        ratios = {}
        
        try:
            capital_employed = None
            # ROE (Return on Equity) - as percentage
            if net_income and shareholders_equity and shareholders_equity > 0:
                ratios['roe'] = (float(net_income) / float(shareholders_equity)) * 100
            else:
                ratios['roe'] = self._safe_get_info_value(info, 'returnOnEquity', as_percentage=True)
            
            # ROA (Return on Assets) - as percentage
            if net_income and total_assets and total_assets > 0:
                ratios['roa'] = (float(net_income) / float(total_assets)) * 100
            else:
                ratios['roa'] = self._safe_get_info_value(info, 'returnOnAssets', as_percentage=True)
            
            # ROCE (Return on Capital Employed) - as percentage
            if operating_income and total_assets and total_liabilities:
                capital_employed = float(total_assets) - float(total_liabilities)
                if capital_employed > 0:
                    ratios['roce'] = (float(operating_income) / capital_employed) * 100
        
            # Fallback ROCE calculations only if not already calculated
            if 'roce' not in ratios:
                # Fallback 1: Calculate EBIT if operating_income missing
                ebit = (float(operating_income)) if operating_income else \
                    (float(net_income) + 
                        float(info.get('interestExpense', 0)) + 
                        float(info.get('taxProvision', 0))) if net_income else None
                
                # Fallback 2: Calculate Capital Employed
                if capital_employed is None:  # Only calculate if not set earlier
                    if shareholders_equity and total_debt:
                        capital_employed = float(shareholders_equity) + float(total_debt)
                    elif 'totalStockholderEquity' in info and 'totalDebt' in info:
                        capital_employed = float(info['totalStockholderEquity']) + float(info['totalDebt'])
                
                # Final ROCE calculation if we have the required data
                if ebit is not None and capital_employed is not None and capital_employed > 0:
                    ratios['roce'] = (ebit / capital_employed) * 100
                else:
                    ratios['roce'] = self._safe_get_info_value(info, 'returnOnCapitalEmployed', as_percentage=True)
            # EPS (Earnings Per Share)
            if net_income and shares_outstanding and shares_outstanding > 0:
                ratios['eps'] = float(net_income) / float(shares_outstanding)
            else:
                ratios['eps'] = self._safe_get_info_value(info, 'trailingEps')
            
            # P/E Ratio
            ratios['pe_ratio'] = self._safe_get_info_value(info, 'trailingPE')
            
            # P/B Ratio
            ratios['pb_ratio'] = self._safe_get_info_value(info, 'priceToBook')
            
            # Debt to Equity
            if total_debt and shareholders_equity and shareholders_equity > 0:
                ratios['debt_to_equity'] = float(total_debt) / float(shareholders_equity)
            else:
                ratios['debt_to_equity'] = self._safe_get_info_value(info, 'debtToEquity')
            
            # Current Ratio
            ratios['current_ratio'] = self._safe_get_info_value(info, 'currentRatio')
            
            # Quick Ratio
            ratios['quick_ratio'] = self._safe_get_info_value(info, 'quickRatio')
            
            # Margin ratios - as percentages
            if revenue and revenue > 0:
                # Gross Margin
                gross_profit = self._safe_get_info_value(info, 'grossProfit')
                if gross_profit:
                    ratios['gross_margin'] = (float(gross_profit) / float(revenue)) * 100
                else:
                    ratios['gross_margin'] = self._safe_get_info_value(info, 'grossMargins', as_percentage=True)
                
                # Operating Margin
                if operating_income:
                    ratios['operating_margin'] = (float(operating_income) / float(revenue)) * 100
                else:
                    ratios['operating_margin'] = self._safe_get_info_value(info, 'operatingMargins', as_percentage=True)
                
                # Net Margin
                if net_income:
                    ratios['net_margin'] = (float(net_income) / float(revenue)) * 100
                else:
                    ratios['net_margin'] = self._safe_get_info_value(info, 'profitMargins', as_percentage=True)
            
        except Exception as e:
            logger.error(f"Error calculating ratios: {e}")
        
        return ratios

    def _calculate_growth_rate(self, current_value, previous_value) -> Optional[Decimal]:
        """Calculate growth rate as percentage"""
        try:
            if current_value is None or previous_value is None:
                return None
            
            current_val = float(current_value)
            previous_val = float(previous_value)
            
            if previous_val == 0:
                return None
            
            growth_rate = ((current_val - previous_val) / abs(previous_val)) * 100
            return Decimal(str(round(growth_rate, 4)))
            
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    def _safe_get_df_value(self, df: pd.DataFrame, key: str, date_col, alternative_keys: List[str] = None) -> Optional[Decimal]:
        """Safely get value from DataFrame with fallback options"""
        try:
            if df.empty:
                return None
            
            # Try primary key first
            if key in df.index:
                value = df.loc[key, date_col]
                if pd.notna(value) and value != 0:
                    return Decimal(str(float(value)))
            
            # Try alternative keys if provided
            if alternative_keys:
                for alt_key in alternative_keys:
                    if alt_key in df.index:
                        value = df.loc[alt_key, date_col]
                        if pd.notna(value) and value != 0:
                            return Decimal(str(float(value)))
            
        except (KeyError, ValueError, TypeError):
            pass
        return None

    def _safe_get_info_value(self, info: dict, key: str, as_percentage: bool = False) -> Optional[Decimal]:
        """Safely get value from info dictionary"""
        try:
            value = info.get(key)
            if value is not None and value != 0:
                float_value = float(value)
                if as_percentage:
                    # Convert decimal to percentage (e.g., 0.15 -> 15.0)
                    float_value = float_value * 100
                return Decimal(str(float_value))
        except (ValueError, TypeError):
            pass
        return None

    def update_data_log(self, company_id: int, data_type: str, status: str, 
                       records_updated: int = 0, error_message: str = None):
        """Update data collection log"""
        try:
            log_entry = DataUpdateLog(
                company_id=company_id,
                data_type=data_type,
                last_update_date=datetime.now().date(),
                status=status,
                records_updated=records_updated,
                error_message=error_message
            )
            
            with self.db_lock:
                self.db.add(log_entry)
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error updating data log: {e}")

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
                        fundamental_success = self.fundamental_collector.collect_all_periods_fundamental_data(symbol)
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

    def fast_setup_backtesting_data(self, symbol_list=List) -> bool:
        logger.info("🚀 Starting backtesting data setup...")
        batch_size = 10
        for i in range(0, len(symbol_list), batch_size):
            batch = symbol_list[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(symbol_list) + batch_size - 1)//batch_size}")
            
            # Process each company in the batch
            for symbol in batch:
                    
                try:
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
                        historical_success = self.historical_collector.collect_company_historical_data(symbol, period="10y")
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
                    logger.error(f"Error processing {symbol}: {e}")
                    continue
            
            # Pause between batches
            logger.info(f"Batch {i//batch_size + 1} completed. Pausing before next batch...")
            time.sleep(2)
        
        logger.info("✅ All companies processed successfully!")
        
        # Step 3: Generate data quality report
        self.generate_data_quality_report()
        
        logger.info("✅ Backtesting data setup completed successfully!")
        return True
    
    def setup_nifty200_data(self):
        """Complete setup for backtesting data"""
        logger.info("🚀 Starting backtesting data setup...")
        companies_list = SeleniumScrapper().get_nifty200_symbol()
        self.fast_setup_backtesting_data(companies_list)

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

