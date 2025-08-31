import re
import requests
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urlparse
import logging

from .base import BaseAdapter, ProductInfo

logger = logging.getLogger(__name__)


class HtmlAdapter(BaseAdapter):
    """HTML adapter using BeautifulSoup for scraping product information"""
    
    def __init__(self, timeout: int = 10):
        super().__init__(timeout)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def supports_url(self, url: str) -> bool:
        """This adapter supports most URLs as a fallback"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
        except Exception:
            return False
    
    def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """Extract product info using HTML parsing with BeautifulSoup"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product name
            name = self._extract_name(soup, url)
            if not name:
                logger.warning(f"Could not extract product name from {url}")
                return None
            
            # Extract price
            price = self._extract_price(soup, url)
            if price is None:
                logger.warning(f"Could not extract price from {url}")
                return None
            
            return ProductInfo(name=name, price=price)
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def _extract_name(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract product name from HTML"""
        # Try multiple selectors for product name
        selectors = [
            'h1',
            '[data-testid*="product-title"]',
            '[class*="product-title"]',
            '[class*="product-name"]',
            '[id*="product-title"]',
            'title',
            'meta[property="og:title"]',
            'meta[name="title"]'
        ]
        
        for selector in selectors:
            try:
                if selector.startswith('meta'):
                    element = soup.select_one(selector)
                    if element:
                        content = element.get('content', '').strip()
                        if content and len(content) > 3:
                            return content
                else:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if text and len(text) > 3:
                            return text
            except Exception:
                continue
        
        return None
    
    def _extract_price(self, soup: BeautifulSoup, url: str) -> Optional[float]:
        """Extract price from HTML"""
        # Try multiple selectors for price
        selectors = [
            '[class*="price"]',
            '[data-testid*="price"]',
            '[id*="price"]',
            'meta[property="product:price:amount"]',
            'meta[property="og:price:amount"]',
            '.a-price-whole',  # Amazon
            '.notranslate',    # Common price class
        ]
        
        price_patterns = [
            r'[\$£€¥₹]\s*(\d+[,.]?\d*\.?\d*)',  # Currency symbols
            r'(\d+[,.]?\d*\.?\d*)\s*[\$£€¥₹]',  # Currency after
            r'(\d+[,.]?\d*\.?\d*)',              # Just numbers
        ]
        
        for selector in selectors:
            try:
                if selector.startswith('meta'):
                    element = soup.select_one(selector)
                    if element:
                        content = element.get('content', '')
                        price = self._parse_price_text(content, price_patterns)
                        if price is not None:
                            return price
                else:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text(strip=True)
                        price = self._parse_price_text(text, price_patterns)
                        if price is not None:
                            return price
            except Exception:
                continue
        
        return None
    
    def _parse_price_text(self, text: str, patterns: list) -> Optional[float]:
        """Parse price from text using regex patterns"""
        if not text:
            return None
            
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    # Clean the match (remove commas, handle decimals)
                    clean_price = match.replace(',', '')
                    price = float(clean_price)
                    # Basic validation - price should be reasonable
                    if 0.01 <= price <= 999999:
                        return price
                except (ValueError, TypeError):
                    continue
        
        return None 