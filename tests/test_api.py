import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.adapters.base import ProductInfo


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_root_endpoint(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "DealPulse Lite" in data["message"]
    assert data["version"] == "1.0.0"


@patch('app.adapters.factory.adapter_factory.get_product_info')
def test_add_product_success(mock_get_info, client: TestClient):
    """Test successful product addition"""
    # Mock successful product info extraction
    mock_get_info.return_value = ProductInfo(name="Test Product", price=29.99)
    
    request_data = {
        "url": "https://www.amazon.com/test-product",
        "user_email": "test@example.com"
    }
    
    response = client.post("/api/v1/products", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["retailer"] == "Amazon"
    assert data["url"] == request_data["url"]


@patch('app.adapters.factory.adapter_factory.get_product_info')
def test_add_product_scraping_failure(mock_get_info, client: TestClient):
    """Test product addition when scraping fails"""
    # Mock failed product info extraction
    mock_get_info.return_value = None
    
    request_data = {
        "url": "https://www.amazon.com/test-product",
        "user_email": "test@example.com"
    }
    
    response = client.post("/api/v1/products", json=request_data)
    
    assert response.status_code == 422
    data = response.json()
    assert "Could not extract product information" in data["detail"]


def test_add_product_invalid_url(client: TestClient):
    """Test product addition with invalid URL"""
    request_data = {
        "url": "not-a-valid-url",
        "user_email": "test@example.com"
    }
    
    response = client.post("/api/v1/products", json=request_data)
    
    assert response.status_code == 400
    data = response.json()
    assert "Invalid URL format" in data["detail"]


def test_get_watchlist_empty(client: TestClient):
    """Test getting empty watchlist"""
    response = client.get("/api/v1/watchlist")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_product_not_found(client: TestClient):
    """Test getting non-existent product"""
    response = client.get("/api/v1/products/999")
    
    assert response.status_code == 404
    data = response.json()
    assert "Product not found" in data["detail"]


def test_get_prices_not_found(client: TestClient):
    """Test getting prices for non-existent product"""
    response = client.get("/api/v1/prices/999")
    
    assert response.status_code == 404
    data = response.json()
    assert "Product not found" in data["detail"]


def test_delete_product_not_found(client: TestClient):
    """Test deleting non-existent product"""
    response = client.delete("/api/v1/products/999")
    
    assert response.status_code == 404
    data = response.json()
    assert "Product not found" in data["detail"]


def test_add_product_invalid_email(client: TestClient):
    """Test product addition with invalid email"""
    request_data = {
        "url": "https://www.amazon.com/test-product",
        "user_email": "not-an-email"
    }
    
    response = client.post("/api/v1/products", json=request_data)
    
    assert response.status_code == 422  # Validation error 