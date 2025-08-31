import requests
import extruct
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging

from .base import BaseAdapter, ProductInfo

logger = logging.getLogger(__name__)


class JsonLdAdapter(BaseAdapter):
    """JSON-LD adapter using extruct for structured data scraping"""
    
    def __init__(self, timeout: int = 10):
        super().__init__(timeout)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def supports_url(self, url: str) -> bool:
        """This adapter supports URLs that might have structured data"""
        try:
            parsed = urlparse(url)
            # Prioritize for known e-commerce sites
            known_sites = ['amazon.', 'ebay.', 'walmart.', 'target.', 'bestbuy.']
            hostname = parsed.hostname or ''
            return (bool(parsed.netloc and parsed.scheme in ['http', 'https']) and
                    any(site in hostname.lower() for site in known_sites))
        except Exception:
            return False
    
    def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """Extract product info using JSON-LD structured data"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Extract structured data
            data = extruct.extract(
                response.text,
                base_url=url,
                syntaxes=['json-ld', 'microdata', 'rdfa']
            )
            
            # Try JSON-LD first
            product_info = self._extract_from_jsonld(data.get('json-ld', []))
            if product_info:
                return product_info
            
            # Try microdata
            product_info = self._extract_from_microdata(data.get('microdata', []))
            if product_info:
                return product_info
            
            # Try RDFa
            product_info = self._extract_from_rdfa(data.get('rdfa', []))
            if product_info:
                return product_info
            
            logger.warning(f"No structured data found for {url}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting structured data from {url}: {e}")
            return None
    
    def _extract_from_jsonld(self, jsonld_data: list) -> Optional[ProductInfo]:
        """Extract product info from JSON-LD data"""
        for item in jsonld_data:
            if isinstance(item, dict):
                # Check if it's a Product type
                item_type = item.get('@type', '')
                if isinstance(item_type, list):
                    item_type = ' '.join(item_type)
                
                if 'Product' in str(item_type):
                    name = self._get_nested_value(item, ['name', 'title'])
                    price = self._extract_price_from_offers(item.get('offers', {}))
                    
                    if name and price is not None:
                        return ProductInfo(name=str(name), price=float(price))
        
        return None
    
    def _extract_from_microdata(self, microdata: list) -> Optional[ProductInfo]:
        """Extract product info from microdata"""
        for item in microdata:
            if isinstance(item, dict):
                item_type = item.get('type', '')
                if 'Product' in str(item_type):
                    properties = item.get('properties', {})
                    name = self._get_nested_value(properties, ['name'])
                    
                    # Look for offers in properties
                    offers = properties.get('offers', [])
                    if offers and isinstance(offers, list):
                        for offer in offers:
                            if isinstance(offer, dict):
                                offer_props = offer.get('properties', {})
                                price = self._get_nested_value(offer_props, ['price', 'lowPrice'])
                                if price is not None and name:
                                    try:
                                        return ProductInfo(name=str(name), price=float(price))
                                    except (ValueError, TypeError):
                                        continue
        
        return None
    
    def _extract_from_rdfa(self, rdfa_data: list) -> Optional[ProductInfo]:
        """Extract product info from RDFa data"""
        # RDFa extraction is more complex, simplified version here
        for item in rdfa_data:
            if isinstance(item, dict):
                # Look for product-related predicates
                if any(key for key in item.keys() if 'product' in str(key).lower()):
                    # This is a simplified implementation
                    # In practice, you'd need more sophisticated RDFa parsing
                    pass
        
        return None
    
    def _extract_price_from_offers(self, offers: Any) -> Optional[float]:
        """Extract price from offers structure"""
        if not offers:
            return None
        
        # Handle single offer
        if isinstance(offers, dict):
            offers = [offers]
        
        # Handle list of offers
        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    # Try different price fields
                    price = self._get_nested_value(offer, [
                        'price', 'lowPrice', 'highPrice', 'priceSpecification/price'
                    ])
                    if price is not None:
                        try:
                            # Clean price string if needed
                            if isinstance(price, str):
                                price = price.replace('$', '').replace(',', '').strip()
                            return float(price)
                        except (ValueError, TypeError):
                            continue
        
        return None
    
    def _get_nested_value(self, data: Dict[str, Any], keys: list) -> Any:
        """Get value from nested dictionary using multiple possible keys"""
        if not isinstance(data, dict):
            return None
        
        for key in keys:
            if '/' in key:
                # Handle nested keys like 'priceSpecification/price'
                nested_keys = key.split('/')
                value = data
                for nested_key in nested_keys:
                    if isinstance(value, dict) and nested_key in value:
                        value = value[nested_key]
                    else:
                        value = None
                        break
                if value is not None:
                    return value
            elif key in data:
                value = data[key]
                # If it's a list, try to get the first item
                if isinstance(value, list) and value:
                    return value[0]
                return value
        
        return None 