import pytest
from unittest.mock import Mock, patch
import requests
from bs4 import BeautifulSoup

from app.adapters.base import BaseAdapter, ProductInfo
from app.adapters.html_adapter import HtmlAdapter
from app.adapters.jsonld_adapter import JsonLdAdapter
from app.adapters.factory import AdapterFactory


class TestHtmlAdapter:
    """Test HTML adapter scraping logic"""
    
    def test_supports_url(self):
        """Test URL support validation"""
        adapter = HtmlAdapter()
        
        # Valid URLs
        assert adapter.supports_url("https://www.amazon.com/product")
        assert adapter.supports_url("http://example.com/item")
        
        # Invalid URLs
        assert not adapter.supports_url("not-a-url")
        assert not adapter.supports_url("ftp://example.com")
    
    @patch('requests.Session.get')
    def test_extract_product_info_success(self, mock_get):
        """Test successful product info extraction"""
        # Mock HTML response
        mock_html = """
        <html>
            <head>
                <title>Test Product - Amazon</title>
                <meta property="og:title" content="Test Product">
            </head>
            <body>
                <h1>Test Product</h1>
                <span class="a-price-whole">29</span>
                <span class="a-price-fraction">99</span>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        adapter = HtmlAdapter()
        result = adapter.get_product_info("https://www.amazon.com/test-product")
        
        assert result is not None
        assert result.name == "Test Product"
        assert result.price == 29.0  # Should extract the whole number part
    
    @patch('requests.Session.get')
    def test_extract_price_with_currency_symbol(self, mock_get):
        """Test price extraction with currency symbols"""
        mock_html = """
        <html>
            <body>
                <h1>Test Product</h1>
                <div class="price">$49.99</div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        adapter = HtmlAdapter()
        result = adapter.get_product_info("https://example.com/product")
        
        assert result is not None
        assert result.price == 49.99
    
    @patch('requests.Session.get')
    def test_extract_name_from_meta_tag(self, mock_get):
        """Test product name extraction from meta tags"""
        mock_html = """
        <html>
            <head>
                <meta property="og:title" content="Amazing Widget - Best Deal">
            </head>
            <body>
                <div class="price">$25.50</div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        adapter = HtmlAdapter()
        result = adapter.get_product_info("https://example.com/widget")
        
        assert result is not None
        assert result.name == "Amazing Widget - Best Deal"
        assert result.price == 25.50
    
    @patch('requests.Session.get')
    def test_request_failure(self, mock_get):
        """Test handling of request failures"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        adapter = HtmlAdapter()
        result = adapter.get_product_info("https://example.com/product")
        
        assert result is None
    
    @patch('requests.Session.get')
    def test_no_product_info_found(self, mock_get):
        """Test handling when no product info can be extracted"""
        mock_html = """
        <html>
            <body>
                <div>Some random content</div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        adapter = HtmlAdapter()
        result = adapter.get_product_info("https://example.com/product")
        
        assert result is None


class TestJsonLdAdapter:
    """Test JSON-LD adapter logic"""
    
    def test_supports_url_known_sites(self):
        """Test URL support for known e-commerce sites"""
        adapter = JsonLdAdapter()
        
        # Known sites should be supported
        assert adapter.supports_url("https://www.amazon.com/product")
        assert adapter.supports_url("https://www.ebay.com/item")
        assert adapter.supports_url("https://walmart.com/product")
        
        # Unknown sites should not be prioritized
        assert not adapter.supports_url("https://randomsite.com/product")
    
    @patch('requests.Session.get')
    @patch('extruct.extract')
    def test_extract_from_json_ld(self, mock_extract, mock_get):
        """Test extraction from JSON-LD structured data"""
        # Mock structured data
        mock_data = {
            'json-ld': [
                {
                    '@type': 'Product',
                    'name': 'Structured Data Product',
                    'offers': {
                        'price': '39.99'
                    }
                }
            ],
            'microdata': [],
            'rdfa': []
        }
        
        mock_extract.return_value = mock_data
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>...</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        adapter = JsonLdAdapter()
        result = adapter.get_product_info("https://www.amazon.com/product")
        
        assert result is not None
        assert result.name == "Structured Data Product"
        assert result.price == 39.99
    
    @patch('requests.Session.get')
    @patch('extruct.extract')
    def test_no_structured_data(self, mock_extract, mock_get):
        """Test handling when no structured data is found"""
        mock_data = {
            'json-ld': [],
            'microdata': [],
            'rdfa': []
        }
        
        mock_extract.return_value = mock_data
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>...</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        adapter = JsonLdAdapter()
        result = adapter.get_product_info("https://www.amazon.com/product")
        
        assert result is None


class TestAdapterFactory:
    """Test adapter factory logic"""
    
    def test_adapter_selection(self):
        """Test that factory selects appropriate adapters"""
        factory = AdapterFactory()
        
        # Factory should have both adapters
        assert len(factory.adapters) == 2
        assert any(isinstance(adapter, JsonLdAdapter) for adapter in factory.adapters)
        assert any(isinstance(adapter, HtmlAdapter) for adapter in factory.adapters)
    
    @patch.object(JsonLdAdapter, 'get_product_info')
    @patch.object(JsonLdAdapter, 'supports_url')
    def test_successful_extraction(self, mock_supports, mock_get_info):
        """Test successful product info extraction"""
        mock_supports.return_value = True
        mock_get_info.return_value = ProductInfo(name="Test Product", price=25.99)
        
        factory = AdapterFactory()
        result = factory.get_product_info("https://www.amazon.com/product")
        
        assert result is not None
        assert result.name == "Test Product"
        assert result.price == 25.99
    
    @patch.object(JsonLdAdapter, 'get_product_info')
    @patch.object(JsonLdAdapter, 'supports_url')
    @patch.object(HtmlAdapter, 'get_product_info')
    @patch.object(HtmlAdapter, 'supports_url')
    def test_fallback_to_second_adapter(self, html_supports, html_get, jsonld_supports, jsonld_get):
        """Test fallback when first adapter fails"""
        # First adapter supports URL but fails to extract
        jsonld_supports.return_value = True
        jsonld_get.return_value = None
        
        # Second adapter succeeds
        html_supports.return_value = True
        html_get.return_value = ProductInfo(name="Fallback Product", price=15.50)
        
        factory = AdapterFactory()
        result = factory.get_product_info("https://www.amazon.com/product")
        
        assert result is not None
        assert result.name == "Fallback Product"
        assert result.price == 15.50


class TestPriceCalculations:
    """Test price calculation functions"""
    
    def test_price_drop_percentage(self):
        """Test price drop percentage calculation"""
        from app.tasks.email_tasks import calculate_price_drop_percentage
        
        # 20% drop
        result = calculate_price_drop_percentage(80.0, 100.0)
        assert result == 20.0
        
        # 50% drop
        result = calculate_price_drop_percentage(25.0, 50.0)
        assert result == 50.0
        
        # No drop (same price)
        result = calculate_price_drop_percentage(100.0, 100.0)
        assert result == 0.0
        
        # Price increase (negative drop)
        result = calculate_price_drop_percentage(120.0, 100.0)
        assert result == -20.0
        
        # Division by zero protection
        result = calculate_price_drop_percentage(50.0, 0.0)
        assert result == 0.0 