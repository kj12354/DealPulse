from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, HttpUrl


# User schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Product schemas
class ProductBase(BaseModel):
    name: str
    retailer: str
    url: str


class ProductCreate(ProductBase):
    user_id: int


class ProductResponse(ProductBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Price History schemas
class PriceHistoryBase(BaseModel):
    price: float
    date: datetime


class PriceHistoryResponse(PriceHistoryBase):
    id: int
    product_id: int
    
    class Config:
        from_attributes = True


# Response schemas with relationships
class ProductWithPrices(ProductResponse):
    price_history: List[PriceHistoryResponse] = []


class UserWithProducts(User):
    products: List[ProductResponse] = []


# API request/response schemas
class AddProductRequest(BaseModel):
    url: str
    user_email: EmailStr


class ProductInfo(BaseModel):
    name: str
    price: float


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime 