from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ProductInfo:
    name: str
    price: float


class BaseAdapter(ABC):
    """Base adapter interface for scraping product information from different retailers"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    @abstractmethod
    def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """
        Extract product name and price from the given URL
        
        Args:
            url: Product URL to scrape
            
        Returns:
            ProductInfo with name and price, or None if scraping failed
        """
        pass
    
    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """
        Check if this adapter can handle the given URL
        
        Args:
            url: URL to check
            
        Returns:
            True if this adapter can handle the URL, False otherwise
        """
        pass 