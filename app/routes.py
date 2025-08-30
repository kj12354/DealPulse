from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from . import crud, models, schemas
from .database import get_db
from .adapters.factory import adapter_factory

router = APIRouter()


@router.get("/health", response_model=schemas.HealthResponse)
async def health_check():
    """Health check endpoint"""
    return schemas.HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@router.post("/products", response_model=schemas.ProductResponse)
async def add_product(
    request: schemas.AddProductRequest,
    db: Session = Depends(get_db)
):
    """Add a product to track"""
    # Validate URL
    try:
        parsed_url = urlparse(request.url)
        if not parsed_url.netloc or not parsed_url.scheme:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format"
        )
    
    # Get or create user
    user = crud.get_or_create_user(db, request.user_email)
    
    # Extract product info using adapters
    product_info = adapter_factory.get_product_info(request.url)
    if not product_info:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract product information from URL. Please check the URL and try again."
        )
    
    # Determine retailer from URL
    retailer = parsed_url.netloc.replace('www.', '').split('.')[0].title()
    
    # Create product
    product_data = schemas.ProductCreate(
        name=product_info.name,
        retailer=retailer,
        url=request.url,
        user_id=user.id
    )
    
    product = crud.create_product(db, product_data)
    
    # Create initial price entry
    crud.create_price_entry(db, product.id, product_info.price)
    
    return product


@router.get("/watchlist", response_model=List[schemas.ProductWithPrices])
async def get_watchlist(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all tracked products (watchlist)"""
    products = crud.get_all_products(db, skip=skip, limit=limit)
    
    # Enrich with price history
    result = []
    for product in products:
        price_history = crud.get_price_history(db, product.id, limit=10)
        product_dict = schemas.ProductResponse.from_orm(product).dict()
        product_dict["price_history"] = [
            schemas.PriceHistoryResponse.from_orm(ph) for ph in price_history
        ]
        result.append(schemas.ProductWithPrices(**product_dict))
    
    return result


@router.get("/prices/{product_id}", response_model=List[schemas.PriceHistoryResponse])
async def get_product_prices(
    product_id: int,
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """Get historical prices for a specific product"""
    # Check if product exists
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    price_history = crud.get_price_history(db, product_id, limit=limit)
    return [schemas.PriceHistoryResponse.from_orm(ph) for ph in price_history]


@router.get("/products/{product_id}", response_model=schemas.ProductWithPrices)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific product with its price history"""
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    price_history = crud.get_price_history(db, product_id, limit=30)
    product_dict = schemas.ProductResponse.from_orm(product).dict()
    product_dict["price_history"] = [
        schemas.PriceHistoryResponse.from_orm(ph) for ph in price_history
    ]
    
    return schemas.ProductWithPrices(**product_dict)


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Delete a product from tracking"""
    success = crud.delete_product(db, product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return {"message": "Product deleted successfully"} 