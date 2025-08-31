from typing import List, Optional
import logging

from .base import BaseAdapter, ProductInfo
from .html_adapter import HtmlAdapter
from .jsonld_adapter import JsonLdAdapter

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Factory class to manage and select appropriate adapters for scraping"""
    
    def __init__(self):
        self.adapters: List[BaseAdapter] = [
            JsonLdAdapter(),  # Try structured data first
            HtmlAdapter(),    # Fallback to HTML parsing
        ]
    
    def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """
        Get product information using the best available adapter
        
        Args:
            url: Product URL to scrape
            
        Returns:
            ProductInfo if successful, None otherwise
        """
        for adapter in self.adapters:
            if adapter.supports_url(url):
                try:
                    product_info = adapter.get_product_info(url)
                    if product_info:
                        logger.info(f"Successfully scraped {url} using {adapter.__class__.__name__}")
                        return product_info
                except Exception as e:
                    logger.warning(f"Adapter {adapter.__class__.__name__} failed for {url}: {e}")
                    continue
        
        logger.error(f"No adapter could scrape {url}")
        return None
    
    def add_adapter(self, adapter: BaseAdapter, priority: int = 0):
        """
        Add a new adapter to the factory
        
        Args:
            adapter: The adapter to add
            priority: Priority level (0 = highest priority, added to front)
        """
        if priority == 0:
            self.adapters.insert(0, adapter)
        else:
            self.adapters.append(adapter)


# Global adapter factory instance
adapter_factory = AdapterFactory() 