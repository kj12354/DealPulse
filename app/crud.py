from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from . import models, schemas


# User CRUD operations
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user"""
    db_user = models.User(email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_or_create_user(db: Session, email: str) -> models.User:
    """Get existing user or create new one"""
    user = get_user_by_email(db, email)
    if not user:
        user = create_user(db, schemas.UserCreate(email=email))
    return user


# Product CRUD operations
def get_product(db: Session, product_id: int) -> Optional[models.Product]:
    """Get product by ID"""
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def get_products_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Product]:
    """Get products for a specific user"""
    return db.query(models.Product).filter(models.Product.user_id == user_id).offset(skip).limit(limit).all()


def get_all_products(db: Session, skip: int = 0, limit: int = 100) -> List[models.Product]:
    """Get all products (for watchlist)"""
    return db.query(models.Product).offset(skip).limit(limit).all()


def create_product(db: Session, product: schemas.ProductCreate) -> models.Product:
    """Create a new product"""
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, **kwargs) -> Optional[models.Product]:
    """Update product fields"""
    product = get_product(db, product_id)
    if product:
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        db.commit()
        db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Delete a product"""
    product = get_product(db, product_id)
    if product:
        db.delete(product)
        db.commit()
        return True
    return False


# Price History CRUD operations
def get_price_history(db: Session, product_id: int, limit: int = 30) -> List[models.PriceHistory]:
    """Get price history for a product"""
    return (db.query(models.PriceHistory)
            .filter(models.PriceHistory.product_id == product_id)
            .order_by(desc(models.PriceHistory.date))
            .limit(limit)
            .all())


def create_price_entry(db: Session, product_id: int, price: float) -> models.PriceHistory:
    """Create a new price history entry"""
    db_price = models.PriceHistory(product_id=product_id, price=price)
    db.add(db_price)
    db.commit()
    db.refresh(db_price)
    return db_price


def get_latest_price(db: Session, product_id: int) -> Optional[models.PriceHistory]:
    """Get the latest price for a product"""
    return (db.query(models.PriceHistory)
            .filter(models.PriceHistory.product_id == product_id)
            .order_by(desc(models.PriceHistory.date))
            .first())


def get_average_price(db: Session, product_id: int, days: int = 30) -> Optional[float]:
    """Get average price for a product over the last N days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    result = (db.query(func.avg(models.PriceHistory.price))
              .filter(models.PriceHistory.product_id == product_id)
              .filter(models.PriceHistory.date >= cutoff_date)
              .scalar())
    return float(result) if result else None


def get_products_needing_scraping(db: Session) -> List[models.Product]:
    """Get products that need price scraping (no recent price data)"""
    # Get products that haven't been scraped in the last 23 hours
    cutoff_time = datetime.utcnow() - timedelta(hours=23)
    
    # Subquery to get the latest price date for each product
    latest_prices = (db.query(
        models.PriceHistory.product_id,
        func.max(models.PriceHistory.date).label('latest_date')
    ).group_by(models.PriceHistory.product_id).subquery())
    
    # Get products with no recent prices or no prices at all
    products_to_scrape = (db.query(models.Product)
                         .outerjoin(latest_prices, models.Product.id == latest_prices.c.product_id)
                         .filter((latest_prices.c.latest_date.is_(None)) |
                                (latest_prices.c.latest_date < cutoff_time))
                         .all())
    
    return products_to_scrape 