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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
        if not companies_list:
            logger.error("Failed to fetch companies list")
            return False
            
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
        
        # Enhanced options for better compatibility
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add user agent to avoid bot detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        if headless:
            options.add_argument('--headless')
            
        self.driver = webdriver.Chrome(options=options)
        
        # Execute script to remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 30)  # Increased timeout

    def get_nifty200(self) -> List[str]:
        try:
            url = "https://www.moneycontrol.com/stocks/marketstats/indexcomp.php?optex=NSE&opttopic=indexcomp&index=49"
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load completely
            time.sleep(5)
            
            # Try to handle any popups first
            self._handle_popups()
            
            # Try multiple selectors for the company names
            companies = self._try_multiple_selectors()
            
            if not companies:
                logger.error("No companies found with any selector")
                # Take a screenshot for debugging
                self.driver.save_screenshot("debug_moneycontrol.png")
                logger.info("Screenshot saved as debug_moneycontrol.png")
                return []
            
            logger.info(f"✅ Fetched {len(companies)} companies from Moneycontrol")
            return companies

        except Exception as e:
            logger.exception("❌ Error fetching Nifty 200 list:")
            # Take a screenshot for debugging
            try:
                self.driver.save_screenshot("error_moneycontrol.png")
                logger.info("Error screenshot saved as error_moneycontrol.png")
            except:
                pass
            return []

        finally:
            self.driver.quit()

    def _handle_popups(self):
        """Handle any popups that might appear"""
        try:
            # Common popup selectors
            popup_selectors = [
                '.qc-cmp2-summary-buttons__button',
                '.popup-close',
                '.close-button',
                '[data-dismiss="modal"]',
                '.modal-close'
            ]
            
            for selector in popup_selectors:
                try:
                    popup = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    popup.click()
                    logger.info(f"Closed popup with selector: {selector}")
                    time.sleep(1)
                    break
                except TimeoutException:
                    continue
                    
        except Exception as e:
            logger.debug(f"No popups to handle: {e}")

    def _try_multiple_selectors(self) -> List[str]:
        """Try multiple selectors to find company names"""
        selectors = [
            # Original selector
            '//span[contains(@class, "ReuseTable_gld13")]/a',
            # Alternative selectors
            '//table//td/a[contains(@href, "/company/")]',
            '//a[contains(@href, "/company/")]',
            '//table//tr/td[1]/a',
            '//div[contains(@class, "companyname")]/a',
            '//span[contains(@class, "companyname")]/a',
            # More generic selectors
            '//table//a[contains(@href, "company")]',
            '//a[contains(@class, "company")]'
        ]
        
        for selector in selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, selector)))
                
                companies = []
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 2:  # Basic validation
                        companies.append(text)
                
                if companies:
                    logger.info(f"✅ Found {len(companies)} companies with selector: {selector}")
                    return companies[:200]  # Limit to 200 companies
                    
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
        
        # Enhanced options similar to SeleniumScrapper
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        if headless:
            options.add_argument('--headless')
            
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)
        
    def search_and_get_symbol(self, company_name):
        """Search for company on Screener.in and extract symbol"""
        try:
            print(f"Searching for: {company_name}")
            
            # Go to Screener.in
            self.driver.get("https://www.screener.in/")
            
            # Wait for page to load
            time.sleep(5)
            
            # Wait for the search box
            print("===================++++++++++++")
            print("Current page:", self.driver.current_url)

            # Wait for input box to appear (visible is safer than clickable initially)
            try:
                print("=================== Waiting for input box...")
                
                # Wait for the parent div that contains the input box
                self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.home-search input[type="search"]')
                ))

                # Now access the input
                search_box = self.driver.find_element(By.CSS_SELECTOR, 'div.home-search input[type="search"]')

                search_box.click()
                search_box.clear()
                time.sleep(0.5)

                for char in company_name:
                    search_box.send_keys(char)
                    time.sleep(0.1)

                search_box.send_keys(Keys.RETURN)
                time.sleep(2)

            except Exception as e:
                print("❌ Failed to locate search box:", e)
                self.driver.save_screenshot(f"error_searchbox_{company_name.replace(' ', '_')}.png")
                return None

            # Wait for redirect
            try:
                WebDriverWait(self.driver, 5).until(EC.url_contains('/company/'))
            except TimeoutException:
                print(f"⚠️ No redirect for {company_name}, may be invalid or ambiguous.")

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
        """Extract NSE symbol from Screener.in company page only"""
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
            except Exception as e:
                print("NSE span lookup failed:", e)

            # Method 2: From URL (fallback)
            current_url = self.driver.current_url
            print(f"Current URL: {current_url}")
            if '/company/' in current_url:
                url_parts = current_url.rstrip('/').split('/')
                symbol = url_parts[-1]
                if symbol and symbol.replace('-', '').isalnum():
                    return symbol.upper()

            # Method 3: From page title (if contains NSE:)
            try:
                title = self.driver.title
                if 'NSE:' in title:
                    return title.split('NSE:')[1].strip().split()[0].upper()
            except:
                pass

            # Method 4: Meta tag
            try:
                metas = self.driver.find_elements(By.XPATH, '//meta[@name="description"]')
                for meta in metas:
                    content = meta.get_attribute("content")
                    if content and "NSE:" in content:
                        return content.split("NSE:")[1].strip().split()[0].upper()
            except:
                pass

            # Method 5: Regex fallback from HTML
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
        """Get symbols for a list of company names"""
        symbols = []
        for company_name in company_names:
            if not company_name.strip():
                continue
            symbol = self.search_and_get_symbol(company_name)
            if symbol:
                symbols.append(symbol)
            time.sleep(1)  # Be respectful to the server
        return symbols
    
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()