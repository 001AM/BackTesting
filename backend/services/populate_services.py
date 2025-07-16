from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from backend.models.database import Company
from backend.models.schemas import CompanyCreate
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import yfinance as yf
import time
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompanyPopulate:
    def __init__(self, db: Session):
        self.db = db

    def company_exists(self, symbol: str) -> bool:
        return self.db.query(Company).filter_by(symbol=symbol).first() is not None

    def company_create(self, company_data: Dict) -> bool:
        if not company_data or not company_data.get("symbol"):
            return False
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
        screener = ScreenerSymbolExtractor()
        symbols = screener.get_symbols_for_companies(companies_list)

        for symbol in symbols:
            company_data = self.get_company_data_from_yahoo(symbol)
            if company_data:
                self.company_create(company_data)

        return True

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
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1200,800')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')  # For Docker/Linux
        if headless:
            options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)


    def get_nifty200(self) -> List[str]:
        try:
            url = "https://www.moneycontrol.com/stocks/marketstats/indexcomp.php?optex=NSE&opttopic=indexcomp&index=49"
            self.driver.get(url)

            price_elems = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, '//span[contains(@class, "ReuseTable_gld13")]/a')
            ))
            companies = [
                elem.text.strip() for elem in price_elems
            ]
            
            logger.info(f"✅ Fetched {len(companies)} companies from Moneycontrol")
            return companies

        except Exception as e:
            logger.exception("❌ Error fetching Nifty 200 list:")
            return []

        finally:
            self.driver.quit()

class ScreenerSymbolExtractor:
    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1200,800')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')  # For Docker/Linux
        if headless:
            options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)

    def search_and_get_symbol(self, company_name: str) -> Optional[str]:
        try:
            self.driver.get("https://www.screener.in/")
            time.sleep(3)

            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.home-search input[type="search"]')
            ))
            search_box = self.driver.find_element(By.CSS_SELECTOR, 'div.home-search input[type="search"]')
            search_box.clear()
            search_box.click()

            for char in company_name:
                search_box.send_keys(char)
                time.sleep(0.1)

            search_box.send_keys(Keys.RETURN)
            time.sleep(3)

            try:
                WebDriverWait(self.driver, 5).until(EC.url_contains('/company/'))
            except TimeoutException:
                return None

            return self._extract_symbol_from_page()

        except Exception as e:
            logger.error(f"Error searching Screener for {company_name}: {e}")
            return None

    def _extract_symbol_from_page(self) -> Optional[str]:
        try:
            url = self.driver.current_url
            if '/company/' in url:
                parts = url.rstrip('/').split('/')
                return parts[-1].upper() if parts[-1].isalnum() else None
        except Exception as e:
            logger.error(f"Error extracting symbol: {e}")
        return None

    def get_symbols_for_companies(self, company_names: List[str]) -> List[str]:
        symbols = []
        for name in company_names:
            if not name.strip():
                continue
            symbol = self.search_and_get_symbol(name)
            if symbol:
                symbols.append(symbol)
            time.sleep(1)
        return symbols

    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
